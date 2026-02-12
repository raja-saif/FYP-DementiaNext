import os
import time
import torch
import numpy as np
import nibabel as nib
from PIL import Image
from io import BytesIO
from django.conf import settings
from django.core.files.storage import default_storage
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import DetectionResult, ModelMetadata
from .serializers import DetectionResultSerializer, DetectionUploadSerializer, ModelMetadataSerializer
from torchvision import transforms
from torchvision.models import resnet34
import logging

logger = logging.getLogger(__name__)


class ModelLoader:
    """Singleton for loading and caching the trained model"""
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
        """Load the trained ResNet-34 model"""
        try:
            # Model path - adjust to your actual model location
            model_path = os.path.join(settings.BASE_DIR, 'models', 'alzheimers_detector.pth')
            
            # Initialize ResNet-34 backbone
            backbone = resnet34(pretrained=False)
            
            # Replace final layer for binary classification
            num_features = backbone.fc.in_features
            backbone.fc = torch.nn.Sequential(
                torch.nn.Dropout(0.5),
                torch.nn.Linear(num_features, 1)
            )
            
            # Wrap in the same structure used during training
            class AlzheimerDetector(torch.nn.Module):
                def __init__(self, backbone):
                    super().__init__()
                    self.backbone = backbone
                
                def forward(self, x):
                    return self.backbone(x)
            
            self._model = AlzheimerDetector(backbone)
            
            # Load trained weights
            if os.path.exists(model_path):
                checkpoint = torch.load(model_path, map_location=self.device)
                self._model.load_state_dict(checkpoint['model_state_dict'])
                logger.info(f"Model loaded from {model_path}")
            else:
                logger.warning(f"Model file not found at {model_path}. Using untrained model.")
            
            self._model.to(self.device)
            self._model.eval()
            
        except Exception as e:
            logger.error(f"Error loading model: {str(e)}")
            raise


