"""
Unit tests for detection models
Tests DetectionResult and ModelMetadata models
"""
import os
from datetime import datetime, timedelta
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db.utils import IntegrityError
from django.utils import timezone
from detection.models import DetectionResult, ModelMetadata

User = get_user_model()


class DetectionResultModelTests(TestCase):
    """Unit tests for DetectionResult model"""
    
    def setUp(self):
        """Set up test users and sample data"""
        self.user1 = User.objects.create_user(
            username='testpatient1',
            email='patient1@test.com',
            password='testpass123',
            first_name='Test Patient'
        )
        self.user2 = User.objects.create_user(
            username='testdoctor1',
            email='doctor1@test.com',
            password='testpass123',
            first_name='Dr. Test'
        )
        
        # Create a simple test file
        self.test_file = SimpleUploadedFile(
            "test_mri.jpg",
            b"fake image content",
            content_type="image/jpeg"
        )
    
    def test_create_detection_result_minimal(self):
        """Test creating DetectionResult with minimal required fields"""
        detection = DetectionResult.objects.create(
            user=self.user1,
            uploaded_file=self.test_file,
            file_size=1024
        )
        
        self.assertIsNotNone(detection.id)
        self.assertEqual(detection.user, self.user1)
        self.assertEqual(detection.status, 'pending')
        self.assertEqual(detection.file_size, 1024)
        self.assertIsNotNone(detection.upload_date)
        self.assertIsNone(detection.predicted_class)
        self.assertIsNone(detection.confidence_score)
    
    def test_create_detection_result_complete(self):
        """Test creating DetectionResult with all fields"""
        detection = DetectionResult.objects.create(
            user=self.user1,
            uploaded_file=self.test_file,
            file_size=2048,
            status='completed',
            predicted_class='Alzheimer\'s Disease (AD)',
            confidence_score=0.92,
            prediction_probability={'AD': 0.92, 'CN': 0.08},
            model_version='v2.0',
            processing_time=1.5,
            analysis_details={'threshold': 0.5, 'model': 'ResNet-34'},
            patient_age=72,
            patient_gender='Male',
            notes='Patient shows symptoms',
            clinician_notes='Requires further investigation',
            reviewed_by=self.user2
        )
        
        self.assertEqual(detection.predicted_class, 'Alzheimer\'s Disease (AD)')
        self.assertEqual(detection.confidence_score, 0.92)
        self.assertEqual(detection.patient_age, 72)
        self.assertEqual(detection.patient_gender, 'Male')
        self.assertEqual(detection.reviewed_by, self.user2)
        self.assertEqual(detection.model_version, 'v2.0')
        self.assertIn('threshold', detection.analysis_details)
    
    def test_detection_result_status_choices(self):
        """Test all status choices are valid"""
        statuses = ['pending', 'processing', 'completed', 'failed']
        
        for status_choice in statuses:
            detection = DetectionResult.objects.create(
                user=self.user1,
                uploaded_file=SimpleUploadedFile(f"test_{status_choice}.jpg", b"content", "image/jpeg"),
                file_size=1024,
                status=status_choice
            )
            self.assertEqual(detection.status, status_choice)
    
    def test_detection_result_user_relationship(self):
        """Test user foreign key relationship"""
        detection1 = DetectionResult.objects.create(
            user=self.user1,
            uploaded_file=SimpleUploadedFile("test1.jpg", b"content1", "image/jpeg"),
            file_size=1024
        )
        detection2 = DetectionResult.objects.create(
            user=self.user1,
            uploaded_file=SimpleUploadedFile("test2.jpg", b"content2", "image/jpeg"),
            file_size=2048
        )
        
        # Test reverse relationship
        user_detections = self.user1.detection_results.all()
        self.assertEqual(user_detections.count(), 2)
        self.assertIn(detection1, user_detections)
        self.assertIn(detection2, user_detections)
    
    def test_detection_result_ordering(self):
        """Test that results are ordered by created_at descending"""
        # Create detections at different times
        detection1 = DetectionResult.objects.create(
            user=self.user1,
            uploaded_file=SimpleUploadedFile("test1.jpg", b"content1", "image/jpeg"),
            file_size=1024
        )
        
        detection2 = DetectionResult.objects.create(
            user=self.user1,
            uploaded_file=SimpleUploadedFile("test2.jpg", b"content2", "image/jpeg"),
            file_size=2048
        )
        
        results = DetectionResult.objects.all()
        # Most recent should be first
        self.assertEqual(results[0], detection2)
        self.assertEqual(results[1], detection1)
    
    def test_detection_result_str_representation(self):
        """Test string representation of DetectionResult"""
        detection = DetectionResult.objects.create(
            user=self.user1,
            uploaded_file=self.test_file,
            file_size=1024,
            predicted_class='Control (CN)',
            confidence_score=0.85,
            status='completed'
        )
        
        str_repr = str(detection)
        self.assertIn(self.user1.username, str_repr)
        self.assertIn('Control (CN)', str_repr)
    
    def test_detection_result_cascade_delete_user(self):
        """Test that detection results are deleted when user is deleted"""
        detection = DetectionResult.objects.create(
            user=self.user1,
            uploaded_file=self.test_file,
            file_size=1024
        )
        detection_id = detection.id
        
        self.user1.delete()
        
        # Detection should be deleted
        self.assertFalse(DetectionResult.objects.filter(id=detection_id).exists())
    
    def test_detection_result_set_null_reviewed_by(self):
        """Test that reviewed_by is set to NULL when reviewer is deleted"""
        detection = DetectionResult.objects.create(
            user=self.user1,
            uploaded_file=self.test_file,
            file_size=1024,
            reviewed_by=self.user2
        )
        
        self.user2.delete()
        detection.refresh_from_db()
        
        # Detection should still exist but reviewed_by should be None
        self.assertIsNone(detection.reviewed_by)
    
    def test_detection_result_json_fields(self):
        """Test JSON fields store and retrieve data correctly"""
        prediction_prob = {
            'Alzheimer\'s Disease (AD)': 0.65,
            'Control (CN)': 0.35
        }
        analysis = {
            'raw_output': 0.32,
            'sigmoid_probability': 0.65,
            'threshold_used': 0.5,
            'model_version': 'ResNet-34-v1.0'
        }
        
        detection = DetectionResult.objects.create(
            user=self.user1,
            uploaded_file=self.test_file,
            file_size=1024,
            prediction_probability=prediction_prob,
            analysis_details=analysis
        )
        
        detection.refresh_from_db()
        
        self.assertEqual(detection.prediction_probability, prediction_prob)
        self.assertEqual(detection.analysis_details, analysis)
        self.assertEqual(detection.analysis_details['model_version'], 'ResNet-34-v1.0')
    
    def test_detection_result_timestamps(self):
        """Test that created_at and updated_at timestamps work correctly"""
        detection = DetectionResult.objects.create(
            user=self.user1,
            uploaded_file=self.test_file,
            file_size=1024
        )
        
        created_time = detection.created_at
        self.assertIsNotNone(created_time)
        
        # Update the detection
        detection.status = 'completed'
        detection.save()
        
        self.assertGreaterEqual(detection.updated_at, created_time)
    
    def test_detection_result_default_values(self):
        """Test model default values"""
        detection = DetectionResult.objects.create(
            user=self.user1,
            uploaded_file=self.test_file,
            file_size=1024
        )
        
        self.assertEqual(detection.status, 'pending')
        self.assertEqual(detection.model_version, 'v1.0')


