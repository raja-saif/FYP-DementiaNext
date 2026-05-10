import math
import os
import time
from io import BytesIO
from django.conf import settings
from django.core.files.storage import default_storage
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import DetectionResult, ModelMetadata, DoctorReview
from .serializers import (
    DetectionResultSerializer, DetectionUploadSerializer,
    ModelMetadataSerializer, DoctorReviewSerializer, PatientVisibleReviewSerializer,
)
import logging

logger = logging.getLogger(__name__)


def _finalize_detection_from_inference(detection_result, result: dict, processing_time: float) -> None:
    """
    Persist model outputs and mark completed. Raises ValueError if the
    model did not return usable diagnosis fields (avoids 201 with nulls).
    """
    pred = result.get('predicted_class')
    conf = result.get('confidence')
    if pred is None or (isinstance(pred, str) and not pred.strip()):
        raise ValueError('AI inference returned no predicted_class.')
    if conf is None:
        raise ValueError('AI inference returned no confidence score.')
    try:
        conf_f = float(conf)
    except (TypeError, ValueError) as exc:
        raise ValueError(f'AI inference returned invalid confidence: {conf!r}') from exc
    if not math.isfinite(conf_f):
        raise ValueError('AI inference returned non-finite confidence.')

    detection_result.status = 'completed'
    detection_result.predicted_class = pred
    detection_result.confidence_score = conf_f
    detection_result.prediction_probability = result.get('probabilities')
    detection_result.analysis_details = result.get('analysis')
    detection_result.processing_time = processing_time
    detection_result.save()


# ML libraries are imported lazily at inference time so the server can
# start even when torch / torchvision / nibabel are not installed.
torch = None
np = None
nib = None
Image = None
transforms = None
resnet34 = None


def _ensure_ml_libs():
    """Import heavy ML deps on first use."""
    global torch, np, nib, Image, transforms, resnet34
    if torch is not None:
        return
    import torch as _torch
    import numpy as _np
    import nibabel as _nib
    from PIL import Image as _Image
    from torchvision import transforms as _transforms
    from torchvision.models import resnet34 as _resnet34

    torch = _torch
    np = _np
    nib = _nib
    Image = _Image
    transforms = _transforms
    resnet34 = _resnet34


class ModelLoader:
    """Singleton for loading and caching the trained binary dementia detector model"""
    _instance = None
    _model = None
    _device = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ModelLoader, cls).__new__(cls)
        return cls._instance
    
    @property
    def model(self):
        if self._model is None:
            self._load_model()
        return self._model
    
    @property
    def device(self):
        if self._device is None:
            self._device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        return self._device
    
    def _load_model(self):
        """Load the trained ResNet-34 binary model"""
        _ensure_ml_libs()
        try:
            # Model path - adjust to your actual model location
            model_path = os.path.join(settings.BASE_DIR, 'models', 'dementia_detector.pth')
            
            # Initialize ResNet-34 backbone
            backbone = resnet34(pretrained=False)
            
            # Replace final layer for binary classification
            num_features = backbone.fc.in_features
            backbone.fc = torch.nn.Sequential(
                torch.nn.Dropout(0.5),
                torch.nn.Linear(num_features, 1)
            )
            
            # Wrap in the same structure used during training
            class DementiaDetector(torch.nn.Module):
                def __init__(self, backbone):
                    super().__init__()
                    self.backbone = backbone
                
                def forward(self, x):
                    return self.backbone(x)
            
            self._model = DementiaDetector(backbone)
            
            # Load trained weights
            if os.path.exists(model_path):
                checkpoint = torch.load(model_path, map_location=self.device)
                self._model.load_state_dict(checkpoint['model_state_dict'])
                logger.info(f"Binary model loaded from {model_path}")
            else:
                logger.warning(f"Model file not found at {model_path}. Using untrained model.")
            
            self._model.to(self.device)
            self._model.eval()
            
        except Exception as e:
            logger.error(f"Error loading binary model: {str(e)}")
            raise


class SubtypeModelLoader:
    """Singleton for loading and caching the 4-class subtype classifier model"""
    _instance = None
    _model = None
    _device = None
    
    # Class names in the order the model outputs them
    CLASS_NAMES = ['ad', 'pd', 'ftd', 'cn']
    CLASS_DISPLAY = {
        'ad': "Alzheimer's Disease",
        'pd': "Parkinson's Disease", 
        'ftd': "Frontotemporal Dementia",
        'cn': "Control/Normal"
    }
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(SubtypeModelLoader, cls).__new__(cls)
        return cls._instance
    
    @property
    def model(self):
        if self._model is None:
            self._load_model()
        return self._model
    
    @property
    def device(self):
        if self._device is None:
            self._device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        return self._device
    
    def _load_model(self):
        """Load the trained ResNet-34 subtype classifier model"""
        _ensure_ml_libs()
        try:
            model_path = os.path.join(settings.BASE_DIR, 'models', 'subtype_classifier.pth')
            
            # Initialize ResNet-34 backbone
            backbone = resnet34(pretrained=False)
            
            # Replace final layer for 4-class classification
            # Architecture must match the checkpoint: Dropout -> Linear(512,512) -> ReLU -> Dropout -> Linear(512,4)
            num_features = backbone.fc.in_features  # 512 for ResNet-34
            backbone.fc = torch.nn.Sequential(
                torch.nn.Dropout(0.25),
                torch.nn.Linear(num_features, 512),
                torch.nn.ReLU(),
                torch.nn.Dropout(0.25),
                torch.nn.Linear(512, 4)  # 4 classes: AD, PD, FTD, CN
            )
            
            # Wrap in the same structure used during training
            class SubtypeClassifier(torch.nn.Module):
                def __init__(self, backbone):
                    super().__init__()
                    self.backbone = backbone
                
                def forward(self, x):
                    return self.backbone(x)
            
            self._model = SubtypeClassifier(backbone)
            
            # Load trained weights
            if os.path.exists(model_path):
                checkpoint = torch.load(model_path, map_location=self.device)
                # Handle different checkpoint formats
                if 'model_state_dict' in checkpoint:
                    self._model.load_state_dict(checkpoint['model_state_dict'])
                else:
                    self._model.load_state_dict(checkpoint)
                logger.info(f"Subtype classifier loaded from {model_path}")
            else:
                logger.warning(f"Subtype model file not found at {model_path}. Using untrained model.")
            
            self._model.to(self.device)
            self._model.eval()
            
        except Exception as e:
            logger.error(f"Error loading subtype model: {str(e)}")
            raise


