"""
API Integration tests for detection endpoints
Tests DetectionViewSet API endpoints with authentication
"""
import io
import json
from datetime import datetime
from unittest.mock import patch, MagicMock
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient, APITestCase
from rest_framework_simplejwt.tokens import AccessToken
from PIL import Image
from detection.models import DetectionResult, ModelMetadata

User = get_user_model()


class DetectionAPITests(APITestCase):
    """Integration tests for Detection API endpoints"""
    
    def setUp(self):
        """Set up test users and authentication"""
        self.client = APIClient()
        
        # Create test users
        self.user1 = User.objects.create_user(
            username='patient1',
            email='patient1@test.com',
            password='testpass123',
            first_name='Patient One'
        )
        
        self.user2 = User.objects.create_user(
            username='patient2',
            email='patient2@test.com',
            password='testpass123',
            first_name='Patient Two'
        )
        
        # Create JWT tokens for authentication
        self.token1 = str(AccessToken.for_user(self.user1))
        self.token2 = str(AccessToken.for_user(self.user2))
        
        # Create some test detections
        self.detection1 = DetectionResult.objects.create(
            user=self.user1,
            uploaded_file=SimpleUploadedFile('test1.jpg', b'content1', 'image/jpeg'),
            file_size=1024,
            status='completed',
            predicted_class='Alzheimer\'s Disease (AD)',
            confidence_score=0.88
        )
        
        self.detection2 = DetectionResult.objects.create(
            user=self.user1,
            uploaded_file=SimpleUploadedFile('test2.jpg', b'content2', 'image/jpeg'),
            file_size=2048,
            status='pending'
        )
        
        self.detection_user2 = DetectionResult.objects.create(
            user=self.user2,
            uploaded_file=SimpleUploadedFile('test3.jpg', b'content3', 'image/jpeg'),
            file_size=1536,
            status='completed',
            predicted_class='Control (CN)',
            confidence_score=0.92
        )
    
    def create_test_image(self):
        """Helper to create a test image file"""
        img = Image.new('RGB', (224, 224), color='gray')
        buf = io.BytesIO()
        img.save(buf, format='JPEG')
        buf.seek(0)
        return SimpleUploadedFile('test_scan.jpg', buf.read(), content_type='image/jpeg')
    
    def test_list_detections_authenticated(self):
        """Test listing detections for authenticated user"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token1}')
        url = reverse('detection-list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)  # Only user1's detections
        
        # Check data contains expected fields
        self.assertIn('id', response.data[0])
        self.assertIn('status', response.data[0])
        self.assertIn('predicted_class', response.data[0])
    
    def test_list_detections_unauthenticated(self):
        """Test listing detections without authentication fails"""
        url = reverse('detection-list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_list_detections_isolation(self):
        """Test users can only see their own detections"""
        # User 1 should see 2 detections
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token1}')
        url = reverse('detection-list')
        response = self.client.get(url)
        self.assertEqual(len(response.data), 2)
        
        # User 2 should see 1 detection
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token2}')
        response = self.client.get(url)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['user_username'], 'patient2')
    
    def test_retrieve_detection_detail(self):
        """Test retrieving a specific detection"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token1}')
        url = reverse('detection-detail', args=[self.detection1.id])
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['id'], self.detection1.id)
        self.assertEqual(response.data['status'], 'completed')
        self.assertEqual(response.data['confidence_score'], 0.88)
    
    def test_retrieve_detection_unauthorized_user(self):
        """Test user cannot access another user's detection"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token2}')
        url = reverse('detection-detail', args=[self.detection1.id])
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
    
    @patch('detection.views.ModelLoader')
    def test_upload_and_detect_success(self, mock_loader):
        """Test successful file upload and detection"""
        # Mock the model prediction
        mock_instance = MagicMock()
        mock_instance.model = MagicMock()
        mock_instance.device = 'cpu'
        mock_loader.return_value = mock_instance
        
        # Mock torch operations
        with patch('detection.views.torch') as mock_torch:
            mock_output = MagicMock()
            mock_output.item.return_value = 0.3
            mock_instance.model.return_value = mock_output
            
            mock_sigmoid = MagicMock()
            mock_sigmoid.item.return_value = 0.85
            mock_torch.sigmoid.return_value = mock_sigmoid
            mock_torch.no_grad.return_value.__enter__ = MagicMock()
            mock_torch.no_grad.return_value.__exit__ = MagicMock()
            
            self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token1}')
            url = reverse('detection-upload-and-detect')
            
            data = {
                'uploaded_file': self.create_test_image(),
                'patient_age': 70,
                'patient_gender': 'Male',
                'notes': 'Routine screening'
            }
            
            response = self.client.post(url, data, format='multipart')
            
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)
            self.assertIn('id', response.data)
            self.assertIn('predicted_class', response.data)
            self.assertIn('confidence_score', response.data)
            self.assertEqual(response.data['patient_age'], 70)
    
    def test_upload_and_detect_missing_file(self):
        """Test upload without file fails"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token1}')
        url = reverse('detection-upload-and-detect')
        
        data = {
            'patient_age': 65,
            'notes': 'No file'
        }
        
        response = self.client.post(url, data, format='multipart')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('uploaded_file', response.data)
    
    def test_upload_and_detect_invalid_file_type(self):
        """Test upload with invalid file type fails"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token1}')
        url = reverse('detection-upload-and-detect')
        
        invalid_file = SimpleUploadedFile('document.txt', b'text content', content_type='text/plain')
        data = {'uploaded_file': invalid_file}
        
        response = self.client.post(url, data, format='multipart')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_upload_and_detect_unauthenticated(self):
        """Test upload without authentication fails"""
        url = reverse('detection-upload-and-detect')
        data = {'uploaded_file': self.create_test_image()}
        
        response = self.client.post(url, data, format='multipart')
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_detection_history_endpoint(self):
        """Test detection history endpoint"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token1}')
        url = reverse('detection-history')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)
    
    def test_detection_stats_endpoint(self):
        """Test detection statistics endpoint"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token1}')
        url = reverse('detection-stats')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('total_detections', response.data)
        self.assertIn('completed', response.data)
        self.assertIn('alzheimers_cases', response.data)
        self.assertIn('control_cases', response.data)
        self.assertIn('ad_percentage', response.data)
        
        # Verify stats
        self.assertEqual(response.data['total_detections'], 2)
        self.assertEqual(response.data['completed'], 1)
        self.assertEqual(response.data['alzheimers_cases'], 1)
        self.assertEqual(response.data['control_cases'], 0)
    
    def test_detection_stats_multiple_completed(self):
        """Test stats with multiple completed detections"""
        # Add more completed detections
        DetectionResult.objects.create(
            user=self.user1,
            uploaded_file=SimpleUploadedFile('test4.jpg', b'content4', 'image/jpeg'),
            file_size=1024,
            status='completed',
            predicted_class='Control (CN)',
            confidence_score=0.91
        )
        
        DetectionResult.objects.create(
            user=self.user1,
            uploaded_file=SimpleUploadedFile('test5.jpg', b'content5', 'image/jpeg'),
            file_size=1024,
            status='completed',
            predicted_class='Control (CN)',
            confidence_score=0.87
        )
        
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token1}')
        url = reverse('detection-stats')
        response = self.client.get(url)
        
        self.assertEqual(response.data['completed'], 3)
        self.assertEqual(response.data['alzheimers_cases'], 1)
        self.assertEqual(response.data['control_cases'], 2)
        self.assertAlmostEqual(response.data['ad_percentage'], 33.33, places=1)
    
    def test_update_detection_notes(self):
        """Test updating detection notes and patient info"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token1}')
        url = reverse('detection-detail', args=[self.detection1.id])
        
        data = {
            'notes': 'Updated notes',
            'patient_age': 69,
            'clinician_notes': 'Review recommended'
        }
        
        response = self.client.patch(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['notes'], 'Updated notes')
        self.assertEqual(response.data['patient_age'], 69)
        self.assertEqual(response.data['clinician_notes'], 'Review recommended')
    
    def test_delete_detection(self):
        """Test deleting a detection"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token1}')
        url = reverse('detection-detail', args=[self.detection2.id])
        
        response = self.client.delete(url)
        
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        
        # Verify deletion
        self.assertFalse(DetectionResult.objects.filter(id=self.detection2.id).exists())
    
    def test_delete_detection_unauthorized(self):
        """Test user cannot delete another user's detection"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token2}')
        url = reverse('detection-detail', args=[self.detection1.id])
        
        response = self.client.delete(url)
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        
        # Verify detection still exists
        self.assertTrue(DetectionResult.objects.filter(id=self.detection1.id).exists())


