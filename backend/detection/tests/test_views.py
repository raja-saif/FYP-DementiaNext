"""
Unit tests for detection views
Tests ModelLoader and image processing logic
"""
import os
import io
import tempfile
from unittest.mock import patch, MagicMock, Mock
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image
import numpy as np
from detection.views import ModelLoader, DetectionViewSet
from detection.models import DetectionResult

User = get_user_model()


class ModelLoaderTests(TestCase):
    """Unit tests for ModelLoader class"""
    
    def setUp(self):
        """Reset ModelLoader singleton for each test"""
        ModelLoader._instance = None
        ModelLoader._model = None
        ModelLoader._device = None
    
    def test_model_loader_is_singleton(self):
        """Test ModelLoader implements singleton pattern"""
        loader1 = ModelLoader()
        loader2 = ModelLoader()
        
        self.assertIs(loader1, loader2)
    
    @patch('detection.views.torch')
    def test_model_loader_device_cpu(self, mock_torch):
        """Test device selection defaults to CPU when CUDA unavailable"""
        mock_torch.cuda.is_available.return_value = False
        mock_torch.device.return_value = 'cpu'
        
        loader = ModelLoader()
        device = loader.device
        
        mock_torch.device.assert_called_with('cpu')
    
    @patch('detection.views.torch')
    def test_model_loader_device_cuda(self, mock_torch):
        """Test device selection uses CUDA when available"""
        mock_torch.cuda.is_available.return_value = True
        mock_torch.device.return_value = 'cuda'
        
        loader = ModelLoader()
        device = loader.device
        
        mock_torch.device.assert_called_with('cuda')
    
    @patch('detection.views.os.path.exists')
    @patch('detection.views.torch')
    @patch('detection.views.resnet34')
    @patch('detection.views.settings')
    def test_load_model_file_exists(self, mock_settings, mock_resnet34, mock_torch, mock_exists):
        """Test model loading when model file exists"""
        mock_settings.BASE_DIR = '/fake/path'
        mock_exists.return_value = True
        
        # Mock model components
        mock_backbone = MagicMock()
        mock_backbone.fc = MagicMock()
        mock_backbone.fc.in_features = 512
        mock_resnet34.return_value = mock_backbone
        
        mock_checkpoint = {'model_state_dict': {}}
        mock_torch.load.return_value = mock_checkpoint
        mock_torch.device.return_value = 'cpu'
        mock_torch.cuda.is_available.return_value = False
        mock_torch.nn.Sequential = MagicMock()
        mock_torch.nn.Dropout = MagicMock()
        mock_torch.nn.Linear = MagicMock()
        
        loader = ModelLoader()
        model = loader.model
        
        self.assertIsNotNone(model)
        mock_torch.load.assert_called_once()
    
    @patch('detection.views.os.path.exists')
    @patch('detection.views.torch')
    @patch('detection.views.resnet34')
    @patch('detection.views.settings')
    def test_load_model_file_not_exists(self, mock_settings, mock_resnet34, mock_torch, mock_exists):
        """Test model loading when model file doesn't exist"""
        mock_settings.BASE_DIR = '/fake/path'
        mock_exists.return_value = False
        
        mock_backbone = MagicMock()
        mock_backbone.fc = MagicMock()
        mock_backbone.fc.in_features = 512
        mock_resnet34.return_value = mock_backbone
        
        mock_torch.device.return_value = 'cpu'
        mock_torch.cuda.is_available.return_value = False
        mock_torch.nn.Sequential = MagicMock()
        mock_torch.nn.Dropout = MagicMock()
        mock_torch.nn.Linear = MagicMock()
        
        loader = ModelLoader()
        model = loader.model
        
        # Should still create model, just not load weights
        self.assertIsNotNone(model)
        mock_torch.load.assert_not_called()


