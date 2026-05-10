"""
Unit tests for detection models
Tests DetectionResult and ModelMetadata models
"""
from datetime import datetime, timedelta
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from detection.models import DetectionResult, ModelMetadata

User = get_user_model()


class DetectionResultModelTests(TestCase):

    def setUp(self):
        self.patient = User.objects.create_user(
            email='patient1@test.com', password='testpass123',
            first_name='Test', last_name='Patient', role='patient'
        )
        self.doctor = User.objects.create_user(
            email='doctor1@test.com', password='testpass123',
            first_name='Dr', last_name='Test', role='doctor'
        )
        self.test_file = SimpleUploadedFile(
            "test_mri.jpg", b"fake image content", content_type="image/jpeg"
        )

    def _make_file(self, name="test.jpg"):
        return SimpleUploadedFile(name, b"content", "image/jpeg")

    def test_create_detection_result_minimal(self):
        detection = DetectionResult.objects.create(
            patient=self.patient,
            uploaded_file=self.test_file,
            file_size=1024
        )
        self.assertIsNotNone(detection.id)
        self.assertEqual(detection.patient, self.patient)
        self.assertEqual(detection.status, 'pending')
        self.assertEqual(detection.file_size, 1024)
        self.assertIsNotNone(detection.upload_date)
        self.assertIsNone(detection.predicted_class)
        self.assertIsNone(detection.confidence_score)

    def test_create_detection_result_complete(self):
        detection = DetectionResult.objects.create(
            patient=self.patient,
            doctor=self.doctor,
            uploaded_file=self.test_file,
            file_size=2048,
            status='completed',
            predicted_class='alzheimers',
            confidence_score=0.92,
            prediction_probability={'alzheimers': 0.92, 'cn': 0.08},
            model_version='v2.0',
            processing_time=1.5,
            analysis_details={'threshold': 0.5, 'model': 'ResNet-34'},
            patient_age=72,
            patient_gender='Male',
            notes='Patient shows symptoms',
            clinician_notes='Requires further investigation',
        )
        self.assertEqual(detection.predicted_class, 'alzheimers')
        self.assertEqual(detection.confidence_score, 0.92)
        self.assertEqual(detection.patient_age, 72)
        self.assertEqual(detection.doctor, self.doctor)
        self.assertEqual(detection.model_version, 'v2.0')
        self.assertIn('threshold', detection.analysis_details)

    def test_detection_result_status_choices(self):
        for status_choice in ['pending', 'processing', 'completed', 'failed']:
            detection = DetectionResult.objects.create(
                patient=self.patient,
                uploaded_file=self._make_file(f"test_{status_choice}.jpg"),
                file_size=1024,
                status=status_choice
            )
            self.assertEqual(detection.status, status_choice)

    def test_detection_result_patient_relationship(self):
        det1 = DetectionResult.objects.create(
            patient=self.patient,
            uploaded_file=self._make_file("test1.jpg"),
            file_size=1024
        )
        det2 = DetectionResult.objects.create(
            patient=self.patient,
            uploaded_file=self._make_file("test2.jpg"),
            file_size=2048
        )
        user_detections = self.patient.patient_detections.all()
        self.assertEqual(user_detections.count(), 2)
        self.assertIn(det1, user_detections)
        self.assertIn(det2, user_detections)

    def test_detection_result_ordering(self):
        det1 = DetectionResult.objects.create(
            patient=self.patient,
            uploaded_file=self._make_file("test1.jpg"),
            file_size=1024
        )
        det2 = DetectionResult.objects.create(
            patient=self.patient,
            uploaded_file=self._make_file("test2.jpg"),
            file_size=2048
        )
        results = list(DetectionResult.objects.all())
        self.assertEqual(results[0], det2)
        self.assertEqual(results[1], det1)

    def test_detection_result_str_with_prediction(self):
        detection = DetectionResult.objects.create(
            patient=self.patient,
            uploaded_file=self.test_file,
            file_size=1024,
            predicted_class='cn',
            confidence_score=0.85,
            status='completed'
        )
        s = str(detection)
        self.assertIn(detection.detection_id, s)

    def test_detection_result_str_pending(self):
        detection = DetectionResult.objects.create(
            patient=self.patient,
            uploaded_file=self.test_file,
            file_size=1024,
        )
        s = str(detection)
        self.assertIn('Pending', s)

    def test_detection_result_cascade_delete_patient(self):
        detection = DetectionResult.objects.create(
            patient=self.patient,
            uploaded_file=self.test_file,
            file_size=1024
        )
        det_id = detection.id
        self.patient.delete()
        self.assertFalse(DetectionResult.objects.filter(id=det_id).exists())

    def test_detection_result_json_fields(self):
        prediction_prob = {'alzheimers': 0.65, 'cn': 0.35}
        analysis = {
            'raw_output': 0.32,
            'sigmoid_probability': 0.65,
            'threshold_used': 0.5,
            'model_version': 'ResNet-34-v1.0'
        }
        detection = DetectionResult.objects.create(
            patient=self.patient,
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
        detection = DetectionResult.objects.create(
            patient=self.patient,
            uploaded_file=self.test_file,
            file_size=1024
        )
        created_time = detection.created_at
        self.assertIsNotNone(created_time)
        detection.status = 'completed'
        detection.save()
        self.assertGreaterEqual(detection.updated_at, created_time)

    def test_detection_result_default_values(self):
        detection = DetectionResult.objects.create(
            patient=self.patient,
            uploaded_file=self.test_file,
            file_size=1024
        )
        self.assertEqual(detection.status, 'pending')
        self.assertEqual(detection.model_version, 'v1.0')
        self.assertEqual(detection.model_type, 'binary')

    def test_detection_id_auto_generated(self):
        det = DetectionResult.objects.create(
            patient=self.patient,
            uploaded_file=self.test_file,
            file_size=1024
        )
        self.assertTrue(det.detection_id.startswith('DET'))


class ModelMetadataModelTests(TestCase):

    def test_create_model_metadata_complete(self):
        metadata = ModelMetadata.objects.create(
            name='Dementia Detector',
            version='1.0.0',
            architecture='ResNet-34',
            accuracy=0.92,
            auc_score=0.95,
            sensitivity=0.89,
            specificity=0.93,
            trained_on=datetime.now().date(),
            is_active=True,
            model_path='models/dementia_detector.pth',
            description='Binary classifier for AD detection'
        )
        self.assertEqual(metadata.name, 'Dementia Detector')
        self.assertEqual(metadata.accuracy, 0.92)
        self.assertTrue(metadata.is_active)

    def test_model_metadata_str_representation(self):
        metadata = ModelMetadata.objects.create(
            name='AD Detector', version='2.1.0',
            architecture='ResNet-50', accuracy=0.94,
            auc_score=0.96, sensitivity=0.91, specificity=0.95,
            trained_on=datetime.now().date(),
            model_path='models/v2.pth'
        )
        s = str(metadata)
        self.assertIn('AD Detector', s)
        self.assertIn('2.1.0', s)

    def test_model_metadata_ordering(self):
        m1 = ModelMetadata.objects.create(
            name='Model V1', version='1.0', architecture='ResNet-34',
            accuracy=0.90, auc_score=0.92, sensitivity=0.88, specificity=0.90,
            trained_on=datetime.now().date(), model_path='models/v1.pth'
        )
        m2 = ModelMetadata.objects.create(
            name='Model V2', version='2.0', architecture='ResNet-50',
            accuracy=0.94, auc_score=0.96, sensitivity=0.92, specificity=0.94,
            trained_on=datetime.now().date(), model_path='models/v2.pth'
        )
        results = list(ModelMetadata.objects.all())
        self.assertEqual(results[0], m2)
        self.assertEqual(results[1], m1)

    def test_model_metadata_active_filter(self):
        active = ModelMetadata.objects.create(
            name='Active', version='1.0', architecture='R34',
            accuracy=0.92, auc_score=0.94, sensitivity=0.90, specificity=0.92,
            trained_on=datetime.now().date(), is_active=True, model_path='a.pth'
        )
        ModelMetadata.objects.create(
            name='Inactive', version='0.9', architecture='R18',
            accuracy=0.85, auc_score=0.87, sensitivity=0.83, specificity=0.86,
            trained_on=datetime.now().date(), is_active=False, model_path='i.pth'
        )
        active_models = ModelMetadata.objects.filter(is_active=True)
        self.assertEqual(active_models.count(), 1)
        self.assertEqual(active_models.first(), active)

    def test_model_metadata_metrics_precision(self):
        metadata = ModelMetadata.objects.create(
            name='Precise', version='1.0', architecture='ResNet-34',
            accuracy=0.923456, auc_score=0.956789,
            sensitivity=0.891234, specificity=0.934567,
            trained_on=datetime.now().date(), model_path='p.pth'
        )
        self.assertAlmostEqual(metadata.accuracy, 0.923456, places=6)

    def test_model_metadata_timestamps(self):
        metadata = ModelMetadata.objects.create(
            name='TS', version='1.0', architecture='R34',
            accuracy=0.92, auc_score=0.94, sensitivity=0.90, specificity=0.92,
            trained_on=datetime.now().date(), model_path='ts.pth'
        )
        self.assertIsNotNone(metadata.created_at)
        self.assertIsNotNone(metadata.updated_at)

    def test_model_metadata_default_is_active(self):
        metadata = ModelMetadata.objects.create(
            name='Def', version='1.0', architecture='R34',
            accuracy=0.92, auc_score=0.94, sensitivity=0.90, specificity=0.92,
            trained_on=datetime.now().date(), model_path='d.pth'
        )
        self.assertTrue(metadata.is_active)
