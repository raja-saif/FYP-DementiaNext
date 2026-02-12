"""
Unit tests for detection serializers
Tests DetectionResultSerializer, DetectionUploadSerializer, and ModelMetadataSerializer
"""
import io
from datetime import datetime
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIRequestFactory
from detection.models import DetectionResult, ModelMetadata
from detection.serializers import (
    DetectionResultSerializer, 
    DetectionUploadSerializer,
    ModelMetadataSerializer
)

User = get_user_model()


class DetectionResultSerializerTests(TestCase):
    """Unit tests for DetectionResultSerializer"""
    
    def setUp(self):
        """Set up test users and detection results"""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            first_name='Test User'
        )
        
        self.test_file = SimpleUploadedFile(
            "test_mri.jpg",
            b"fake image content",
            content_type="image/jpeg"
        )
        
        self.detection = DetectionResult.objects.create(
            user=self.user,
            uploaded_file=self.test_file,
            file_size=1024,
            status='completed',
            predicted_class='Alzheimer\'s Disease (AD)',
            confidence_score=0.89,
            prediction_probability={'AD': 0.89, 'CN': 0.11},
            model_version='v1.0',
            processing_time=1.2,
            analysis_details={'model': 'ResNet-34'},
            patient_age=68,
            patient_gender='Female'
        )
    
    def test_serializer_contains_expected_fields(self):
        """Test serializer returns all expected fields"""
        serializer = DetectionResultSerializer(self.detection)
        data = serializer.data
        
        expected_fields = {
            'id', 'user_username', 'status', 'predicted_class',
            'confidence_score', 'prediction_probability', 'model_version',
            'processing_time', 'analysis_details', 'patient_age',
            'patient_gender', 'notes', 'clinician_notes', 'upload_date',
            'created_at', 'updated_at'
        }
        
        self.assertEqual(set(data.keys()), expected_fields)
    
    def test_serializer_user_username_field(self):
        """Test user_username field shows username correctly"""
        serializer = DetectionResultSerializer(self.detection)
        self.assertEqual(serializer.data['user_username'], 'testuser')
    
    def test_serializer_read_only_fields(self):
        """Test that read-only fields cannot be modified"""
        data = {
            'status': 'failed',
            'predicted_class': 'Modified',
            'confidence_score': 0.5,
            'patient_age': 75
        }
        
        serializer = DetectionResultSerializer(self.detection, data=data, partial=True)
        self.assertTrue(serializer.is_valid())
        
        updated = serializer.save()
        
        # Read-only fields should not change
        self.assertEqual(updated.status, 'completed')  # Not 'failed'
        self.assertEqual(updated.predicted_class, 'Alzheimer\'s Disease (AD)')  # Not 'Modified'
        
        # Writable fields should change
        self.assertEqual(updated.patient_age, 75)
    
    def test_serializer_json_fields(self):
        """Test JSON fields are serialized correctly"""
        serializer = DetectionResultSerializer(self.detection)
        data = serializer.data
        
        self.assertIsInstance(data['prediction_probability'], dict)
        self.assertIn('AD', data['prediction_probability'])
        self.assertEqual(data['prediction_probability']['AD'], 0.89)
        
        self.assertIsInstance(data['analysis_details'], dict)
        self.assertEqual(data['analysis_details']['model'], 'ResNet-34')
    
    def test_serializer_with_multiple_detections(self):
        """Test serializer with queryset of multiple detections"""
        detection2 = DetectionResult.objects.create(
            user=self.user,
            uploaded_file=SimpleUploadedFile("test2.jpg", b"content", "image/jpeg"),
            file_size=2048,
            status='pending'
        )
        
        detections = DetectionResult.objects.all()
        serializer = DetectionResultSerializer(detections, many=True)
        
        self.assertEqual(len(serializer.data), 2)
        self.assertTrue(all('id' in item for item in serializer.data))