class DetectionViewSet(viewsets.ModelViewSet):
    serializer_class = DetectionResultSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Return detection results for the current user"""
        user = self.request.user
        if user.role == 'doctor':
            # Doctors see detections for their appointments
            return DetectionResult.objects.filter(doctor=user) | DetectionResult.objects.filter(appointment__doctor=user)
        return DetectionResult.objects.filter(patient=user)
    
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
            
            # Update result
            detection_result.status = 'completed'
            detection_result.predicted_class = result['predicted_class']
            detection_result.confidence_score = result['confidence']
            detection_result.prediction_probability = result['probabilities']
            detection_result.analysis_details = result['analysis']
            detection_result.processing_time = processing_time
            detection_result.save()
            
            return Response(
                DetectionResultSerializer(detection_result).data,
                status=status.HTTP_200_OK
            )
        
        except Exception as e:
            detection_result.status = 'failed'
            detection_result.error_message = str(e)
            detection_result.save()
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
        
        try:
            # Generate conclusion based on detection result
            if detection_result.predicted_class == 'alzheimers':
                conclusion = f"AI-assisted analysis indicates possible Alzheimer's Disease with {detection_result.confidence_score:.1%} confidence. Further clinical evaluation recommended."
                conclusion_codes = [{'system': 'http://snomed.info/sct', 'code': '26929004', 'display': "Alzheimer's disease"}]
            else:
                conclusion = f"AI-assisted analysis indicates Normal/Control findings with {detection_result.confidence_score:.1%} confidence. No significant abnormalities detected."
                conclusion_codes = [{'system': 'http://snomed.info/sct', 'code': '17621005', 'display': 'Normal'}]
            
            # Create FHIR report
            fhir_report = FHIRDiagnosticReport.objects.create(
                detection=detection_result,
                patient=detection_result.patient,
                doctor=request.user,
                status='final',
                effective_datetime=detection_result.upload_date,
                conclusion=conclusion,
                conclusion_code=conclusion_codes,
                hospital_name=request.data.get('hospital_name', 'DementiaNext AI Diagnostic Center'),
                department='Neurology',
                category={
                    'coding': [{'system': 'http://terminology.hl7.org/CodeSystem/v2-0074', 'code': 'RAD', 'display': 'Radiology'}]
                },
                code={
                    'coding': [{'system': 'http://loinc.org', 'code': '30799-1', 'display': 'MRI Brain WO contrast'}]
                },
                subject={
                    'reference': f'Patient/{detection_result.patient.id}',
                    'display': detection_result.patient.get_full_name()
                },
                performer=[{
                    'reference': f'Practitioner/{request.user.id}',
                    'display': f'Dr. {request.user.get_full_name()}'
                }],
                result=[{
                    'reference': f'Observation/{detection_result.detection_id}',
                    'display': f'AI Detection Result: {detection_result.get_predicted_class_display() if detection_result.predicted_class else "Pending"}'
                }],
                fhir_json={}  # Will be populated below
            )
            
            # Generate complete FHIR JSON
            fhir_json = {
                'resourceType': 'DiagnosticReport',
                'id': fhir_report.report_id,
                'meta': {
                    'versionId': '1',
                    'lastUpdated': timezone.now().isoformat()
                },
                'status': fhir_report.status,
                'category': [fhir_report.category],
                'code': fhir_report.code,
                'subject': fhir_report.subject,
                'effectiveDateTime': (fhir_report.effective_datetime or timezone.now()).isoformat(),
                'issued': (fhir_report.issued or timezone.now()).isoformat(),
                'performer': fhir_report.performer,
                'result': fhir_report.result,
                'conclusion': fhir_report.conclusion,
                'conclusionCode': fhir_report.conclusion_code
            }
            
            fhir_report.fhir_json = fhir_json
            fhir_report.save()
            
            # Mark appointment as completed if linked
            if detection_result.appointment:
                detection_result.appointment.status = 'completed'
                detection_result.appointment.save()
            
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
        Expected: multipart/form-data with 'uploaded_file' field
        """
        serializer = DetectionUploadSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # Create detection result record
            detection_result = DetectionResult.objects.create(
                patient=request.user,
                uploaded_file=serializer.validated_data['uploaded_file'],
                file_size=request.FILES['uploaded_file'].size,
                patient_age=serializer.validated_data.get('patient_age'),
                patient_gender=serializer.validated_data.get('patient_gender'),
                notes=serializer.validated_data.get('notes'),
                status='processing',
            )
            
            # Process the image and run model
            start_time = time.time()
            result = self._process_image(detection_result)
            processing_time = time.time() - start_time
            
            # Update result
            detection_result.status = 'completed'
            detection_result.predicted_class = result['predicted_class']
            detection_result.confidence_score = result['confidence']
            detection_result.prediction_probability = result['probabilities']
            detection_result.analysis_details = result['analysis']
            detection_result.processing_time = processing_time
            detection_result.save()
            
            return Response(
                DetectionResultSerializer(detection_result).data,
                status=status.HTTP_201_CREATED
            )
        
        except Exception as e:
            detection_result.status = 'failed'
            detection_result.error_message = str(e)
            detection_result.save()
            logger.error(f"Detection error: {str(e)}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
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
    
    def _process_image(self, detection_result):
        """Process image and run model inference"""
        try:
            # Load image
            image_path = detection_result.uploaded_file.path
            
            # Check if file is NIfTI format
            if image_path.endswith('.nii') or image_path.endswith('.nii.gz'):
                image = self._load_nifti_slice(image_path)
            else:
                image = Image.open(image_path).convert('RGB')
            
            # Image preprocessing
            transform = transforms.Compose([
                transforms.Resize((224, 224)),
                transforms.ToTensor(),
                transforms.Normalize(
                    mean=[0.485, 0.456, 0.406],
                    std=[0.229, 0.224, 0.225]
                )
            ])
            
            image_tensor = transform(image).unsqueeze(0)
            
            # Load model and run inference
            model_loader = ModelLoader()
            model = model_loader.model
            device = model_loader.device
            
            image_tensor = image_tensor.to(device)
            
            with torch.no_grad():
                output = model(image_tensor)
                probability = torch.sigmoid(output).item()
            
            # Determine class based on probability threshold (0.5)
            # Store the choice keys used across the app: 'alzheimers' or 'cn'
            threshold = 0.5
            predicted_class = 'alzheimers' if probability >= threshold else 'cn'
            
            return {
                'predicted_class': predicted_class,
                'confidence': max(probability, 1 - probability),
                'probabilities': {
                    'alzheimers': float(probability),
                    'cn': float(1 - probability),
                },
                'analysis': {
                    'raw_output': float(output.item()),
                    'sigmoid_probability': float(probability),
                    'threshold_used': threshold,
                    'model_version': 'ResNet-34-v1.0',
                }
            }
        
        except Exception as e:
            logger.error(f"Image processing error: {str(e)}")
            raise
    
    @action(detail=False, methods=['get'])
    def history(self, request):
        """Get user's detection history"""
        detections = self.get_queryset()
        serializer = self.get_serializer(detections, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Get user's detection statistics"""
        detections = self.get_queryset()
        total = detections.count()
        completed = detections.filter(status='completed').count()
        ad_cases = detections.filter(status='completed', predicted_class='alzheimers').count()
        cn_cases = detections.filter(status='completed', predicted_class='cn').count()
        
        return Response({
            'total_detections': total,
            'completed': completed,
            'alzheimers_cases': ad_cases,
            'control_cases': cn_cases,
            'ad_percentage': (ad_cases / completed * 100) if completed > 0 else 0,
        })


class ModelMetadataViewSet(viewsets.ReadOnlyModelViewSet):
    """View active models metadata"""
    queryset = ModelMetadata.objects.filter(is_active=True)
    serializer_class = ModelMetadataSerializer
    permission_classes = [IsAuthenticated]
