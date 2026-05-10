"""
Unit tests for detection serializers
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
    ModelMetadataSerializer,
)

User = get_user_model()


class DetectionResultSerializerTests(TestCase):

    def setUp(self):
        self.patient = User.objects.create_user(
            email='ser_pat@test.com', password='testpass123',
            first_name='Test', last_name='Patient', role='patient'
        )
        self.test_file = SimpleUploadedFile(
            "test_mri.jpg", b"fake image content", content_type="image/jpeg"
        )
        self.detection = DetectionResult.objects.create(
            patient=self.patient,
            uploaded_file=self.test_file,
            file_size=1024,
            status='completed',
            predicted_class='alzheimers',
            confidence_score=0.89,
            prediction_probability={'alzheimers': 0.89, 'cn': 0.11},
            model_version='v1.0',
            processing_time=1.2,
            analysis_details={'model': 'ResNet-34'},
            patient_age=68,
            patient_gender='Female'
        )

    def test_serializer_contains_key_fields(self):
        data = DetectionResultSerializer(self.detection).data
        for field in ['id', 'status', 'predicted_class', 'confidence_score',
                      'prediction_probability', 'model_version', 'processing_time',
                      'analysis_details', 'patient_age', 'patient_gender',
                      'upload_date', 'created_at', 'updated_at',
                      'patient_name', 'patient_email',
                      'predicted_class_display', 'review_status']:
            self.assertIn(field, data, f"Missing field: {field}")

    def test_patient_name_field(self):
        data = DetectionResultSerializer(self.detection).data
        self.assertEqual(data['patient_name'], 'Test Patient')

    def test_patient_email_field(self):
        data = DetectionResultSerializer(self.detection).data
        self.assertEqual(data['patient_email'], 'ser_pat@test.com')

    def test_predicted_class_display(self):
        data = DetectionResultSerializer(self.detection).data
        self.assertEqual(data['predicted_class_display'], "Alzheimer's Disease")

    def test_review_status_needs_review(self):
        data = DetectionResultSerializer(self.detection).data
        self.assertEqual(data['review_status'], 'needs_review')

    def test_read_only_fields(self):
        data = {
            'predicted_class': 'cn',
            'confidence_score': 0.5,
            'patient_age': 75
        }
        ser = DetectionResultSerializer(self.detection, data=data, partial=True)
        self.assertTrue(ser.is_valid())
        updated = ser.save()
        self.assertEqual(updated.predicted_class, 'alzheimers')
        self.assertEqual(updated.patient_age, 75)

    def test_json_fields_serialized(self):
        data = DetectionResultSerializer(self.detection).data
        self.assertIsInstance(data['prediction_probability'], dict)
        self.assertIn('alzheimers', data['prediction_probability'])

    def test_multiple_detections(self):
        DetectionResult.objects.create(
            patient=self.patient,
            uploaded_file=SimpleUploadedFile("t2.jpg", b"c", "image/jpeg"),
            file_size=2048, status='pending'
        )
        detections = DetectionResult.objects.all()
        ser = DetectionResultSerializer(detections, many=True)
        self.assertEqual(len(ser.data), 2)


class DetectionUploadSerializerTests(TestCase):

    def _make_file(self, name='test.jpg', size=1024, ct='image/jpeg'):
        return SimpleUploadedFile(name, b"x" * size, content_type=ct)

    def test_valid_jpg(self):
        ser = DetectionUploadSerializer(data={'uploaded_file': self._make_file('s.jpg')})
        self.assertTrue(ser.is_valid(), ser.errors)

    def test_valid_png(self):
        ser = DetectionUploadSerializer(data={'uploaded_file': self._make_file('s.png', ct='image/png')})
        self.assertTrue(ser.is_valid(), ser.errors)

    def test_valid_nifti(self):
        ser = DetectionUploadSerializer(data={'uploaded_file': self._make_file('b.nii', ct='application/octet-stream')})
        self.assertTrue(ser.is_valid(), ser.errors)

    def test_valid_nifti_gz(self):
        ser = DetectionUploadSerializer(data={'uploaded_file': self._make_file('b.nii.gz', ct='application/gzip')})
        self.assertTrue(ser.is_valid(), ser.errors)

    def test_valid_dcm(self):
        ser = DetectionUploadSerializer(data={'uploaded_file': self._make_file('s.dcm', ct='application/dicom')})
        self.assertTrue(ser.is_valid(), ser.errors)

    def test_valid_zip(self):
        ser = DetectionUploadSerializer(data={'uploaded_file': self._make_file('d.zip', ct='application/zip')})
        self.assertTrue(ser.is_valid(), ser.errors)

    def test_rejects_invalid_type(self):
        ser = DetectionUploadSerializer(data={'uploaded_file': self._make_file('d.pdf', ct='application/pdf')})
        self.assertFalse(ser.is_valid())
        self.assertIn('uploaded_file', ser.errors)

    def test_rejects_oversized_image(self):
        ser = DetectionUploadSerializer(data={'uploaded_file': self._make_file('l.jpg', size=11 * 1024 * 1024)})
        self.assertFalse(ser.is_valid())
        self.assertIn('uploaded_file', ser.errors)

    def test_accepts_large_nifti(self):
        ser = DetectionUploadSerializer(data={'uploaded_file': self._make_file('n.nii.gz', size=30 * 1024 * 1024, ct='application/gzip')})
        self.assertTrue(ser.is_valid(), ser.errors)

    def test_rejects_oversized_nifti(self):
        ser = DetectionUploadSerializer(data={'uploaded_file': self._make_file('n.nii.gz', size=201 * 1024 * 1024, ct='application/gzip')})
        self.assertFalse(ser.is_valid())

    def test_optional_fields(self):
        ser = DetectionUploadSerializer(data={'uploaded_file': self._make_file()})
        self.assertTrue(ser.is_valid())
        self.assertIsNone(ser.validated_data.get('patient_age'))
        self.assertIsNone(ser.validated_data.get('patient_gender'))

    def test_with_all_fields(self):
        ser = DetectionUploadSerializer(data={
            'uploaded_file': self._make_file(),
            'patient_age': 72, 'patient_gender': 'Female',
            'notes': 'Memory issues'
        })
        self.assertTrue(ser.is_valid())
        self.assertEqual(ser.validated_data['patient_age'], 72)

    def test_missing_file(self):
        ser = DetectionUploadSerializer(data={'patient_age': 65})
        self.assertFalse(ser.is_valid())
        self.assertIn('uploaded_file', ser.errors)

    def test_case_insensitive_extension(self):
        ser = DetectionUploadSerializer(data={'uploaded_file': self._make_file('SCAN.JPG')})
        self.assertTrue(ser.is_valid())


class ModelMetadataSerializerTests(TestCase):

    def setUp(self):
        self.metadata = ModelMetadata.objects.create(
            name='Dementia Detector', version='1.0.0',
            architecture='ResNet-34', accuracy=0.92,
            auc_score=0.95, sensitivity=0.89, specificity=0.93,
            trained_on=datetime(2024, 1, 15).date(),
            is_active=True, model_path='models/dd.pth',
            description='Binary classifier'
        )

    def test_contains_key_fields(self):
        data = ModelMetadataSerializer(self.metadata).data
        for field in ['id', 'name', 'version', 'architecture', 'accuracy',
                      'auc_score', 'sensitivity', 'specificity', 'trained_on',
                      'is_active', 'description', 'model_path',
                      'created_at', 'updated_at']:
            self.assertIn(field, data, f"Missing: {field}")

    def test_field_values(self):
        data = ModelMetadataSerializer(self.metadata).data
        self.assertEqual(data['name'], 'Dementia Detector')
        self.assertEqual(data['version'], '1.0.0')
        self.assertEqual(data['accuracy'], 0.92)

    def test_multiple_models(self):
        ModelMetadata.objects.create(
            name='V2', version='2.0', architecture='R50',
            accuracy=0.94, auc_score=0.96, sensitivity=0.91, specificity=0.95,
            trained_on=datetime(2024, 6, 1).date(), model_path='v2.pth'
        )
        ser = ModelMetadataSerializer(ModelMetadata.objects.all(), many=True)
        self.assertEqual(len(ser.data), 2)

    def test_read_only_id(self):
        data = {
            'id': 9999, 'name': 'Test', 'version': '1.0',
            'architecture': 'R34', 'accuracy': 0.90,
            'auc_score': 0.92, 'sensitivity': 0.88, 'specificity': 0.90,
            'trained_on': datetime.now().date(), 'is_active': True,
            'model_path': 'm.pth',
        }
        ser = ModelMetadataSerializer(data=data)
        self.assertTrue(ser.is_valid())
        self.assertNotIn('id', ser.validated_data)

    def test_metric_precision(self):
        m = ModelMetadata.objects.create(
            name='Precise', version='1.0', architecture='R34',
            accuracy=0.923456, auc_score=0.956789,
            sensitivity=0.891234, specificity=0.934567,
            trained_on=datetime.now().date(), model_path='p.pth'
        )
        data = ModelMetadataSerializer(m).data
        self.assertAlmostEqual(data['accuracy'], 0.923456, places=5)