class DetectionUploadSerializerTests(TestCase):
    """Unit tests for DetectionUploadSerializer"""
    
    def setUp(self):
        """Set up test data"""
        self.factory = APIRequestFactory()
    
    def create_test_image(self, filename='test.jpg', size=1024):
        """Helper to create test image file"""
        return SimpleUploadedFile(
            filename,
            b"x" * size,
            content_type="image/jpeg"
        )
    
    def test_serializer_valid_jpg_upload(self):
        """Test serializer validates JPG file correctly"""
        file = self.create_test_image('scan.jpg')
        data = {
            'uploaded_file': file,
            'patient_age': 65,
            'patient_gender': 'Male',
            'notes': 'Routine scan'
        }
        
        serializer = DetectionUploadSerializer(data=data)
        self.assertTrue(serializer.is_valid())
        self.assertEqual(serializer.validated_data['patient_age'], 65)
    
    def test_serializer_valid_png_upload(self):
        """Test serializer validates PNG file correctly"""
        file = SimpleUploadedFile('scan.png', b"x" * 1024, content_type="image/png")
        data = {'uploaded_file': file}
        
        serializer = DetectionUploadSerializer(data=data)
        self.assertTrue(serializer.is_valid())
    
    def test_serializer_valid_nifti_upload(self):
        """Test serializer validates NIfTI file correctly"""
        file = SimpleUploadedFile('brain.nii', b"x" * 2048, content_type="application/octet-stream")
        data = {'uploaded_file': file}
        
        serializer = DetectionUploadSerializer(data=data)
        self.assertTrue(serializer.is_valid())
    
    def test_serializer_valid_nifti_gz_upload(self):
        """Test serializer validates compressed NIfTI file correctly"""
        file = SimpleUploadedFile('brain.nii.gz', b"x" * 2048, content_type="application/gzip")
        data = {'uploaded_file': file}
        
        serializer = DetectionUploadSerializer(data=data)
        self.assertTrue(serializer.is_valid())
    
    def test_serializer_rejects_invalid_file_type(self):
        """Test serializer rejects unsupported file types"""
        file = SimpleUploadedFile('document.pdf', b"x" * 1024, content_type="application/pdf")
        data = {'uploaded_file': file}
        
        serializer = DetectionUploadSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('uploaded_file', serializer.errors)
    
    def test_serializer_rejects_oversized_image(self):
        """Test serializer rejects image files larger than 10MB"""
        # 11MB file
        file = self.create_test_image('large.jpg', size=11 * 1024 * 1024)
        data = {'uploaded_file': file}
        
        serializer = DetectionUploadSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('uploaded_file', serializer.errors)
        self.assertIn('too large', str(serializer.errors['uploaded_file'][0]).lower())
    
    def test_serializer_rejects_oversized_nifti(self):
        """Test serializer rejects NIfTI files larger than 50MB"""
        # 51MB NIfTI file
        file = SimpleUploadedFile(
            'large.nii.gz',
            b"x" * (51 * 1024 * 1024),
            content_type="application/gzip"
        )
        data = {'uploaded_file': file}
        
        serializer = DetectionUploadSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('uploaded_file', serializer.errors)
    
    def test_serializer_accepts_nifti_under_limit(self):
        """Test serializer accepts NIfTI files under 50MB"""
        # 30MB NIfTI file
        file = SimpleUploadedFile(
            'normal.nii.gz',
            b"x" * (30 * 1024 * 1024),
            content_type="application/gzip"
        )
        data = {'uploaded_file': file}
        
        serializer = DetectionUploadSerializer(data=data)
        self.assertTrue(serializer.is_valid())
    
    def test_serializer_optional_fields(self):
        """Test that patient info fields are optional"""
        file = self.create_test_image()
        data = {'uploaded_file': file}
        
        serializer = DetectionUploadSerializer(data=data)
        self.assertTrue(serializer.is_valid())
        
        # All optional fields should be None
        self.assertIsNone(serializer.validated_data.get('patient_age'))
        self.assertIsNone(serializer.validated_data.get('patient_gender'))
        self.assertIsNone(serializer.validated_data.get('notes'))
    
    def test_serializer_with_all_fields(self):
        """Test serializer with all optional fields provided"""
        file = self.create_test_image()
        data = {
            'uploaded_file': file,
            'patient_age': 72,
            'patient_gender': 'Female',
            'notes': 'Patient reports memory issues'
        }
        
        serializer = DetectionUploadSerializer(data=data)
        self.assertTrue(serializer.is_valid())
        self.assertEqual(serializer.validated_data['patient_age'], 72)
        self.assertEqual(serializer.validated_data['patient_gender'], 'Female')
        self.assertEqual(serializer.validated_data['notes'], 'Patient reports memory issues')
    
    def test_serializer_missing_file(self):
        """Test serializer rejects request without uploaded_file"""
        data = {
            'patient_age': 65,
            'notes': 'No file'
        }
        
        serializer = DetectionUploadSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('uploaded_file', serializer.errors)
    
    def test_serializer_case_insensitive_extension(self):
        """Test that file extension check is case insensitive"""
        file = SimpleUploadedFile('SCAN.JPG', b"x" * 1024, content_type="image/jpeg")
        data = {'uploaded_file': file}
        
        serializer = DetectionUploadSerializer(data=data)
        self.assertTrue(serializer.is_valid())


