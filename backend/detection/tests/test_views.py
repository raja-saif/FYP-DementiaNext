"""
Unit tests for detection views
Tests ModelLoader and image processing logic
"""
import os
import io
import tempfile
from unittest.mock import patch, MagicMock
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image
import numpy as np
from detection.views import ModelLoader, SubtypeModelLoader, DetectionViewSet
from detection.models import DetectionResult

User = get_user_model()


class ModelLoaderTests(TestCase):

    def setUp(self):
        ModelLoader._instance = None
        ModelLoader._model = None
        ModelLoader._device = None

    def test_singleton(self):
        loader1 = ModelLoader()
        loader2 = ModelLoader()
        self.assertIs(loader1, loader2)

    @patch('detection.views.torch')
    def test_device_cpu(self, mock_torch):
        mock_torch.cuda.is_available.return_value = False
        mock_torch.device.return_value = 'cpu'
        loader = ModelLoader()
        loader.device
        mock_torch.device.assert_called_with('cpu')

    @patch('detection.views.torch')
    def test_device_cuda(self, mock_torch):
        mock_torch.cuda.is_available.return_value = True
        mock_torch.device.return_value = 'cuda'
        loader = ModelLoader()
        loader.device
        mock_torch.device.assert_called_with('cuda')

    @patch('detection.views.os.path.exists')
    @patch('detection.views.torch')
    @patch('detection.views.resnet34')
    @patch('detection.views.settings')
    def test_load_model_file_exists(self, mock_settings, mock_resnet34, mock_torch, mock_exists):
        mock_settings.BASE_DIR = '/fake/path'
        mock_exists.return_value = True
        mock_backbone = MagicMock()
        mock_backbone.fc = MagicMock()
        mock_backbone.fc.in_features = 512
        mock_resnet34.return_value = mock_backbone
        mock_torch.load.return_value = {'model_state_dict': {}}
        mock_torch.device.return_value = 'cpu'
        mock_torch.cuda.is_available.return_value = False
        mock_torch.nn.Sequential = MagicMock()
        mock_torch.nn.Dropout = MagicMock()
        mock_torch.nn.Linear = MagicMock()
        mock_torch.nn.Module = type('Module', (), {'__init__': lambda s, *a: None, 'forward': lambda s, x: x, 'to': lambda s, d: s, 'eval': lambda s: s, 'load_state_dict': lambda s, d: None})

        loader = ModelLoader()
        model = loader.model
        self.assertIsNotNone(model)
        mock_torch.load.assert_called_once()

    @patch('detection.views.os.path.exists')
    @patch('detection.views.torch')
    @patch('detection.views.resnet34')
    @patch('detection.views.settings')
    def test_load_model_file_not_exists(self, mock_settings, mock_resnet34, mock_torch, mock_exists):
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
        mock_torch.nn.Module = type('Module', (), {'__init__': lambda s, *a: None, 'forward': lambda s, x: x, 'to': lambda s, d: s, 'eval': lambda s: s})

        loader = ModelLoader()
        model = loader.model
        self.assertIsNotNone(model)
        mock_torch.load.assert_not_called()


class SubtypeModelLoaderTests(TestCase):

    def setUp(self):
        SubtypeModelLoader._instance = None
        SubtypeModelLoader._model = None
        SubtypeModelLoader._device = None

    def test_singleton(self):
        l1 = SubtypeModelLoader()
        l2 = SubtypeModelLoader()
        self.assertIs(l1, l2)

    def test_class_names(self):
        self.assertEqual(SubtypeModelLoader.CLASS_NAMES, ['ad', 'pd', 'ftd', 'cn'])

    def test_class_display_mapping(self):
        self.assertIn('ad', SubtypeModelLoader.CLASS_DISPLAY)
        self.assertIn('cn', SubtypeModelLoader.CLASS_DISPLAY)


class ImageProcessingTests(TestCase):

    def setUp(self):
        self.patient = User.objects.create_user(
            email='imgproc@test.com', password='testpass123',
            first_name='Img', last_name='Proc', role='patient'
        )
        self.viewset = DetectionViewSet()
        self.viewset.request = MagicMock()
        self.viewset.request.user = self.patient

    def _make_image_bytes(self, size=(224, 224)):
        img = Image.new('RGB', size, color='gray')
        buf = io.BytesIO()
        img.save(buf, format='JPEG')
        buf.seek(0)
        return buf.getvalue()

    @patch('detection.views.Image', Image)
    @patch('detection.views.np', np)
    @patch('detection.views.nib')
    def test_load_nifti_slice(self, mock_nib):
        mock_data = np.random.rand(100, 100, 50) * 255
        mock_nii = MagicMock()
        mock_nii.get_fdata.return_value = mock_data
        mock_nib.load.return_value = mock_nii

        image = self.viewset._load_nifti_slice('/fake/path/scan.nii')
        self.assertIsInstance(image, Image.Image)
        self.assertEqual(image.mode, 'RGB')

    @patch('detection.views.Image', Image)
    @patch('detection.views.np', np)
    @patch('detection.views.nib')
    def test_load_nifti_normalization(self, mock_nib):
        mock_data = np.array([[[0, 50, 100], [150, 200, 255]]])
        mock_nii = MagicMock()
        mock_nii.get_fdata.return_value = mock_data
        mock_nib.load.return_value = mock_nii

        image = self.viewset._load_nifti_slice('/fake/path/scan.nii')
        self.assertIsInstance(image, Image.Image)

    @patch('detection.views.nib')
    def test_load_nifti_error_handling(self, mock_nib):
        mock_nib.load.side_effect = Exception('File not found')
        with self.assertRaises(ValueError) as ctx:
            self.viewset._load_nifti_slice('/fake/path/scan.nii')
        self.assertIn('Failed to process NIfTI file', str(ctx.exception))

    def test_is_mri_file(self):
        self.assertTrue(DetectionViewSet._is_mri_file('scan.nii'))
        self.assertTrue(DetectionViewSet._is_mri_file('scan.nii.gz'))
        self.assertTrue(DetectionViewSet._is_mri_file('scan.dcm'))
        self.assertTrue(DetectionViewSet._is_mri_file('archive.zip'))
        self.assertFalse(DetectionViewSet._is_mri_file('image.jpg'))
        self.assertFalse(DetectionViewSet._is_mri_file('image.png'))

    def test_is_nifti_path(self):
        self.assertTrue(DetectionViewSet._is_nifti_path('scan.nii'))
        self.assertTrue(DetectionViewSet._is_nifti_path('scan.nii.gz'))
        self.assertFalse(DetectionViewSet._is_nifti_path('scan.dcm'))
        self.assertFalse(DetectionViewSet._is_nifti_path(''))
        self.assertFalse(DetectionViewSet._is_nifti_path(None))

    @patch('detection.views.Image', Image)
    @patch('detection.views.np', np)
    @patch('detection.views.nib')
    def test_nifti_slice_to_pil(self, mock_nib):
        volume = np.random.rand(64, 64, 30) * 255
        img = self.viewset._nifti_slice_to_pil(volume, 15)
        self.assertIsInstance(img, Image.Image)
        self.assertEqual(img.mode, 'RGB')

    def test_find_pipeline_output_nifti_no_dir(self):
        result = self.viewset._find_pipeline_output_nifti('/nonexistent/path/file.zip')
        self.assertIsNone(result)