class ModelMetadataAPITests(APITestCase):
    """Integration tests for ModelMetadata API endpoints"""
    
    def setUp(self):
        """Set up test data"""
        self.client = APIClient()
        
        self.user = User.objects.create_user(
            username='testuser',
            email='test@test.com',
            password='testpass123'
        )
        
        self.token = str(AccessToken.for_user(self.user))
        
        # Create active and inactive models
        self.active_model = ModelMetadata.objects.create(
            name='Active Model',
            version='1.0',
            architecture='ResNet-34',
            accuracy=0.92,
            auc_score=0.94,
            sensitivity=0.90,
            specificity=0.92,
            trained_on=datetime(2024, 1, 1).date(),
            is_active=True,
            model_path='models/active.pth'
        )
        
        self.inactive_model = ModelMetadata.objects.create(
            name='Inactive Model',
            version='0.9',
            architecture='ResNet-18',
            accuracy=0.85,
            auc_score=0.87,
            sensitivity=0.83,
            specificity=0.86,
            trained_on=datetime(2023, 6, 1).date(),
            is_active=False,
            model_path='models/inactive.pth'
        )
    
    def test_list_model_metadata_authenticated(self):
        """Test listing model metadata (active only)"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token}')
        url = reverse('model-metadata-list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)  # Only active models
        self.assertEqual(response.data[0]['name'], 'Active Model')
    
    def test_list_model_metadata_unauthenticated(self):
        """Test listing model metadata without authentication fails"""
        url = reverse('model-metadata-list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_retrieve_model_metadata_detail(self):
        """Test retrieving specific model metadata"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token}')
        url = reverse('model-metadata-detail', args=[self.active_model.id])
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], 'Active Model')
        self.assertEqual(response.data['version'], '1.0')
        self.assertEqual(response.data['architecture'], 'ResNet-34')
        self.assertEqual(response.data['accuracy'], 0.92)
    
    def test_model_metadata_is_read_only(self):
        """Test that model metadata endpoints are read-only"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token}')
        
        # Try to create
        create_url = reverse('model-metadata-list')
        data = {
            'name': 'New Model',
            'version': '2.0',
            'architecture': 'ResNet-50',
            'accuracy': 0.95,
            'auc_score': 0.96,
            'sensitivity': 0.93,
            'specificity': 0.94,
            'trained_on': datetime.now().date()
        }
        response = self.client.post(create_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
        
        # Try to update
        update_url = reverse('model-metadata-detail', args=[self.active_model.id])
        response = self.client.put(update_url, {'name': 'Modified'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
        
        # Try to delete
        response = self.client.delete(update_url)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