class ModelMetadataSerializerTests(TestCase):
    """Unit tests for ModelMetadataSerializer"""
    
    def setUp(self):
        """Set up test model metadata"""
        self.metadata = ModelMetadata.objects.create(
            name='Alzheimer Detector',
            version='1.0.0',
            architecture='ResNet-34',
            accuracy=0.92,
            auc_score=0.95,
            sensitivity=0.89,
            specificity=0.93,
            trained_on=datetime(2024, 1, 15).date(),
            is_active=True,
            description='Binary classifier for AD detection'
        )
    
    def test_serializer_contains_expected_fields(self):
        """Test serializer returns all expected fields"""
        serializer = ModelMetadataSerializer(self.metadata)
        data = serializer.data
        
        expected_fields = {
            'id', 'name', 'version', 'architecture', 'accuracy',
            'auc_score', 'sensitivity', 'specificity', 'trained_on',
            'is_active', 'description'
        }
        
        self.assertEqual(set(data.keys()), expected_fields)
    
    def test_serializer_field_values(self):
        """Test serializer returns correct field values"""
        serializer = ModelMetadataSerializer(self.metadata)
        data = serializer.data
        
        self.assertEqual(data['name'], 'Alzheimer Detector')
        self.assertEqual(data['version'], '1.0.0')
        self.assertEqual(data['architecture'], 'ResNet-34')
        self.assertEqual(data['accuracy'], 0.92)
        self.assertEqual(data['auc_score'], 0.95)
        self.assertEqual(data['sensitivity'], 0.89)
        self.assertEqual(data['specificity'], 0.93)
        self.assertTrue(data['is_active'])
    
    def test_serializer_with_multiple_models(self):
        """Test serializer with multiple model metadata entries"""
        metadata2 = ModelMetadata.objects.create(
            name='AD Detector V2',
            version='2.0.0',
            architecture='ResNet-50',
            accuracy=0.94,
            auc_score=0.96,
            sensitivity=0.91,
            specificity=0.95,
            trained_on=datetime(2024, 6, 1).date(),
            is_active=True,
            description='Improved model'
        )
        
        models = ModelMetadata.objects.all()
        serializer = ModelMetadataSerializer(models, many=True)
        
        self.assertEqual(len(serializer.data), 2)
        names = [item['name'] for item in serializer.data]
        self.assertIn('Alzheimer Detector', names)
        self.assertIn('AD Detector V2', names)
    
    def test_serializer_read_only_id_field(self):
        """Test that id field is read-only"""
        data = {
            'id': 9999,
            'name': 'Test Model',
            'version': '1.0',
            'architecture': 'ResNet-34',
            'accuracy': 0.90,
            'auc_score': 0.92,
            'sensitivity': 0.88,
            'specificity': 0.90,
            'trained_on': datetime.now().date(),
            'is_active': True
        }
        
        serializer = ModelMetadataSerializer(data=data)
        self.assertTrue(serializer.is_valid())
        
        # ID should not be in validated data
        self.assertNotIn('id', serializer.validated_data)
    
    def test_serializer_optional_description(self):
        """Test that description field is optional"""
        metadata = ModelMetadata.objects.create(
            name='Model Without Desc',
            version='1.0',
            architecture='ResNet-18',
            accuracy=0.88,
            auc_score=0.90,
            sensitivity=0.85,
            specificity=0.88,
            trained_on=datetime.now().date(),
            is_active=True
            # No description
        )
        
        serializer = ModelMetadataSerializer(metadata)
        self.assertIn('description', serializer.data)
        self.assertEqual(serializer.data['description'], '')
    
    def test_serializer_metric_precision(self):
        """Test that metric fields maintain decimal precision"""
        metadata = ModelMetadata.objects.create(
            name='Precise Model',
            version='1.0',
            architecture='ResNet-34',
            accuracy=0.923456,
            auc_score=0.956789,
            sensitivity=0.891234,
            specificity=0.934567,
            trained_on=datetime.now().date()
        )
        
        serializer = ModelMetadataSerializer(metadata)
        data = serializer.data
        
        # Check precision is maintained
        self.assertAlmostEqual(data['accuracy'], 0.923456, places=5)
        self.assertAlmostEqual(data['auc_score'], 0.956789, places=5)
        self.assertAlmostEqual(data['sensitivity'], 0.891234, places=5)
        self.assertAlmostEqual(data['specificity'], 0.934567, places=5)