class DetectionViewSet(viewsets.ModelViewSet):
    serializer_class = DetectionResultSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Return detection results for the current user"""
        user = self.request.user
        # Everyone should see detections where they are the patient
        queryset = DetectionResult.objects.filter(patient=user)
        
        if user.role == 'doctor':
            # Doctors also see detections assigned to them or through their appointments
            queryset |= DetectionResult.objects.filter(doctor=user) | DetectionResult.objects.filter(appointment__doctor=user)
            
        return queryset.distinct()
    
    def destroy(self, request, *args, **kwargs):
        """Only the doctor who ran the detection can delete it."""
        detection = self.get_object()
        if request.user.role != 'doctor' or detection.doctor_id != request.user.id:
            return Response(
                {'error': 'Only the owning doctor can delete this detection.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        # Clean up uploaded file from disk
        if detection.uploaded_file:
            try:
                path = detection.uploaded_file.path
                if os.path.exists(path):
                    os.remove(path)
            except Exception:
                pass
        detection.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
    
    @action(detail=False, methods=['post'], serializer_class=DetectionUploadSerializer)
    def upload_for_appointment(self, request):
        """
        Upload MRI scan for an approved appointment (patients only)
        Expected: multipart/form-data with 'uploaded_file' and 'appointment_id' fields
        """
        from .models import Appointment
        
        if request.user.role != 'patient':
            return Response(
                {'error': 'Only patients can upload MRI scans'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        appointment_id = request.data.get('appointment_id')
        if not appointment_id:
            return Response(
                {'error': 'Appointment ID is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Verify appointment exists and is approved
        try:
            appointment = Appointment.objects.get(
                id=appointment_id,
                patient=request.user
            )
        except Appointment.DoesNotExist:
            return Response(
                {'error': 'Appointment not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        if appointment.status != 'approved':
            return Response(
                {'error': 'Can only upload MRI for approved appointments'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if file was provided
        if 'uploaded_file' not in request.FILES:
            return Response(
                {'error': 'MRI file is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Create detection result linked to appointment
            detection_result = DetectionResult.objects.create(
                patient=request.user,
                doctor=appointment.doctor,
                appointment=appointment,
                uploaded_file=request.FILES['uploaded_file'],
                file_size=request.FILES['uploaded_file'].size,
                notes=request.data.get('notes', ''),
                status='pending',  # Will be processed by doctor
            )
            
            return Response({
                'message': 'MRI scan uploaded successfully',
                'detection_id': detection_result.detection_id,
                'status': detection_result.status
            }, status=status.HTTP_201_CREATED)
        
        except Exception as e:
            logger.error(f"Upload error: {str(e)}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['post'])
    def run_detection(self, request, pk=None):
        """
        Run AI detection on uploaded MRI (doctors only)
        """
        if request.user.role != 'doctor':
            return Response(
                {'error': 'Only doctors can run detection'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        detection_result = self.get_object()
        
        # Verify doctor has access (their appointment)
        if detection_result.appointment and detection_result.appointment.doctor != request.user:
            return Response(
                {'error': 'You can only process your own patients\' scans'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        if detection_result.status == 'completed':
            return Response(
                {'error': 'Detection already completed'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            detection_result.status = 'processing'
            detection_result.doctor = request.user
            detection_result.save()
            
            # Process the image and run model
            start_time = time.time()
            result = self._process_image(detection_result)
            processing_time = time.time() - start_time

            _finalize_detection_from_inference(detection_result, result, processing_time)
            detection_result.refresh_from_db()

            return Response(
                DetectionResultSerializer(detection_result).data,
                status=status.HTTP_200_OK
            )

        except Exception as e:
            try:
                detection_result.status = 'failed'
                detection_result.error_message = str(e)
                detection_result.save()
            except Exception:
                logger.exception('Could not persist failed detection status')
            logger.error(f"Detection error: {str(e)}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['post'])
    def generate_fhir_report(self, request, pk=None):
        """
        Generate FHIR Diagnostic Report for a completed detection (doctors only)
        """
        from .models import FHIRDiagnosticReport
        from django.utils import timezone
        
        if request.user.role != 'doctor':
            return Response(
                {'error': 'Only doctors can generate FHIR reports'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        detection_result = self.get_object()
        
        if detection_result.status != 'completed':
            return Response(
                {'error': 'Detection must be completed before generating report'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if report already exists
        if hasattr(detection_result, 'fhir_report'):
            return Response(
                {'error': 'FHIR report already exists for this detection'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Require doctor review before FHIR generation
        if not hasattr(detection_result, 'doctor_review'):
            return Response(
                {'error': 'Please write a clinical review before generating a FHIR report.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            review = detection_result.doctor_review
            self._sync_fhir_report(detection_result, review, request.user)
            
            from .serializers import FHIRDiagnosticReportSerializer
            return Response(
                FHIRDiagnosticReportSerializer(fhir_report).data,
                status=status.HTTP_201_CREATED
            )
        
        except Exception as e:
            logger.error(f"FHIR report generation error: {str(e)}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['post'], serializer_class=DetectionUploadSerializer)
    def upload_and_detect(self, request):
        """
        Upload MRI image and run detection
        Expected: multipart/form-data with 'uploaded_file' field and optional 'model_type' field
        model_type: 'binary' (default) or 'subtype'
        """
        serializer = DetectionUploadSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        # Get model_type from request, default to 'binary'
        model_type = request.data.get('model_type', 'binary')
        if model_type not in ['binary', 'subtype']:
            model_type = 'binary'
        
        try:
            # Extract patient_id if provided (required for doctors)
            patient_id = request.data.get('patient_id')
            patient = request.user
            
            if request.user.role == 'doctor':
                if not patient_id:
                    return Response({'error': 'patient_id is required for doctors'}, status=status.HTTP_400_BAD_REQUEST)
                from authx.models import User
                try:
                    patient = User.objects.get(id=patient_id, role='patient')
                except User.DoesNotExist:
                    return Response({'error': 'Selected patient not found'}, status=status.HTTP_400_BAD_REQUEST)

            # Create detection result record
            create_params = {
                'patient': patient,
                'uploaded_file': serializer.validated_data['uploaded_file'],
                'file_size': request.FILES['uploaded_file'].size,
                'patient_age': serializer.validated_data.get('patient_age'),
                'patient_gender': serializer.validated_data.get('patient_gender'),
                'notes': serializer.validated_data.get('notes'),
                'model_type': model_type,
                'status': 'processing',
            }
            
            # If a doctor is performing the detection, set them as the doctor too
            if request.user.role == 'doctor':
                create_params['doctor'] = request.user
                
            detection_result = DetectionResult.objects.create(**create_params)
            
            # Process the image and run model
            start_time = time.time()
            result = self._process_image(detection_result)
            processing_time = time.time() - start_time

            _finalize_detection_from_inference(detection_result, result, processing_time)
            detection_result.refresh_from_db()

            return Response(
                DetectionResultSerializer(detection_result).data,
                status=status.HTTP_201_CREATED
            )

        except Exception as e:
            dr = locals().get('detection_result')
            if dr is not None:
                try:
                    dr.status = 'failed'
                    dr.error_message = str(e)
                    dr.save()
                except Exception:
                    logger.exception('Could not persist failed detection status')
            logger.error(f"Detection error: {str(e)}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def _nifti_slice_to_pil(self, data_3d, slice_idx):
        """Convert a single axial slice from a 3D volume to a PIL RGB Image."""
        slice_data = data_3d[:, :, slice_idx]
        s_min, s_max = slice_data.min(), slice_data.max()
        if s_max > s_min:
            normalized = ((slice_data - s_min) / (s_max - s_min) * 255).astype(np.uint8)
        else:
            normalized = np.zeros_like(slice_data, dtype=np.uint8)
        return Image.fromarray(normalized).convert('RGB')

    def _load_nifti_slice(self, nifti_path):
        """Load NIfTI file and extract middle axial slice as PIL Image"""
        try:
            # Load NIfTI file
            nii = nib.load(nifti_path)
            data = nii.get_fdata()
            
            # Extract middle axial slice (along z-axis)
            # You can adjust the axis based on your data orientation
            middle_slice_idx = data.shape[2] // 2
            slice_data = data[:, :, middle_slice_idx]
            
            # Normalize to 0-255 range
            slice_min = slice_data.min()
            slice_max = slice_data.max()
            if slice_max > slice_min:
                normalized = ((slice_data - slice_min) / (slice_max - slice_min) * 255).astype(np.uint8)
            else:
                normalized = np.zeros_like(slice_data, dtype=np.uint8)
            
            # Convert to PIL Image and ensure RGB
            image = Image.fromarray(normalized)
            image = image.convert('RGB')
            
            logger.info(f"Loaded NIfTI slice from {nifti_path}, shape: {slice_data.shape}")
            return image
            
        except Exception as e:
            logger.error(f"Error loading NIfTI file: {str(e)}")
            raise ValueError(f"Failed to process NIfTI file: {str(e)}")
    
    def _run_pipeline(self, file_path: str) -> str:
        """Run the preprocessing pipeline on a NIfTI or DICOM file.

        DICOM / ZIP  → Phase 1 (DICOM→NIfTI) then Phase 2 (steps 4-8)
        NIfTI        → Phase 2 only

        Returns the path to the preprocessed 128×128×128 NIfTI.
        Falls back to the original file if the pipeline fails.
        """
        try:
            from pipeline.preprocess import preprocess_mri
            work_dir = os.path.join(
                os.path.dirname(file_path), "pipeline_work"
            )
            preprocessed = preprocess_mri(file_path, output_dir=work_dir)
            logger.info("Pipeline preprocessing complete: %s", preprocessed)
            return preprocessed
        except Exception as e:
            logger.warning("Pipeline preprocessing failed: %s", e)
            raise

    @staticmethod
    def _is_mri_file(path: str) -> bool:
        lp = path.lower()
        return (lp.endswith('.nii') or lp.endswith('.nii.gz')
                or lp.endswith('.dcm') or lp.endswith('.zip'))

    @staticmethod
    def _is_nifti_path(path: str) -> bool:
        if not path:
            return False
        lp = path.lower()
        return lp.endswith('.nii') or lp.endswith('.nii.gz')

    def _find_pipeline_output_nifti(self, upload_abs_path: str) -> str | None:
        """Locate a preprocessed NIfTI left under pipeline_work next to the upload."""
        if not upload_abs_path:
            return None
        work = os.path.join(os.path.dirname(upload_abs_path), 'pipeline_work')
        if not os.path.isdir(work):
            return None
        candidates: list[str] = []
        for root, _dirs, files in os.walk(work):
            for f in files:
                fl = f.lower()
                if fl.endswith('.nii.gz') or (
                    fl.endswith('.nii') and not fl.endswith('.nii.gz')
                ):
                    candidates.append(os.path.join(root, f))
        if not candidates:
            return None
        candidates.sort(key=lambda p: os.path.getmtime(p), reverse=True)
        return candidates[0]

    def _resolve_nifti_path_for_detection(self, detection_result) -> str:
        """
        Return an on-disk path to a NIfTI produced for this detection.
        Handles relative paths in preprocessed_file, stale ZIP paths in DB,
        and pipeline_work artifacts when the original ZIP was removed.
        """
        paths_to_try: list[str] = []
        prep = (getattr(detection_result, 'preprocessed_file', None) or '').strip()
        if prep:
            paths_to_try.append(prep)
            if not os.path.isabs(prep):
                media_root = str(getattr(settings, 'MEDIA_ROOT', '') or '')
                if media_root:
                    paths_to_try.append(
                        os.path.normpath(os.path.join(media_root, prep.lstrip('/')))
                    )
        try:
            up = detection_result.uploaded_file.path
        except Exception:
            up = ''
        if up:
            residual = self._find_pipeline_output_nifti(up)
            if residual:
                paths_to_try.append(residual)

        seen: set[str] = set()
        for p in paths_to_try:
            if not p or p in seen:
                continue
            seen.add(p)
            if self._is_nifti_path(p) and os.path.isfile(p):
                return p
        return ''

    def _process_image(self, detection_result):
        """Process image and run model inference based on model_type"""
        _ensure_ml_libs()
        try:
            image_path = detection_result.uploaded_file.path
            needs_pipeline = self._is_mri_file(image_path)

            if needs_pipeline:
                preprocessed_path = self._run_pipeline(image_path)
                # Save the preprocessed path for future re-runs
                detection_result.preprocessed_file = preprocessed_path
                detection_result.save(update_fields=['preprocessed_file'])
                image = self._load_nifti_slice(preprocessed_path)
            else:
                image = Image.open(image_path).convert('RGB')

            transform = transforms.Compose([
                transforms.Resize((224, 224)),
                transforms.ToTensor(),
                transforms.Normalize(
                    mean=[0.485, 0.456, 0.406],
                    std=[0.229, 0.224, 0.225]
                )
            ])

            image_tensor = transform(image).unsqueeze(0)
            
            # Select model based on model_type
            model_type = getattr(detection_result, 'model_type', 'binary')
            
            if model_type == 'subtype':
                return self._run_subtype_inference(image_tensor, needs_pipeline)
            else:
                return self._run_binary_inference(image_tensor, needs_pipeline)

        except Exception as e:
            logger.error(f"Image processing error: {str(e)}")
            raise
    
    def _run_binary_inference(self, image_tensor, needs_pipeline):
        """Run binary dementia detector inference"""
        model_loader = ModelLoader()
        model = model_loader.model
        device = model_loader.device

        image_tensor = image_tensor.to(device)

        with torch.no_grad():
            output = model(image_tensor)
            probability = torch.sigmoid(output).item()
            
        import math
        if math.isnan(probability):
            raise ValueError("AI model returned an invalid result (NaN). The input image may be blank or corrupted.")

        threshold = 0.5
        predicted_class = 'dementia' if probability >= threshold else 'cn'

        return {
            'predicted_class': predicted_class,
            'confidence': max(probability, 1 - probability),
            'probabilities': {
                'dementia': float(probability),
                'cn': float(1 - probability),
            },
            'analysis': {
                'raw_output': float(output.item()),
                'sigmoid_probability': float(probability),
                'threshold_used': threshold,
                'model_version': 'Binary-ResNet-34-v1.0',
                'model_type': 'binary',
                'pipeline_preprocessing': needs_pipeline,
            }
        }
    
    def _run_subtype_inference(self, image_tensor, needs_pipeline):
        """Run 4-class subtype classifier inference"""
        model_loader = SubtypeModelLoader()
        model = model_loader.model
        device = model_loader.device

        image_tensor = image_tensor.to(device)

        with torch.no_grad():
            output = model(image_tensor)
            probabilities = torch.softmax(output, dim=1).squeeze()
            
        if torch.isnan(probabilities).any():
            raise ValueError("AI model returned an invalid result (NaN). The input image may be blank or corrupted.")
        
        # Get predicted class (argmax)
        predicted_idx = torch.argmax(probabilities).item()
        class_names = SubtypeModelLoader.CLASS_NAMES  # ['ad', 'pd', 'ftd', 'cn']
        
        # Map to database field names
        class_mapping = {'ad': 'alzheimers', 'pd': 'pd', 'ftd': 'ftd', 'cn': 'cn'}
        predicted_class = class_mapping[class_names[predicted_idx]]
        confidence = probabilities[predicted_idx].item()

        return {
            'predicted_class': predicted_class,
            'confidence': float(confidence),
            'probabilities': {
                'alzheimers': float(probabilities[0].item()),  # AD
                'pd': float(probabilities[1].item()),          # PD
                'ftd': float(probabilities[2].item()),         # FTD
                'cn': float(probabilities[3].item()),          # CN
            },
            'analysis': {
                'raw_output': [float(x) for x in output.squeeze().tolist()],
                'softmax_probabilities': [float(x) for x in probabilities.tolist()],
                'predicted_index': predicted_idx,
                'model_version': 'Subtype-ResNet-34-v1.0',
                'model_type': 'subtype',
                'pipeline_preprocessing': needs_pipeline,
            }
        }
    
    @action(detail=False, methods=['get'])
    def history(self, request):
        """Get user's detection history"""
        detections = self.get_queryset()
        serializer = self.get_serializer(detections, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'], url_path='my_uploads')
    def my_uploads(self, request):
        """Get completed detections uploaded by the current doctor (for reuse)."""
        if request.user.role != 'doctor':
            return Response({'error': 'Doctors only'}, status=status.HTTP_403_FORBIDDEN)
        detections = DetectionResult.objects.filter(
            doctor=request.user,
            status='completed',
        ).order_by('-created_at')
        serializer = self.get_serializer(detections, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'], url_path='rerun')
    def rerun_detection(self, request, pk=None):
        """Re-run inference on an already preprocessed MRI, skipping the pipeline.
        Expects: { model_type }
        The patient is inherited from the source detection.
        """
        if request.user.role != 'doctor':
            return Response({'error': 'Doctors only'}, status=status.HTTP_403_FORBIDDEN)

        source = self.get_object()
        if source.doctor_id != request.user.id:
            return Response({'error': 'You can only reuse your own uploads'}, status=status.HTTP_403_FORBIDDEN)

        model_type = request.data.get('model_type', 'binary')
        if model_type not in ['binary', 'subtype']:
            model_type = 'binary'

        try:
            # Create a new DetectionResult reusing the same patient and file.
            # Point at the same stored upload as `source` (same `name` in storage). Using
            # `uploaded_file=source.uploaded_file.name` alone breaks FieldFile behavior
            # on some storages and reruns.
            new_detection = DetectionResult(
                patient=source.patient,
                doctor=request.user,
                preprocessed_file=source.preprocessed_file,
                file_size=source.file_size,
                model_type=model_type,
                status='processing',
            )
            new_detection.uploaded_file.name = source.uploaded_file.name
            new_detection.save()

            _ensure_ml_libs()
            start_time = time.time()

            nifti_path = self._resolve_nifti_path_for_detection(source)
            if nifti_path:
                logger.info("Rerun: loading NIfTI: %s", nifti_path)
                image = self._load_nifti_slice(nifti_path)
                new_detection.preprocessed_file = nifti_path
            else:
                # Fallback: run the pipeline if no usable NIfTI on disk
                image_path = source.uploaded_file.path
                needs_pipeline = self._is_mri_file(image_path)
                if needs_pipeline:
                    if not os.path.isfile(image_path):
                        raise ValueError(
                            'Original upload missing and no preprocessed NIfTI found.'
                        )
                    preprocessed_path = self._run_pipeline(image_path)
                    if not self._is_nifti_path(preprocessed_path):
                        raise ValueError('Preprocessing did not produce a NIfTI file.')
                    new_detection.preprocessed_file = preprocessed_path
                    image = self._load_nifti_slice(preprocessed_path)
                else:
                    image = Image.open(image_path).convert('RGB')

            transform = transforms.Compose([
                transforms.Resize((224, 224)),
                transforms.ToTensor(),
                transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
            ])
            image_tensor = transform(image).unsqueeze(0)

            if model_type == 'subtype':
                result = self._run_subtype_inference(image_tensor, False)
            else:
                result = self._run_binary_inference(image_tensor, False)

            processing_time = time.time() - start_time

            _finalize_detection_from_inference(new_detection, result, processing_time)
            new_detection.refresh_from_db()

            return Response(DetectionResultSerializer(new_detection).data, status=status.HTTP_201_CREATED)

        except ValueError as e:
            logger.warning('Rerun detection validation error: %s', str(e))
            nd = locals().get('new_detection')
            if nd is not None:
                try:
                    nd.status = 'failed'
                    nd.error_message = str(e)
                    nd.save()
                except Exception:
                    logger.exception('Could not persist rerun failure')
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Rerun detection error: {str(e)}")
            nd = locals().get('new_detection')
            if nd is not None:
                try:
                    nd.status = 'failed'
                    nd.error_message = str(e)
                    nd.save()
                except Exception:
                    logger.exception('Could not persist rerun failure')
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Get user's detection statistics"""
        detections = self.get_queryset()
        total = detections.count()
        completed = detections.filter(status='completed').count()
        ad_cases = detections.filter(status='completed', predicted_class__in=['alzheimers', 'dementia']).count()
        cn_cases = detections.filter(status='completed', predicted_class='cn').count()
        pd_cases = detections.filter(status='completed', predicted_class='pd').count()
        ftd_cases = detections.filter(status='completed', predicted_class='ftd').count()
        
        return Response({
            'total_detections': total,
            'completed': completed,
            'alzheimers_cases': ad_cases,
            'control_cases': cn_cases,
            'parkinsons_cases': pd_cases,
            'ftd_cases': ftd_cases,
            'ad_percentage': (ad_cases / completed * 100) if completed > 0 else 0,
        })
    
    def _sync_fhir_report(self, detection, review, doctor):
        """Create or update a FHIR report that includes the doctor's review comments."""
        from .models import FHIRDiagnosticReport
        from django.utils import timezone

        final_class = review.doctor_override_class if (not review.ai_accepted and review.doctor_override_class) else detection.predicted_class
        confidence = detection.confidence_score or 0

        CLASS_MAP = {
            'alzheimers': ("Alzheimer's Disease", '26929004', "Alzheimer's disease"),
            'pd': ("Parkinson's Disease", '49049000', "Parkinson's disease"),
            'ftd': ("Frontotemporal Dementia", '230270009', "Frontotemporal dementia"),
            'dementia': ("Dementia", '52448006', "Dementia"),
            'cn': ("Normal/Control", '17621005', "Normal"),
        }
        label, code, display = CLASS_MAP.get(final_class, ("Unknown", '261665006', "Unknown"))

        conclusion = review.doctor_conclusion or f"AI-assisted analysis indicates possible {label} with {confidence:.1%} confidence."
        conclusion_codes = [{'system': 'http://snomed.info/sct', 'code': code, 'display': display}]

        try:
            fhir_report = detection.fhir_report
            fhir_report.conclusion = conclusion
            fhir_report.conclusion_code = conclusion_codes
            fhir_report.status = 'final'
        except FHIRDiagnosticReport.DoesNotExist:
            fhir_report = FHIRDiagnosticReport(
                detection=detection,
                patient=detection.patient,
                doctor=doctor,
                status='final',
                effective_datetime=detection.upload_date,
                conclusion=conclusion,
                conclusion_code=conclusion_codes,
                hospital_name='DementiaNext AI Diagnostic Center',
                department='Neurology',
                category={'coding': [{'system': 'http://terminology.hl7.org/CodeSystem/v2-0074', 'code': 'RAD', 'display': 'Radiology'}]},
                code={'coding': [{'system': 'http://loinc.org', 'code': '30799-1', 'display': 'MRI Brain WO contrast'}]},
                subject={'reference': f'Patient/{detection.patient.id}', 'display': detection.patient.get_full_name()},
                performer=[{'reference': f'Practitioner/{doctor.id}', 'display': f'Dr. {doctor.get_full_name()}'}],
                result=[{'reference': f'Observation/{detection.detection_id}', 'display': f'AI Detection Result: {detection.get_predicted_class_display() if detection.predicted_class else "Pending"}'}],
                fhir_json={},
            )

        fhir_json = {
            'resourceType': 'DiagnosticReport',
            'id': fhir_report.report_id if fhir_report.pk else f'FHIR-{detection.detection_id}',
            'meta': {'versionId': '1', 'lastUpdated': timezone.now().isoformat()},
            'status': 'final',
            'category': [fhir_report.category] if isinstance(fhir_report.category, dict) else fhir_report.category,
            'code': fhir_report.code,
            'subject': fhir_report.subject,
            'effectiveDateTime': (fhir_report.effective_datetime or timezone.now()).isoformat(),
            'issued': timezone.now().isoformat(),
            'performer': fhir_report.performer,
            'result': fhir_report.result,
            'conclusion': conclusion,
            'conclusionCode': conclusion_codes,
            'doctorReview': {
                'aiAccepted': review.ai_accepted,
                'overrideDiagnosis': review.doctor_override_class if not review.ai_accepted else None,
                'clinicalConclusion': review.doctor_conclusion,
                'patientSummary': review.patient_summary,
                'reviewedAt': review.updated_at.isoformat() if review.updated_at else timezone.now().isoformat(),
            },
        }
        fhir_report.fhir_json = fhir_json
        fhir_report.save()

        if detection.appointment:
            detection.appointment.status = 'completed'
            detection.appointment.save()

    @action(detail=True, methods=['get', 'post'])
    def review(self, request, pk=None):
        """GET / POST doctor's clinical review for a detection."""
        detection = self.get_object()
        
        # Only the doctor who ran the detection can review it, or someone with access.
        # But let's allow doctors.
        if request.user.role != 'doctor':
            return Response({'error': 'Only doctors can add reviews'}, status=status.HTTP_403_FORBIDDEN)

        # GET: retrieve existing review
        if request.method == 'GET':
            try:
                review = DoctorReview.objects.get(detection=detection)
                serializer = DoctorReviewSerializer(review)
                return Response(serializer.data)
            except DoctorReview.DoesNotExist:
                return Response({'detail': 'No review exists for this detection yet.'}, status=status.HTTP_404_NOT_FOUND)

        # POST: create or update review
        # Note: if it exists, we update. Otherwise create.
        try:
            review = DoctorReview.objects.get(detection=detection)
            # Check auth
            if review.doctor != request.user:
                return Response({'error': 'You can only edit your own reviews'}, status=status.HTTP_403_FORBIDDEN)
        except DoctorReview.DoesNotExist:
            review = DoctorReview(
                detection=detection,
                doctor=request.user,
                patient=detection.patient
            )

        # Update fields
        review.ai_accepted = request.data.get('ai_accepted', review.ai_accepted)
        review.doctor_override_class = request.data.get('doctor_override_class', review.doctor_override_class or '')
        review.doctor_conclusion = request.data.get('doctor_conclusion', review.doctor_conclusion)
        review.doctor_notes = request.data.get('doctor_notes', review.doctor_notes)
        review.patient_summary = request.data.get('patient_summary', review.patient_summary)
        
        was_sent = review.is_sent_to_patient
        is_sent_now = request.data.get('is_sent_to_patient', review.is_sent_to_patient)
        
        from django.utils import timezone

        if is_sent_now and not was_sent:
            review.sent_at = timezone.now()
            
        review.is_sent_to_patient = is_sent_now
        review.save()

        # When sending to patient, auto-generate/update FHIR report with doctor's comments
        if is_sent_now:
            self._sync_fhir_report(detection, review, request.user)

        serializer = DoctorReviewSerializer(review)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def explainability(self, request, pk=None):
        """
        Generate Grad-CAM explainability visualization for a completed detection.
        Returns base64-encoded heatmap overlay and analysis details.
        """
        detection_result = self.get_object()
        
        if detection_result.status != 'completed':
            return Response(
                {'error': 'Detection must be completed before generating explainability'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            _ensure_ml_libs()
            from .xai import get_gradcam_for_detection
            
            # Load MRI slice: resolve real NIfTI (DB path, MEDIA-relative, or
            # pipeline_work) — never pass .zip to nibabel.
            nifti_path = self._resolve_nifti_path_for_detection(detection_result)
            if nifti_path:
                image = self._load_nifti_slice(nifti_path)
            else:
                image_path = detection_result.uploaded_file.path
                needs_pipeline = self._is_mri_file(image_path)
                if needs_pipeline:
                    if not os.path.isfile(image_path):
                        raise ValueError(
                            'The original scan file is no longer on disk and no '
                            'preprocessed NIfTI was found. Re-upload the MRI or pick '
                            'another detection.'
                        )
                    preprocessed_path = self._run_pipeline(image_path)
                    if not self._is_nifti_path(preprocessed_path):
                        raise ValueError('Preprocessing did not produce a NIfTI file.')
                    image = self._load_nifti_slice(preprocessed_path)
                else:
                    image = Image.open(image_path).convert('RGB')
            
            # Store original for visualization
            original_image = np.array(image)
            
            # Preprocess for model
            transform = transforms.Compose([
                transforms.Resize((224, 224)),
                transforms.ToTensor(),
                transforms.Normalize(
                    mean=[0.485, 0.456, 0.406],
                    std=[0.229, 0.224, 0.225]
                )
            ])
            image_tensor = transform(image).unsqueeze(0)
            
            # Get appropriate model
            model_type = getattr(detection_result, 'model_type', 'binary')
            is_binary = model_type == 'binary'
            
            if is_binary:
                model_loader = ModelLoader()
                class_names = ["Normal", "Dementia"]
            else:
                model_loader = SubtypeModelLoader()
                class_names = ["Alzheimer's Disease", "Parkinson's Disease", 
                              "Frontotemporal Dementia", "Normal/Control"]
            
            model = model_loader.model
            device = model_loader.device
            image_tensor = image_tensor.to(device)
            
            # Generate Grad-CAM
            gradcam_result = get_gradcam_for_detection(
                model=model,
                input_tensor=image_tensor,
                original_image=original_image,
                is_binary=is_binary,
                class_names=class_names,
            )
            
            # Build response with analysis
            response_data = {
                'detection_id': str(detection_result.detection_id),
                'predicted_class': detection_result.predicted_class,
                'confidence': detection_result.confidence_score,
                'gradcam': {
                    'overlay_base64': gradcam_result['overlay_base64'],
                    'heatmap_base64': gradcam_result['heatmap_base64'],
                    'original_base64': gradcam_result['original_base64'],
                    'target_layer': gradcam_result['layer_name'],
                    'gradcam_class': gradcam_result['predicted_class'],
                    'gradcam_class_name': gradcam_result['predicted_class_name'],
                    'gradcam_confidence': gradcam_result['confidence'],
                },
                'analysis': detection_result.analysis_details,
                'model_type': model_type,
            }
            
            return Response(response_data, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Explainability generation error: {str(e)}")
            return Response(
                {'error': f'Failed to generate explainability: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


    @action(detail=True, methods=['get'], url_path='explainability_slices')
    def explainability_slices(self, request, pk=None):
        """Generate Grad-CAM overlays for multiple axial slices so the
        frontend can render an interactive 3D slice explorer.

        Query params:
            num_slices - how many evenly-spaced slices to return (default 30, max 60)
        """
        detection_result = self.get_object()

        if detection_result.status != 'completed':
            return Response(
                {'error': 'Detection must be completed before generating explainability'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            _ensure_ml_libs()
            from .xai import get_gradcam_for_detection

            image_path = detection_result.uploaded_file.path
            needs_pipeline = self._is_mri_file(image_path)

            if not needs_pipeline:
                return Response(
                    {'error': 'Slice explorer is only available for 3D NIfTI MRI volumes'},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            model_type = getattr(detection_result, 'model_type', 'binary')
            is_binary = model_type == 'binary'

            if is_binary:
                model_loader = ModelLoader()
                class_names = ["Normal", "Dementia"]
            else:
                model_loader = SubtypeModelLoader()
                class_names = ["Alzheimer's Disease", "Parkinson's Disease",
                              "Frontotemporal Dementia", "Normal/Control"]

            model = model_loader.model
            device = model_loader.device

            transform = transforms.Compose([
                transforms.Resize((224, 224)),
                transforms.ToTensor(),
                transforms.Normalize(
                    mean=[0.485, 0.456, 0.406],
                    std=[0.229, 0.224, 0.225],
                ),
            ])

            nifti_path = self._resolve_nifti_path_for_detection(detection_result)
            if not nifti_path:
                image_path = detection_result.uploaded_file.path
                if not os.path.isfile(image_path):
                    raise ValueError('Original scan file not found on disk.')
                nifti_path = self._run_pipeline(image_path)

            nii = nib.load(nifti_path)
            volume = nii.get_fdata()
            total_slices = volume.shape[2]

            num_slices = min(int(request.query_params.get('num_slices', 30)), 60)
            margin = int(total_slices * 0.10)
            start = max(margin, 0)
            end = min(total_slices - margin, total_slices)
            if end <= start:
                start, end = 0, total_slices

            step = max((end - start) // num_slices, 1)
            indices = list(range(start, end, step))[:num_slices]

            slices_data = []
            best_idx = None
            best_conf = -1.0

            model.eval()
            for idx in indices:
                pil_img = self._nifti_slice_to_pil(volume, idx)
                image_tensor = transform(pil_img).unsqueeze(0).to(device)

                gradcam_result = get_gradcam_for_detection(
                    model=model,
                    input_tensor=image_tensor,
                    original_image=np.array(pil_img),
                    is_binary=is_binary,
                    class_names=class_names,
                )

                conf = gradcam_result['confidence']
                if conf > best_conf:
                    best_conf = conf
                    best_idx = idx

                slices_data.append({
                    'index': idx,
                    'original_base64': gradcam_result['original_base64'],
                    'overlay_base64': gradcam_result['overlay_base64'],
                    'heatmap_base64': gradcam_result['heatmap_base64'],
                    'confidence': conf,
                    'predicted_class_name': gradcam_result['predicted_class_name'],
                })

            return Response({
                'detection_id': str(detection_result.detection_id),
                'predicted_class': detection_result.predicted_class,
                'confidence': detection_result.confidence_score,
                'model_type': model_type,
                'total_slices': total_slices,
                'best_slice_index': best_idx,
                'slices': slices_data,
            }, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error("Slice explainability error: %s", e)
            return Response(
                {'error': f'Failed to generate slice explainability: {e}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class ModelMetadataViewSet(viewsets.ReadOnlyModelViewSet):
    """View active models metadata"""
    queryset = ModelMetadata.objects.filter(is_active=True)
    serializer_class = ModelMetadataSerializer
    permission_classes = [IsAuthenticated]


class PatientReportViewSet(viewsets.GenericViewSet):
    """Patient-facing endpoint to retrieve doctor reports sent to them."""
    permission_classes = [IsAuthenticated]
    serializer_class = PatientVisibleReviewSerializer

    @action(detail=False, methods=['get'], url_path='mine')
    def my_reports(self, request):
        """GET /api/detection/patient-reports/mine/"""
        reviews = DoctorReview.objects.filter(
            patient=request.user,
            is_sent_to_patient=True,
        ).select_related('doctor', 'detection').order_by('-sent_at')
        serializer = self.get_serializer(reviews, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'], url_path='fhir')
    def fhir_download(self, request, pk=None):
        """GET /api/detection/patient-reports/<review_id>/fhir/
        Returns the FHIR JSON for a report that has been sent to the patient."""
        try:
            review = DoctorReview.objects.select_related('detection').get(
                pk=pk, patient=request.user, is_sent_to_patient=True
            )
        except DoctorReview.DoesNotExist:
            return Response({'error': 'Report not found'}, status=status.HTTP_404_NOT_FOUND)

        try:
            fhir_report = review.detection.fhir_report
            return Response(fhir_report.fhir_json or {})
        except Exception:
            return Response({'error': 'No FHIR report available'}, status=status.HTTP_404_NOT_FOUND)