class ModelMetadataModelTests(TestCase):
    """Unit tests for ModelMetadata model"""
    
    def test_create_model_metadata_complete(self):
        """Test creating ModelMetadata with all fields"""
        metadata = ModelMetadata.objects.create(
            name='Alzheimer Detector',
            version='1.0.0',
            architecture='ResNet-34',
            accuracy=0.92,
            auc_score=0.95,
            sensitivity=0.89,
            specificity=0.93,
            trained_on=datetime.now().date(),
            is_active=True,
            model_path='models/alzheimers_detector.pth',
            description='Binary classifier for AD detection'
        )
        
        self.assertEqual(metadata.name, 'Alzheimer Detector')
        self.assertEqual(metadata.version, '1.0.0')
        self.assertEqual(metadata.architecture, 'ResNet-34')
        self.assertEqual(metadata.accuracy, 0.92)
        self.assertEqual(metadata.auc_score, 0.95)
        self.assertTrue(metadata.is_active)
    
    def test_model_metadata_str_representation(self):
        """Test string representation of ModelMetadata"""
        metadata = ModelMetadata.objects.create(
            name='AD Detector',
            version='2.1.0',
            architecture='ResNet-50',
            accuracy=0.94,
            auc_score=0.96,
            sensitivity=0.91,
            specificity=0.95,
            trained_on=datetime.now().date(),
            model_path='models/v2.pth'
        )
        
        str_repr = str(metadata)
        self.assertIn('AD Detector', str_repr)
        self.assertIn('2.1.0', str_repr)
    
    def test_model_metadata_ordering(self):
        """Test that metadata is ordered by created_at descending"""
        metadata1 = ModelMetadata.objects.create(
            name='Model V1',
            version='1.0',
            architecture='ResNet-34',
            accuracy=0.90,
            auc_score=0.92,
            sensitivity=0.88,
            specificity=0.90,
            trained_on=datetime.now().date(),
            model_path='models/v1.pth'
        )
        
        metadata2 = ModelMetadata.objects.create(
            name='Model V2',
            version='2.0',
            architecture='ResNet-50',
            accuracy=0.94,
            auc_score=0.96,
            sensitivity=0.92,
            specificity=0.94,
            trained_on=datetime.now().date(),
            model_path='models/v2.pth'
        )
        
        results = ModelMetadata.objects.all()
        self.assertEqual(results[0], metadata2)
        self.assertEqual(results[1], metadata1)
    
    def test_model_metadata_active_filter(self):
        """Test filtering for active models"""
        active_model = ModelMetadata.objects.create(
            name='Active Model',
            version='1.0',
            architecture='ResNet-34',
            accuracy=0.92,
            auc_score=0.94,
            sensitivity=0.90,
            specificity=0.92,
            trained_on=datetime.now().date(),
            is_active=True,
            model_path='models/active.pth'
        )
        
        inactive_model = ModelMetadata.objects.create(
            name='Inactive Model',
            version='0.9',
            architecture='ResNet-18',
            accuracy=0.85,
            auc_score=0.87,
            sensitivity=0.83,
            specificity=0.86,
            trained_on=datetime.now().date() - timedelta(days=30),
            is_active=False,
            model_path='models/inactive.pth'
        )
        
        active_models = ModelMetadata.objects.filter(is_active=True)
        self.assertEqual(active_models.count(), 1)
        self.assertEqual(active_models.first(), active_model)
    
    def test_model_metadata_metrics_validation(self):
        """Test that model metrics are stored correctly as floats"""
        metadata = ModelMetadata.objects.create(
            name='Test Model',
            version='1.0',
            architecture='ResNet-34',
            accuracy=0.923456,
            auc_score=0.956789,
            sensitivity=0.891234,
            specificity=0.934567,
            trained_on=datetime.now().date(),
            model_path='models/test.pth'
        )
        
        self.assertIsInstance(metadata.accuracy, float)
        self.assertIsInstance(metadata.auc_score, float)
        self.assertIsInstance(metadata.sensitivity, float)
        self.assertIsInstance(metadata.specificity, float)
        
        # Check precision is maintained
        self.assertAlmostEqual(metadata.accuracy, 0.923456, places=6)
    
    def test_model_metadata_timestamps(self):
        """Test that timestamps are automatically set"""
        metadata = ModelMetadata.objects.create(
            name='Test Model',
            version='1.0',
            architecture='ResNet-34',
            accuracy=0.92,
            auc_score=0.94,
            sensitivity=0.90,
            specificity=0.92,
            trained_on=datetime.now().date(),
            model_path='models/test.pth'
        )
        
        self.assertIsNotNone(metadata.created_at)
        self.assertIsNotNone(metadata.updated_at)
        
        # Update and check updated_at changes
        created = metadata.created_at
        metadata.description = 'Updated description'
        metadata.save()
        
        self.assertGreaterEqual(metadata.updated_at, created)
    
    def test_model_metadata_default_is_active(self):
        """Test that is_active defaults to True"""
        metadata = ModelMetadata.objects.create(
            name='Test Model',
            version='1.0',
            architecture='ResNet-34',
            accuracy=0.92,
            auc_score=0.94,
            sensitivity=0.90,
            specificity=0.92,
            trained_on=datetime.now().date(),
            model_path='models/test.pth'
        )
        
        self.assertTrue(metadata.is_active)