class ImageProcessingTests(TestCase):
    """Unit tests for image processing logic in DetectionViewSet"""
    
    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@test.com',
            password='testpass123'
        )
        
        self.viewset = DetectionViewSet()
        self.viewset.request = MagicMock()
        self.viewset.request.user = self.user
    
    def create_test_image(self, size=(224, 224), color='gray'):
        """Helper to create test image"""
        img = Image.new('RGB', size, color=color)
        buf = io.BytesIO()
        img.save(buf, format='JPEG')
        buf.seek(0)
        return buf.getvalue()
    
    def test_process_image_jpg_format(self):
        """Test processing regular JPEG image"""
        # Create a test detection result
        image_bytes = self.create_test_image()
        
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp_file:
            tmp_file.write(image_bytes)
            tmp_file_path = tmp_file.name
        
        try:
            detection = DetectionResult.objects.create(
                user=self.user,
                uploaded_file=SimpleUploadedFile('test.jpg', image_bytes, 'image/jpeg'),
                file_size=len(image_bytes)
            )
            
            # Mock the file path
            # Mock the uploaded_file.path using property mock
            with patch('django.core.files.storage.FileSystemStorage.path', return_value=tmp_file_path):
                # Mock model and torch
                with patch('detection.views.ModelLoader') as mock_loader_class:
                    mock_loader = MagicMock()
                    mock_loader_class.return_value = mock_loader
                    
                    mock_model = MagicMock()
                    mock_loader.model = mock_model
                    mock_loader.device = 'cpu'
                    
                    with patch('detection.views.torch') as mock_torch:
                        mock_output = MagicMock()
                        mock_output.item.return_value = 0.5
                        mock_model.return_value = mock_output
                        
                        mock_sigmoid = MagicMock()
                        mock_sigmoid.item.return_value = 0.85
                        mock_torch.sigmoid.return_value = mock_sigmoid
                        mock_torch.no_grad.return_value.__enter__ = MagicMock()
                        mock_torch.no_grad.return_value.__exit__ = MagicMock()
                        
                        result = self.viewset._process_image(detection)
                        
                        self.assertIn('predicted_class', result)
                        self.assertIn('confidence', result)
                        self.assertIn('probabilities', result)
                        self.assertIn('analysis', result)
        finally:
            # Clean up temp file
            if os.path.exists(tmp_file_path):
                os.remove(tmp_file_path)
    
    def test_process_image_returns_correct_format(self):
        """Test that _process_image returns expected result format"""
        image_bytes = self.create_test_image()
        
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp_file:
            tmp_file.write(image_bytes)
            tmp_file_path = tmp_file.name
        
        try:
            detection = DetectionResult.objects.create(
                user=self.user,
                uploaded_file=SimpleUploadedFile('test.jpg', image_bytes, 'image/jpeg'),
                file_size=len(image_bytes)
            )
            
            with patch('django.core.files.storage.FileSystemStorage.path', return_value=tmp_file_path):
                with patch('detection.views.ModelLoader') as mock_loader_class:
                    mock_loader = MagicMock()
                    mock_loader_class.return_value = mock_loader
                    mock_loader.model = MagicMock()
                    mock_loader.device = 'cpu'
                    
                    with patch('detection.views.torch') as mock_torch:
                        mock_output = MagicMock()
                        mock_output.item.return_value = 0.3
                        mock_loader.model.return_value = mock_output
                        
                        mock_sigmoid = MagicMock()
                        mock_sigmoid.item.return_value = 0.65
                        mock_torch.sigmoid.return_value = mock_sigmoid
                        mock_torch.no_grad.return_value.__enter__ = MagicMock()
                        mock_torch.no_grad.return_value.__exit__ = MagicMock()
                        
                        result = self.viewset._process_image(detection)
                        
                        # Check result structure
                        self.assertIsInstance(result, dict)
                        self.assertIn('predicted_class', result)
                        self.assertIn('confidence', result)
                        self.assertIn('probabilities', result)
                        self.assertIn('analysis', result)
                        
                        # Check probabilities
                        self.assertIsInstance(result['probabilities'], dict)
                        self.assertIn('Alzheimer\'s Disease (AD)', result['probabilities'])
                        self.assertIn('Control (CN)', result['probabilities'])
                        
                        # Check analysis details
                        self.assertIn('raw_output', result['analysis'])
                        self.assertIn('sigmoid_probability', result['analysis'])
                        self.assertIn('threshold_used', result['analysis'])
                        self.assertIn('model_version', result['analysis'])
        finally:
            if os.path.exists(tmp_file_path):
                os.remove(tmp_file_path)
    
    @patch('detection.views.nib')
    def test_load_nifti_slice(self, mock_nib):
        """Test loading NIfTI file and extracting slice"""
        # Create mock NIfTI data
        mock_data = np.random.rand(100, 100, 50) * 255
        mock_nii = MagicMock()
        mock_nii.get_fdata.return_value = mock_data
        mock_nib.load.return_value = mock_nii
        
        image = self.viewset._load_nifti_slice('/fake/path/scan.nii')
        
        self.assertIsInstance(image, Image.Image)
        self.assertEqual(image.mode, 'RGB')
        mock_nib.load.assert_called_once_with('/fake/path/scan.nii')
    
    @patch('detection.views.nib')
    def test_load_nifti_normalization(self, mock_nib):
        """Test NIfTI slice normalization to 0-255 range"""
        # Create mock data with known min/max
        mock_data = np.array([[[0, 50, 100], [150, 200, 255]]])
        mock_nii = MagicMock()
        mock_nii.get_fdata.return_value = mock_data
        mock_nib.load.return_value = mock_nii
        
        image = self.viewset._load_nifti_slice('/fake/path/scan.nii')
        
        # Image should be created successfully
        self.assertIsInstance(image, Image.Image)
    
    @patch('detection.views.nib')
    def test_load_nifti_error_handling(self, mock_nib):
        """Test NIfTI loading error handling"""
        mock_nib.load.side_effect = Exception('File not found')
        
        with self.assertRaises(ValueError) as context:
            self.viewset._load_nifti_slice('/fake/path/scan.nii')
        
        self.assertIn('Failed to process NIfTI file', str(context.exception))
    
    def test_process_image_classification_threshold(self):
        """Test classification uses correct threshold (0.5)"""
        image_bytes = self.create_test_image()
        
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp_file:
            tmp_file.write(image_bytes)
            tmp_file_path = tmp_file.name
        
        try:
            detection = DetectionResult.objects.create(
                user=self.user,
                uploaded_file=SimpleUploadedFile('test.jpg', image_bytes, 'image/jpeg'),
                file_size=len(image_bytes)
            )
            
            with patch('django.core.files.storage.FileSystemStorage.path', return_value=tmp_file_path):
                with patch('detection.views.ModelLoader') as mock_loader_class:
                    mock_loader = MagicMock()
                    mock_loader_class.return_value = mock_loader
                    mock_loader.model = MagicMock()
                    mock_loader.device = 'cpu'
                    
                    with patch('detection.views.torch') as mock_torch:
                        # Test above threshold (>= 0.5)
                        mock_output = MagicMock()
                        mock_output.item.return_value = 0.3
                        mock_loader.model.return_value = mock_output
                        
                        mock_sigmoid = MagicMock()
                        mock_sigmoid.item.return_value = 0.65  # >= 0.5
                        mock_torch.sigmoid.return_value = mock_sigmoid
                        mock_torch.no_grad.return_value.__enter__ = MagicMock()
                        mock_torch.no_grad.return_value.__exit__ = MagicMock()
                        
                        result = self.viewset._process_image(detection)
                        self.assertEqual(result['predicted_class'], 'Alzheimer\'s Disease (AD)')
                        
                        # Test below threshold (< 0.5)
                        mock_sigmoid.item.return_value = 0.35  # < 0.5
                        
                        result = self.viewset._process_image(detection)
                        self.assertEqual(result['predicted_class'], 'Control (CN)')
        finally:
            if os.path.exists(tmp_file_path):
                os.remove(tmp_file_path)
    
    def test_process_image_confidence_calculation(self):
        """Test confidence is max(probability, 1-probability)"""
        image_bytes = self.create_test_image()
        
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp_file:
            tmp_file.write(image_bytes)
            tmp_file_path = tmp_file.name
        
        try:
            detection = DetectionResult.objects.create(
                user=self.user,
                uploaded_file=SimpleUploadedFile('test.jpg', image_bytes, 'image/jpeg'),
                file_size=len(image_bytes)
            )
            
            with patch('django.core.files.storage.FileSystemStorage.path', return_value=tmp_file_path):
                with patch('detection.views.ModelLoader') as mock_loader_class:
                    mock_loader = MagicMock()
                    mock_loader_class.return_value = mock_loader
                    mock_loader.model = MagicMock()
                    mock_loader.device = 'cpu'
                    
                    with patch('detection.views.torch') as mock_torch:
                        mock_output = MagicMock()
                        mock_output.item.return_value = 0.5
                        mock_loader.model.return_value = mock_output
                        
                        # Test with probability > 0.5
                        mock_sigmoid = MagicMock()
                        mock_sigmoid.item.return_value = 0.85
                        mock_torch.sigmoid.return_value = mock_sigmoid
                        mock_torch.no_grad.return_value.__enter__ = MagicMock()
                        mock_torch.no_grad.return_value.__exit__ = MagicMock()
                        
                        result = self.viewset._process_image(detection)
                        self.assertEqual(result['confidence'], 0.85)
                        
                        # Test with probability < 0.5
                        mock_sigmoid.item.return_value = 0.25
                        result = self.viewset._process_image(detection)
                        self.assertEqual(result['confidence'], 0.75)  # 1 - 0.25
        finally:
            if os.path.exists(tmp_file_path):
                os.remove(tmp_file_path)
