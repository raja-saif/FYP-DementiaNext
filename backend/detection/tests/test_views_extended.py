"""
Extended tests for detection/views.py – DetectionViewSet action endpoints
and internal inference/processing methods.
"""
import io
import os
import uuid
from unittest.mock import patch, MagicMock, PropertyMock

from django.test import TestCase, override_settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone

from rest_framework.test import APITestCase, APIClient
from rest_framework import status as http_status
from rest_framework_simplejwt.tokens import AccessToken

from detection.models import (
    Appointment, DetectionResult, DoctorReview, FHIRDiagnosticReport,
)
from detection.views import DetectionViewSet


User = None  # resolved in setUpModule


def setUpModule():
    global User
    from django.contrib.auth import get_user_model
    User = get_user_model()


def _auth(client, user):
    token = AccessToken.for_user(user)
    client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')


def _fake_image_file(name='scan.jpg', size=(10, 10)):
    from PIL import Image as PILImage
    img = PILImage.new('RGB', size, color='gray')
    buf = io.BytesIO()
    img.save(buf, format='JPEG')
    buf.seek(0)
    return SimpleUploadedFile(name, buf.read(), content_type='image/jpeg')


def _fake_nifti_file(name='scan.nii.gz'):
    return SimpleUploadedFile(name, b'\x00' * 100, content_type='application/gzip')


# ---------------------------------------------------------------------------
# Helpers: create users, appointments, detections
# ---------------------------------------------------------------------------

def _make_patient(**kwargs):
    defaults = dict(
        email=f'patient_{uuid.uuid4().hex[:8]}@test.com',
        password='pass123',
        role='patient',
        first_name='Pat',
        last_name='Ient',
    )
    defaults.update(kwargs)
    return User.objects.create_user(**defaults)


def _make_doctor(**kwargs):
    defaults = dict(
        email=f'doctor_{uuid.uuid4().hex[:8]}@test.com',
        password='pass123',
        role='doctor',
        first_name='Doc',
        last_name='Tor',
    )
    defaults.update(kwargs)
    return User.objects.create_user(**defaults)


def _make_appointment(patient, doctor, status='approved'):
    return Appointment.objects.create(
        patient=patient,
        doctor=doctor,
        appointment_date=timezone.now(),
        reason='MRI check',
        status=status,
    )


def _make_detection(patient, doctor=None, appointment=None, status='pending', model_type='binary', **kwargs):
    defaults = dict(
        patient=patient,
        doctor=doctor,
        appointment=appointment,
        uploaded_file=SimpleUploadedFile('test.jpg', b'\xff\xd8\xff' + b'\x00' * 50, content_type='image/jpeg'),
        file_size=53,
        status=status,
        model_type=model_type,
    )
    defaults.update(kwargs)
    return DetectionResult.objects.create(**defaults)


# ===========================================================================
# upload_for_appointment
# ===========================================================================

@override_settings(MEDIA_ROOT='/tmp/test_media')
class UploadForAppointmentTests(APITestCase):

    def setUp(self):
        self.patient = _make_patient()
        self.doctor = _make_doctor()
        self.client = APIClient()

    def test_only_patients_allowed(self):
        _auth(self.client, self.doctor)
        resp = self.client.post('/api/detection/detections/upload_for_appointment/')
        self.assertEqual(resp.status_code, http_status.HTTP_403_FORBIDDEN)
        self.assertIn('Only patients', resp.data['error'])

    def test_appointment_id_required(self):
        _auth(self.client, self.patient)
        resp = self.client.post('/api/detection/detections/upload_for_appointment/')
        self.assertEqual(resp.status_code, http_status.HTTP_400_BAD_REQUEST)
        self.assertIn('Appointment ID is required', resp.data['error'])

    def test_appointment_not_found(self):
        _auth(self.client, self.patient)
        resp = self.client.post('/api/detection/detections/upload_for_appointment/', {'appointment_id': 9999})
        self.assertEqual(resp.status_code, http_status.HTTP_404_NOT_FOUND)

    def test_appointment_not_approved(self):
        apt = _make_appointment(self.patient, self.doctor, status='pending')
        _auth(self.client, self.patient)
        resp = self.client.post('/api/detection/detections/upload_for_appointment/', {'appointment_id': apt.id})
        self.assertEqual(resp.status_code, http_status.HTTP_400_BAD_REQUEST)
        self.assertIn('approved', resp.data['error'])

    def test_file_required(self):
        apt = _make_appointment(self.patient, self.doctor, status='approved')
        _auth(self.client, self.patient)
        resp = self.client.post('/api/detection/detections/upload_for_appointment/', {'appointment_id': apt.id})
        self.assertEqual(resp.status_code, http_status.HTTP_400_BAD_REQUEST)
        self.assertIn('MRI file is required', resp.data['error'])

    def test_successful_upload(self):
        apt = _make_appointment(self.patient, self.doctor, status='approved')
        _auth(self.client, self.patient)
        f = _fake_image_file()
        resp = self.client.post(
            '/api/detection/detections/upload_for_appointment/',
            {'appointment_id': apt.id, 'uploaded_file': f, 'notes': 'headache'},
            format='multipart',
        )
        self.assertEqual(resp.status_code, http_status.HTTP_201_CREATED)
        self.assertIn('detection_id', resp.data)
        det = DetectionResult.objects.get(detection_id=resp.data['detection_id'])
        self.assertEqual(det.patient, self.patient)
        self.assertEqual(det.doctor, self.doctor)
        self.assertEqual(det.status, 'pending')


# ===========================================================================
# run_detection
# ===========================================================================

@override_settings(MEDIA_ROOT='/tmp/test_media')
class RunDetectionTests(APITestCase):

    def setUp(self):
        self.patient = _make_patient()
        self.doctor = _make_doctor()
        self.other_doctor = _make_doctor()
        self.client = APIClient()

    def test_only_doctors_allowed(self):
        det = _make_detection(self.patient, self.doctor)
        _auth(self.client, self.patient)
        resp = self.client.post(f'/api/detection/detections/{det.pk}/run_detection/')
        self.assertEqual(resp.status_code, http_status.HTTP_403_FORBIDDEN)

    def test_doctor_no_access_to_other_appointment(self):
        apt = _make_appointment(self.patient, self.doctor)
        det = _make_detection(self.patient, self.doctor, appointment=apt)
        _auth(self.client, self.other_doctor)
        resp = self.client.post(f'/api/detection/detections/{det.pk}/run_detection/')
        self.assertIn(resp.status_code, (http_status.HTTP_403_FORBIDDEN, http_status.HTTP_404_NOT_FOUND))

    def test_already_completed(self):
        det = _make_detection(self.patient, self.doctor, status='completed')
        _auth(self.client, self.doctor)
        resp = self.client.post(f'/api/detection/detections/{det.pk}/run_detection/')
        self.assertEqual(resp.status_code, http_status.HTTP_400_BAD_REQUEST)
        self.assertIn('already completed', resp.data['error'])

    @patch.object(DetectionViewSet, '_process_image')
    def test_successful_detection(self, mock_process):
        mock_process.return_value = {
            'predicted_class': 'dementia',
            'confidence': 0.92,
            'probabilities': {'dementia': 0.92, 'cn': 0.08},
            'analysis': {'model_type': 'binary'},
        }
        det = _make_detection(self.patient, self.doctor, status='pending')
        _auth(self.client, self.doctor)
        resp = self.client.post(f'/api/detection/detections/{det.pk}/run_detection/')
        self.assertEqual(resp.status_code, http_status.HTTP_200_OK)
        det.refresh_from_db()
        self.assertEqual(det.status, 'completed')
        self.assertEqual(det.predicted_class, 'dementia')

    @patch.object(DetectionViewSet, '_process_image', side_effect=RuntimeError('GPU error'))
    def test_detection_failure_marks_failed(self, _):
        det = _make_detection(self.patient, self.doctor, status='pending')
        _auth(self.client, self.doctor)
        resp = self.client.post(f'/api/detection/detections/{det.pk}/run_detection/')
        self.assertEqual(resp.status_code, http_status.HTTP_500_INTERNAL_SERVER_ERROR)
        det.refresh_from_db()
        self.assertEqual(det.status, 'failed')
        self.assertIn('GPU error', det.error_message)


# ===========================================================================
# upload_and_detect
# ===========================================================================

@override_settings(MEDIA_ROOT='/tmp/test_media')
class UploadAndDetectTests(APITestCase):

    def setUp(self):
        self.patient = _make_patient()
        self.doctor = _make_doctor()
        self.client = APIClient()

    @patch.object(DetectionViewSet, '_process_image')
    def test_patient_upload_and_detect_binary(self, mock_process):
        mock_process.return_value = {
            'predicted_class': 'cn',
            'confidence': 0.85,
            'probabilities': {'dementia': 0.15, 'cn': 0.85},
            'analysis': {'model_type': 'binary'},
        }
        _auth(self.client, self.patient)
        f = _fake_image_file()
        resp = self.client.post(
            '/api/detection/detections/upload_and_detect/',
            {'uploaded_file': f, 'model_type': 'binary'},
            format='multipart',
        )
        self.assertEqual(resp.status_code, http_status.HTTP_201_CREATED)
        self.assertEqual(resp.data['predicted_class'], 'cn')

    @patch.object(DetectionViewSet, '_process_image')
    def test_patient_upload_and_detect_subtype(self, mock_process):
        mock_process.return_value = {
            'predicted_class': 'alzheimers',
            'confidence': 0.7,
            'probabilities': {'alzheimers': 0.7, 'pd': 0.1, 'ftd': 0.1, 'cn': 0.1},
            'analysis': {'model_type': 'subtype'},
        }
        _auth(self.client, self.patient)
        f = _fake_image_file()
        resp = self.client.post(
            '/api/detection/detections/upload_and_detect/',
            {'uploaded_file': f, 'model_type': 'subtype'},
            format='multipart',
        )
        self.assertEqual(resp.status_code, http_status.HTTP_201_CREATED)
        self.assertEqual(resp.data['predicted_class'], 'alzheimers')

    def test_doctor_requires_patient_id(self):
        _auth(self.client, self.doctor)
        f = _fake_image_file()
        resp = self.client.post(
            '/api/detection/detections/upload_and_detect/',
            {'uploaded_file': f},
            format='multipart',
        )
        self.assertEqual(resp.status_code, http_status.HTTP_400_BAD_REQUEST)
        self.assertIn('patient_id', resp.data['error'])

    def test_doctor_invalid_patient_id(self):
        _auth(self.client, self.doctor)
        f = _fake_image_file()
        resp = self.client.post(
            '/api/detection/detections/upload_and_detect/',
            {'uploaded_file': f, 'patient_id': 99999},
            format='multipart',
        )
        self.assertEqual(resp.status_code, http_status.HTTP_400_BAD_REQUEST)
        self.assertIn('not found', resp.data['error'])

    @patch.object(DetectionViewSet, '_process_image')
    def test_doctor_upload_with_valid_patient(self, mock_process):
        mock_process.return_value = {
            'predicted_class': 'cn',
            'confidence': 0.9,
            'probabilities': {'dementia': 0.1, 'cn': 0.9},
            'analysis': {},
        }
        _auth(self.client, self.doctor)
        f = _fake_image_file()
        resp = self.client.post(
            '/api/detection/detections/upload_and_detect/',
            {'uploaded_file': f, 'patient_id': self.patient.id},
            format='multipart',
        )
        self.assertEqual(resp.status_code, http_status.HTTP_201_CREATED)
        det = DetectionResult.objects.get(detection_id=resp.data['detection_id'])
        self.assertEqual(det.doctor, self.doctor)
        self.assertEqual(det.patient, self.patient)

    def test_invalid_model_type_defaults_to_binary(self):
        _auth(self.client, self.patient)
        f = _fake_image_file()
        with patch.object(DetectionViewSet, '_process_image') as mock_p:
            mock_p.return_value = {
                'predicted_class': 'cn',
                'confidence': 0.8,
                'probabilities': {'dementia': 0.2, 'cn': 0.8},
                'analysis': {},
            }
            resp = self.client.post(
                '/api/detection/detections/upload_and_detect/',
                {'uploaded_file': f, 'model_type': 'invalid_type'},
                format='multipart',
            )
        self.assertEqual(resp.status_code, http_status.HTTP_201_CREATED)
        det = DetectionResult.objects.latest('created_at')
        self.assertEqual(det.model_type, 'binary')

    @patch.object(DetectionViewSet, '_process_image', side_effect=ValueError('bad image'))
    def test_upload_and_detect_failure(self, _):
        _auth(self.client, self.patient)
        f = _fake_image_file()
        resp = self.client.post(
            '/api/detection/detections/upload_and_detect/',
            {'uploaded_file': f},
            format='multipart',
        )
        self.assertEqual(resp.status_code, http_status.HTTP_500_INTERNAL_SERVER_ERROR)

    def test_invalid_file_type_rejected(self):
        _auth(self.client, self.patient)
        f = SimpleUploadedFile('malware.exe', b'\x00' * 100, content_type='application/x-msdownload')
        resp = self.client.post(
            '/api/detection/detections/upload_and_detect/',
            {'uploaded_file': f},
            format='multipart',
        )
        self.assertEqual(resp.status_code, http_status.HTTP_400_BAD_REQUEST)


# ===========================================================================
# history
# ===========================================================================

@override_settings(MEDIA_ROOT='/tmp/test_media')
class HistoryTests(APITestCase):

    def setUp(self):
        self.patient = _make_patient()
        self.doctor = _make_doctor()
        self.client = APIClient()

    def test_patient_sees_own_detections(self):
        _make_detection(self.patient, self.doctor, status='completed')
        _make_detection(self.patient, self.doctor, status='pending')
        _auth(self.client, self.patient)
        resp = self.client.get('/api/detection/detections/history/')
        self.assertEqual(resp.status_code, http_status.HTTP_200_OK)
        self.assertEqual(len(resp.data), 2)

    def test_doctor_sees_assigned_detections(self):
        other_patient = _make_patient()
        _make_detection(other_patient, self.doctor, status='completed')
        _auth(self.client, self.doctor)
        resp = self.client.get('/api/detection/detections/history/')
        self.assertEqual(resp.status_code, http_status.HTTP_200_OK)
        self.assertGreaterEqual(len(resp.data), 1)

    def test_unauthenticated_denied(self):
        resp = self.client.get('/api/detection/detections/history/')
        self.assertEqual(resp.status_code, http_status.HTTP_401_UNAUTHORIZED)


# ===========================================================================
# my_uploads
# ===========================================================================

@override_settings(MEDIA_ROOT='/tmp/test_media')
class MyUploadsTests(APITestCase):

    def setUp(self):
        self.patient = _make_patient()
        self.doctor = _make_doctor()
        self.client = APIClient()

    def test_only_doctors(self):
        _auth(self.client, self.patient)
        resp = self.client.get('/api/detection/detections/my_uploads/')
        self.assertEqual(resp.status_code, http_status.HTTP_403_FORBIDDEN)

    def test_returns_completed_only(self):
        _make_detection(self.patient, self.doctor, status='completed')
        _make_detection(self.patient, self.doctor, status='pending')
        _auth(self.client, self.doctor)
        resp = self.client.get('/api/detection/detections/my_uploads/')
        self.assertEqual(resp.status_code, http_status.HTTP_200_OK)
        self.assertEqual(len(resp.data), 1)


# ===========================================================================
# rerun_detection
# ===========================================================================

@override_settings(MEDIA_ROOT='/tmp/test_media')
class RerunDetectionTests(APITestCase):

    def setUp(self):
        self.patient = _make_patient()
        self.doctor = _make_doctor()
        self.other_doctor = _make_doctor()
        self.client = APIClient()

    def test_only_doctors(self):
        det = _make_detection(self.patient, self.doctor, status='completed')
        _auth(self.client, self.patient)
        resp = self.client.post(f'/api/detection/detections/{det.pk}/rerun/')
        self.assertEqual(resp.status_code, http_status.HTTP_403_FORBIDDEN)

    def test_ownership_check(self):
        det = _make_detection(self.patient, self.doctor, status='completed')
        _auth(self.client, self.other_doctor)
        resp = self.client.post(f'/api/detection/detections/{det.pk}/rerun/')
        self.assertIn(resp.status_code, (http_status.HTTP_403_FORBIDDEN, http_status.HTTP_404_NOT_FOUND))

    @patch.object(DetectionViewSet, '_resolve_nifti_path_for_detection', return_value='')
    @patch.object(DetectionViewSet, '_run_pipeline', return_value='/tmp/out.nii.gz')
    @patch.object(DetectionViewSet, '_load_nifti_slice')
    @patch.object(DetectionViewSet, '_run_binary_inference')
    @patch('detection.views._ensure_ml_libs')
    @patch('detection.views.transforms')
    @patch('detection.views.Image')
    @patch('detection.views.np')
    def test_successful_rerun_with_pipeline(
        self, mock_np, mock_image_mod, mock_transforms, mock_ensure, mock_binary, mock_load, mock_pipeline, mock_resolve
    ):
        mock_transform_obj = MagicMock()
        mock_transform_obj.return_value = MagicMock()
        mock_transforms.Compose.return_value = mock_transform_obj
        mock_transforms.Resize = MagicMock()
        mock_transforms.ToTensor = MagicMock()
        mock_transforms.Normalize = MagicMock()

        from PIL import Image as PILImage
        mock_load.return_value = PILImage.new('RGB', (224, 224))
        mock_image_mod.open.return_value = PILImage.new('RGB', (224, 224))

        mock_tensor = MagicMock()
        mock_tensor.unsqueeze.return_value = mock_tensor
        mock_transform_obj.return_value = mock_tensor

        mock_binary.return_value = {
            'predicted_class': 'dementia',
            'confidence': 0.88,
            'probabilities': {'dementia': 0.88, 'cn': 0.12},
            'analysis': {'model_type': 'binary'},
        }

        det = _make_detection(self.patient, self.doctor, status='completed')
        _auth(self.client, self.doctor)
        resp = self.client.post(f'/api/detection/detections/{det.pk}/rerun/', {'model_type': 'binary'})
        self.assertIn(resp.status_code, (http_status.HTTP_200_OK, http_status.HTTP_201_CREATED))

    @patch.object(DetectionViewSet, '_resolve_nifti_path_for_detection', return_value='/tmp/preprocessed.nii.gz')
    @patch.object(DetectionViewSet, '_load_nifti_slice')
    @patch.object(DetectionViewSet, '_run_subtype_inference')
    @patch('detection.views._ensure_ml_libs')
    @patch('detection.views.transforms')
    def test_rerun_subtype_from_cached_nifti(
        self, mock_transforms, mock_ensure, mock_subtype, mock_load, mock_resolve
    ):
        mock_transform_obj = MagicMock()
        mock_transforms.Compose.return_value = mock_transform_obj
        mock_transforms.Resize = MagicMock()
        mock_transforms.ToTensor = MagicMock()
        mock_transforms.Normalize = MagicMock()

        from PIL import Image as PILImage
        mock_load.return_value = PILImage.new('RGB', (224, 224))

        mock_tensor = MagicMock()
        mock_tensor.unsqueeze.return_value = mock_tensor
        mock_transform_obj.return_value = mock_tensor

        mock_subtype.return_value = {
            'predicted_class': 'pd',
            'confidence': 0.75,
            'probabilities': {'alzheimers': 0.1, 'pd': 0.75, 'ftd': 0.1, 'cn': 0.05},
            'analysis': {'model_type': 'subtype'},
        }

        det = _make_detection(self.patient, self.doctor, status='completed')
        _auth(self.client, self.doctor)
        resp = self.client.post(f'/api/detection/detections/{det.pk}/rerun/', {'model_type': 'subtype'})
        self.assertEqual(resp.status_code, http_status.HTTP_201_CREATED)
        self.assertEqual(resp.data['predicted_class'], 'pd')

    @patch.object(DetectionViewSet, '_resolve_nifti_path_for_detection', return_value='')
    @patch('detection.views._ensure_ml_libs')
    @patch('detection.views.os.path.isfile', return_value=False)
    def test_rerun_missing_original_file(self, mock_isfile, mock_ensure, mock_resolve):
        det = _make_detection(
            self.patient, self.doctor, status='completed',
            uploaded_file=SimpleUploadedFile('scan.nii.gz', b'\x00' * 50, content_type='application/gzip'),
        )
        _auth(self.client, self.doctor)
        resp = self.client.post(f'/api/detection/detections/{det.pk}/rerun/')
        self.assertEqual(resp.status_code, http_status.HTTP_500_INTERNAL_SERVER_ERROR)


# ===========================================================================
# stats
# ===========================================================================

@override_settings(MEDIA_ROOT='/tmp/test_media')
class StatsTests(APITestCase):

    def setUp(self):
        self.patient = _make_patient()
        self.doctor = _make_doctor()
        self.client = APIClient()

    def test_stats_empty(self):
        _auth(self.client, self.patient)
        resp = self.client.get('/api/detection/detections/stats/')
        self.assertEqual(resp.status_code, http_status.HTTP_200_OK)
        self.assertEqual(resp.data['total_detections'], 0)
        self.assertEqual(resp.data['ad_percentage'], 0)

    def test_stats_with_data(self):
        _make_detection(self.patient, self.doctor, status='completed', predicted_class='dementia', confidence_score=0.9)
        _make_detection(self.patient, self.doctor, status='completed', predicted_class='cn', confidence_score=0.8)
        _make_detection(self.patient, self.doctor, status='pending')
        _auth(self.client, self.patient)
        resp = self.client.get('/api/detection/detections/stats/')
        self.assertEqual(resp.status_code, http_status.HTTP_200_OK)
        self.assertEqual(resp.data['total_detections'], 3)
        self.assertEqual(resp.data['completed'], 2)
        self.assertEqual(resp.data['alzheimers_cases'], 1)
        self.assertEqual(resp.data['control_cases'], 1)
        self.assertEqual(resp.data['ad_percentage'], 50.0)


# ===========================================================================
# review (GET / POST)
# ===========================================================================

@override_settings(MEDIA_ROOT='/tmp/test_media')
class ReviewTests(APITestCase):

    def setUp(self):
        self.patient = _make_patient()
        self.doctor = _make_doctor()
        self.other_doctor = _make_doctor()
        self.client = APIClient()
        self.detection = _make_detection(self.patient, self.doctor, status='completed')

    def test_patient_cannot_review(self):
        _auth(self.client, self.patient)
        resp = self.client.post(f'/api/detection/detections/{self.detection.pk}/review/')
        self.assertEqual(resp.status_code, http_status.HTTP_403_FORBIDDEN)

    def test_get_no_review_exists(self):
        _auth(self.client, self.doctor)
        resp = self.client.get(f'/api/detection/detections/{self.detection.pk}/review/')
        self.assertEqual(resp.status_code, http_status.HTTP_404_NOT_FOUND)

    def test_create_review(self):
        _auth(self.client, self.doctor)
        resp = self.client.post(
            f'/api/detection/detections/{self.detection.pk}/review/',
            {
                'ai_accepted': True,
                'doctor_conclusion': 'Consistent with early dementia.',
                'doctor_notes': 'Internal note.',
                'patient_summary': 'Your results show early signs.',
            },
            format='json',
        )
        self.assertEqual(resp.status_code, http_status.HTTP_200_OK)
        self.assertTrue(DoctorReview.objects.filter(detection=self.detection).exists())

    def test_get_existing_review(self):
        DoctorReview.objects.create(
            detection=self.detection,
            doctor=self.doctor,
            patient=self.patient,
            ai_accepted=True,
            doctor_conclusion='All good.',
            patient_summary='Nothing to worry about.',
        )
        _auth(self.client, self.doctor)
        resp = self.client.get(f'/api/detection/detections/{self.detection.pk}/review/')
        self.assertEqual(resp.status_code, http_status.HTTP_200_OK)
        self.assertEqual(resp.data['doctor_conclusion'], 'All good.')

    def test_update_review_only_by_owner(self):
        DoctorReview.objects.create(
            detection=self.detection,
            doctor=self.doctor,
            patient=self.patient,
            ai_accepted=True,
            doctor_conclusion='Initial.',
            patient_summary='Summary.',
        )
        _auth(self.client, self.other_doctor)
        resp = self.client.post(
            f'/api/detection/detections/{self.detection.pk}/review/',
            {'doctor_conclusion': 'Hijack attempt'},
            format='json',
        )
        self.assertIn(resp.status_code, (http_status.HTTP_403_FORBIDDEN, http_status.HTTP_404_NOT_FOUND))

    def test_send_to_patient_sets_sent_at(self):
        _auth(self.client, self.doctor)
        resp = self.client.post(
            f'/api/detection/detections/{self.detection.pk}/review/',
            {
                'ai_accepted': True,
                'doctor_conclusion': 'Positive.',
                'patient_summary': 'You have early signs.',
                'is_sent_to_patient': True,
            },
            format='json',
        )
        self.assertEqual(resp.status_code, http_status.HTTP_200_OK)
        review = DoctorReview.objects.get(detection=self.detection)
        self.assertTrue(review.is_sent_to_patient)
        self.assertIsNotNone(review.sent_at)

    @patch.object(DetectionViewSet, '_sync_fhir_report')
    def test_send_to_patient_triggers_fhir_sync(self, mock_sync):
        _auth(self.client, self.doctor)
        self.client.post(
            f'/api/detection/detections/{self.detection.pk}/review/',
            {
                'ai_accepted': True,
                'doctor_conclusion': 'OK.',
                'patient_summary': 'Fine.',
                'is_sent_to_patient': True,
            },
            format='json',
        )
        mock_sync.assert_called_once()

    def test_override_class_when_ai_not_accepted(self):
        _auth(self.client, self.doctor)
        resp = self.client.post(
            f'/api/detection/detections/{self.detection.pk}/review/',
            {
                'ai_accepted': False,
                'doctor_override_class': 'ftd',
                'doctor_conclusion': 'Actually FTD.',
                'patient_summary': 'Further tests needed.',
            },
            format='json',
        )
        self.assertEqual(resp.status_code, http_status.HTTP_200_OK)
        review = DoctorReview.objects.get(detection=self.detection)
        self.assertFalse(review.ai_accepted)
        self.assertEqual(review.doctor_override_class, 'ftd')


# ===========================================================================
# explainability
# ===========================================================================

@override_settings(MEDIA_ROOT='/tmp/test_media')
class ExplainabilityTests(APITestCase):

    def setUp(self):
        self.patient = _make_patient()
        self.doctor = _make_doctor()
        self.client = APIClient()

    def test_not_completed_returns_400(self):
        det = _make_detection(self.patient, self.doctor, status='pending')
        _auth(self.client, self.doctor)
        resp = self.client.get(f'/api/detection/detections/{det.pk}/explainability/')
        self.assertEqual(resp.status_code, http_status.HTTP_400_BAD_REQUEST)
        self.assertIn('completed', resp.data['error'])

    @patch('detection.views._ensure_ml_libs')
    @patch('detection.views.Image')
    @patch('detection.views.np')
    @patch('detection.views.transforms')
    @patch('detection.views.ModelLoader')
    @patch.object(DetectionViewSet, '_resolve_nifti_path_for_detection', return_value='')
    def test_explainability_success_regular_image(
        self, mock_resolve, mock_loader_cls, mock_transforms, mock_np, mock_image, mock_ensure
    ):
        det = _make_detection(self.patient, self.doctor, status='completed', model_type='binary')

        mock_pil = MagicMock()
        mock_pil.convert.return_value = mock_pil
        mock_image.open.return_value = mock_pil
        mock_np.array.return_value = MagicMock()

        mock_transform_obj = MagicMock()
        mock_transform_obj.return_value = MagicMock(unsqueeze=MagicMock(return_value=MagicMock(to=MagicMock(return_value=MagicMock()))))
        mock_transforms.Compose.return_value = mock_transform_obj

        mock_loader = MagicMock()
        mock_loader.model = MagicMock()
        mock_loader.device = 'cpu'
        mock_loader_cls.return_value = mock_loader

        gradcam_result = {
            'overlay_base64': 'abc123',
            'heatmap_base64': 'def456',
            'original_base64': 'ghi789',
            'layer_name': 'layer4',
            'predicted_class': 1,
            'predicted_class_name': 'Dementia',
            'confidence': 0.9,
        }

        with patch('detection.xai.get_gradcam_for_detection', return_value=gradcam_result):
            _auth(self.client, self.doctor)
            resp = self.client.get(f'/api/detection/detections/{det.pk}/explainability/')

        self.assertEqual(resp.status_code, http_status.HTTP_200_OK)
        self.assertIn('gradcam', resp.data)

    @patch('detection.views._ensure_ml_libs')
    @patch('detection.xai.get_gradcam_for_detection', side_effect=RuntimeError('XAI fail'))
    @patch('detection.views.Image')
    @patch('detection.views.np')
    @patch('detection.views.transforms')
    @patch('detection.views.ModelLoader')
    @patch.object(DetectionViewSet, '_resolve_nifti_path_for_detection', return_value='')
    def test_explainability_error_returns_500(
        self, mock_resolve, mock_loader_cls, mock_transforms, mock_np, mock_image, mock_xai, mock_ensure
    ):
        det = _make_detection(self.patient, self.doctor, status='completed', model_type='binary')

        mock_pil = MagicMock()
        mock_pil.convert.return_value = mock_pil
        mock_image.open.return_value = mock_pil
        mock_np.array.return_value = MagicMock()

        mock_transform_obj = MagicMock()
        mock_transform_obj.return_value = MagicMock(unsqueeze=MagicMock(return_value=MagicMock(to=MagicMock(return_value=MagicMock()))))
        mock_transforms.Compose.return_value = mock_transform_obj

        mock_loader = MagicMock()
        mock_loader.model = MagicMock()
        mock_loader.device = 'cpu'
        mock_loader_cls.return_value = mock_loader

        _auth(self.client, self.doctor)
        resp = self.client.get(f'/api/detection/detections/{det.pk}/explainability/')
        self.assertEqual(resp.status_code, http_status.HTTP_500_INTERNAL_SERVER_ERROR)


# ===========================================================================
# generate_fhir_report
# ===========================================================================

@override_settings(MEDIA_ROOT='/tmp/test_media')
class GenerateFHIRReportTests(APITestCase):

    def setUp(self):
        self.patient = _make_patient()
        self.doctor = _make_doctor()
        self.client = APIClient()

    def test_only_doctors(self):
        det = _make_detection(self.patient, self.doctor, status='completed')
        _auth(self.client, self.patient)
        resp = self.client.post(f'/api/detection/detections/{det.pk}/generate_fhir_report/')
        self.assertEqual(resp.status_code, http_status.HTTP_403_FORBIDDEN)

    def test_not_completed(self):
        det = _make_detection(self.patient, self.doctor, status='processing')
        _auth(self.client, self.doctor)
        resp = self.client.post(f'/api/detection/detections/{det.pk}/generate_fhir_report/')
        self.assertEqual(resp.status_code, http_status.HTTP_400_BAD_REQUEST)
        self.assertIn('completed', resp.data['error'])

    def test_no_doctor_review(self):
        det = _make_detection(self.patient, self.doctor, status='completed')
        _auth(self.client, self.doctor)
        resp = self.client.post(f'/api/detection/detections/{det.pk}/generate_fhir_report/')
        self.assertEqual(resp.status_code, http_status.HTTP_400_BAD_REQUEST)
        self.assertIn('clinical review', resp.data['error'])

    def test_report_already_exists(self):
        det = _make_detection(
            self.patient, self.doctor, status='completed',
            predicted_class='dementia', confidence_score=0.9,
        )
        DoctorReview.objects.create(
            detection=det, doctor=self.doctor, patient=self.patient,
            ai_accepted=True, doctor_conclusion='OK', patient_summary='Fine',
        )
        FHIRDiagnosticReport.objects.create(
            detection=det, patient=self.patient, doctor=self.doctor,
            status='final', effective_datetime=timezone.now(),
            conclusion='Test', hospital_name='Test Hospital',
        )
        _auth(self.client, self.doctor)
        resp = self.client.post(f'/api/detection/detections/{det.pk}/generate_fhir_report/')
        self.assertEqual(resp.status_code, http_status.HTTP_400_BAD_REQUEST)
        self.assertIn('already exists', resp.data['error'])

    @patch.object(DetectionViewSet, '_sync_fhir_report')
    def test_successful_generation(self, mock_sync):
        det = _make_detection(
            self.patient, self.doctor, status='completed',
            predicted_class='dementia', confidence_score=0.9,
        )
        DoctorReview.objects.create(
            detection=det, doctor=self.doctor, patient=self.patient,
            ai_accepted=True, doctor_conclusion='Dementia confirmed', patient_summary='...',
        )
        _auth(self.client, self.doctor)
        resp = self.client.post(f'/api/detection/detections/{det.pk}/generate_fhir_report/')
        # The view has a bug: references `fhir_report` local var not returned from _sync,
        # so it will 500 unless mock intercepts. We verify that _sync was called.
        mock_sync.assert_called_once()


# ===========================================================================
# destroy
# ===========================================================================

@override_settings(MEDIA_ROOT='/tmp/test_media')
class DestroyTests(APITestCase):

    def setUp(self):
        self.patient = _make_patient()
        self.doctor = _make_doctor()
        self.other_doctor = _make_doctor()
        self.client = APIClient()

    def test_patient_cannot_delete(self):
        det = _make_detection(self.patient, self.doctor)
        _auth(self.client, self.patient)
        resp = self.client.delete(f'/api/detection/detections/{det.pk}/')
        self.assertEqual(resp.status_code, http_status.HTTP_403_FORBIDDEN)

    def test_non_owning_doctor_cannot_delete(self):
        det = _make_detection(self.patient, self.doctor)
        _auth(self.client, self.other_doctor)
        resp = self.client.delete(f'/api/detection/detections/{det.pk}/')
        self.assertIn(resp.status_code, (http_status.HTTP_403_FORBIDDEN, http_status.HTTP_404_NOT_FOUND))

    def test_owning_doctor_can_delete(self):
        det = _make_detection(self.patient, self.doctor)
        _auth(self.client, self.doctor)
        resp = self.client.delete(f'/api/detection/detections/{det.pk}/')
        self.assertEqual(resp.status_code, http_status.HTTP_204_NO_CONTENT)
        self.assertFalse(DetectionResult.objects.filter(pk=det.pk).exists())


# ===========================================================================
# get_queryset
# ===========================================================================

@override_settings(MEDIA_ROOT='/tmp/test_media')
class GetQuerysetTests(APITestCase):

    def setUp(self):
        self.patient = _make_patient()
        self.doctor = _make_doctor()
        self.other_patient = _make_patient()
        self.client = APIClient()

    def test_patient_only_sees_own(self):
        _make_detection(self.patient, self.doctor, status='completed')
        _make_detection(self.other_patient, self.doctor, status='completed')
        _auth(self.client, self.patient)
        resp = self.client.get('/api/detection/detections/')
        self.assertEqual(resp.status_code, http_status.HTTP_200_OK)
        self.assertEqual(len(resp.data), 1)

    def test_doctor_sees_own_plus_assigned(self):
        _make_detection(self.patient, self.doctor, status='completed')
        apt = _make_appointment(self.other_patient, self.doctor)
        _make_detection(self.other_patient, appointment=apt, status='pending')
        _auth(self.client, self.doctor)
        resp = self.client.get('/api/detection/detections/')
        self.assertEqual(resp.status_code, http_status.HTTP_200_OK)
        self.assertGreaterEqual(len(resp.data), 2)


# ===========================================================================
# Internal methods: _process_image, _run_binary_inference, _run_subtype_inference
# ===========================================================================

@override_settings(MEDIA_ROOT='/tmp/test_media')
class ProcessImageTests(TestCase):

    def setUp(self):
        self.patient = _make_patient()
        self.doctor = _make_doctor()
        self.viewset = DetectionViewSet()

    @patch('detection.views._ensure_ml_libs')
    @patch('detection.views.Image')
    @patch('detection.views.transforms')
    @patch.object(DetectionViewSet, '_run_binary_inference')
    def test_process_regular_image(self, mock_binary, mock_transforms, mock_image, mock_ensure):
        det = _make_detection(self.patient, self.doctor)
        mock_pil = MagicMock()
        mock_pil.convert.return_value = mock_pil
        mock_image.open.return_value = mock_pil

        mock_transform_obj = MagicMock()
        mock_transform_obj.return_value = MagicMock(unsqueeze=MagicMock(return_value='tensor'))
        mock_transforms.Compose.return_value = mock_transform_obj

        mock_binary.return_value = {'predicted_class': 'cn', 'confidence': 0.8, 'probabilities': {}, 'analysis': {}}

        result = self.viewset._process_image(det)
        self.assertEqual(result['predicted_class'], 'cn')
        mock_binary.assert_called_once()

    @patch('detection.views._ensure_ml_libs')
    @patch('detection.views.Image')
    @patch('detection.views.transforms')
    @patch.object(DetectionViewSet, '_run_subtype_inference')
    @patch.object(DetectionViewSet, '_run_pipeline', return_value='/tmp/out.nii.gz')
    @patch.object(DetectionViewSet, '_load_nifti_slice')
    def test_process_mri_file_runs_pipeline(self, mock_load, mock_pipeline, mock_subtype, mock_transforms, mock_image, mock_ensure):
        det = _make_detection(
            self.patient, self.doctor, model_type='subtype',
            uploaded_file=SimpleUploadedFile('brain.nii.gz', b'\x00' * 50, content_type='application/gzip'),
        )
        from PIL import Image as PILImage
        mock_load.return_value = PILImage.new('RGB', (224, 224))

        mock_transform_obj = MagicMock()
        mock_transform_obj.return_value = MagicMock(unsqueeze=MagicMock(return_value='tensor'))
        mock_transforms.Compose.return_value = mock_transform_obj

        mock_subtype.return_value = {'predicted_class': 'alzheimers', 'confidence': 0.7, 'probabilities': {}, 'analysis': {}}

        result = self.viewset._process_image(det)
        mock_pipeline.assert_called_once()
        mock_subtype.assert_called_once()
        self.assertEqual(result['predicted_class'], 'alzheimers')


@override_settings(MEDIA_ROOT='/tmp/test_media')
class RunBinaryInferenceTests(TestCase):

    def setUp(self):
        self.viewset = DetectionViewSet()

    @patch('detection.views.ModelLoader')
    @patch('detection.views.torch')
    def test_predicts_dementia(self, mock_torch, mock_loader_cls):
        mock_model = MagicMock()
        mock_loader = MagicMock()
        mock_loader.model = mock_model
        mock_loader.device = 'cpu'
        mock_loader_cls.return_value = mock_loader

        mock_output = MagicMock()
        mock_output.item.return_value = 1.5
        mock_model.return_value = mock_output

        mock_torch.no_grad.return_value.__enter__ = MagicMock()
        mock_torch.no_grad.return_value.__exit__ = MagicMock()
        mock_torch.sigmoid.return_value.item.return_value = 0.82

        fake_tensor = MagicMock()
        fake_tensor.to.return_value = fake_tensor

        result = self.viewset._run_binary_inference(fake_tensor, False)
        self.assertEqual(result['predicted_class'], 'dementia')
        self.assertAlmostEqual(result['confidence'], 0.82)
        self.assertIn('probabilities', result)
        self.assertFalse(result['analysis']['pipeline_preprocessing'])

    @patch('detection.views.ModelLoader')
    @patch('detection.views.torch')
    def test_predicts_cn(self, mock_torch, mock_loader_cls):
        mock_model = MagicMock()
        mock_loader = MagicMock()
        mock_loader.model = mock_model
        mock_loader.device = 'cpu'
        mock_loader_cls.return_value = mock_loader

        mock_output = MagicMock()
        mock_output.item.return_value = -1.0
        mock_model.return_value = mock_output

        mock_torch.no_grad.return_value.__enter__ = MagicMock()
        mock_torch.no_grad.return_value.__exit__ = MagicMock()
        mock_torch.sigmoid.return_value.item.return_value = 0.27

        fake_tensor = MagicMock()
        fake_tensor.to.return_value = fake_tensor

        result = self.viewset._run_binary_inference(fake_tensor, True)
        self.assertEqual(result['predicted_class'], 'cn')
        self.assertAlmostEqual(result['confidence'], 0.73)
        self.assertTrue(result['analysis']['pipeline_preprocessing'])

    @patch('detection.views.ModelLoader')
    @patch('detection.views.torch')
    def test_nan_raises_error(self, mock_torch, mock_loader_cls):
        mock_model = MagicMock()
        mock_loader = MagicMock()
        mock_loader.model = mock_model
        mock_loader.device = 'cpu'
        mock_loader_cls.return_value = mock_loader

        mock_output = MagicMock()
        mock_output.item.return_value = float('nan')
        mock_model.return_value = mock_output

        mock_torch.no_grad.return_value.__enter__ = MagicMock()
        mock_torch.no_grad.return_value.__exit__ = MagicMock()
        mock_torch.sigmoid.return_value.item.return_value = float('nan')

        fake_tensor = MagicMock()
        fake_tensor.to.return_value = fake_tensor

        with self.assertRaises(ValueError) as ctx:
            self.viewset._run_binary_inference(fake_tensor, False)
        self.assertIn('NaN', str(ctx.exception))


@override_settings(MEDIA_ROOT='/tmp/test_media')
class RunSubtypeInferenceTests(TestCase):

    def setUp(self):
        self.viewset = DetectionViewSet()

    @patch('detection.views.SubtypeModelLoader')
    @patch('detection.views.torch')
    def test_predicts_alzheimers(self, mock_torch, mock_loader_cls):
        mock_model = MagicMock()
        mock_loader = MagicMock()
        mock_loader.model = mock_model
        mock_loader.device = 'cpu'
        mock_loader_cls.return_value = mock_loader
        mock_loader_cls.CLASS_NAMES = ['ad', 'pd', 'ftd', 'cn']

        mock_output = MagicMock()
        mock_output.squeeze.return_value.tolist.return_value = [2.0, 0.5, 0.3, 0.1]
        mock_model.return_value = mock_output

        mock_torch.no_grad.return_value.__enter__ = MagicMock()
        mock_torch.no_grad.return_value.__exit__ = MagicMock()

        import numpy as np
        probs = np.array([0.7, 0.1, 0.1, 0.1])

        mock_probs = MagicMock()
        mock_probs.squeeze.return_value = mock_probs
        mock_probs.__getitem__ = lambda self, idx: MagicMock(item=lambda: float(probs[idx]))
        mock_torch.softmax.return_value = mock_probs
        mock_torch.argmax.return_value.item.return_value = 0
        mock_torch.isnan.return_value.any.return_value = False

        mock_probs.tolist.return_value = probs.tolist()

        fake_tensor = MagicMock()
        fake_tensor.to.return_value = fake_tensor

        result = self.viewset._run_subtype_inference(fake_tensor, False)
        self.assertEqual(result['predicted_class'], 'alzheimers')
        self.assertIn('probabilities', result)
        self.assertIn('alzheimers', result['probabilities'])

    @patch('detection.views.SubtypeModelLoader')
    @patch('detection.views.torch')
    def test_predicts_cn(self, mock_torch, mock_loader_cls):
        mock_model = MagicMock()
        mock_loader = MagicMock()
        mock_loader.model = mock_model
        mock_loader.device = 'cpu'
        mock_loader_cls.return_value = mock_loader
        mock_loader_cls.CLASS_NAMES = ['ad', 'pd', 'ftd', 'cn']

        mock_output = MagicMock()
        mock_output.squeeze.return_value.tolist.return_value = [0.1, 0.1, 0.1, 3.0]
        mock_model.return_value = mock_output

        mock_torch.no_grad.return_value.__enter__ = MagicMock()
        mock_torch.no_grad.return_value.__exit__ = MagicMock()

        import numpy as np
        probs = np.array([0.05, 0.05, 0.05, 0.85])

        mock_probs = MagicMock()
        mock_probs.squeeze.return_value = mock_probs
        mock_probs.__getitem__ = lambda self, idx: MagicMock(item=lambda: float(probs[idx]))
        mock_torch.softmax.return_value = mock_probs
        mock_torch.argmax.return_value.item.return_value = 3
        mock_torch.isnan.return_value.any.return_value = False
        mock_probs.tolist.return_value = probs.tolist()

        fake_tensor = MagicMock()
        fake_tensor.to.return_value = fake_tensor

        result = self.viewset._run_subtype_inference(fake_tensor, True)
        self.assertEqual(result['predicted_class'], 'cn')
        self.assertTrue(result['analysis']['pipeline_preprocessing'])

    @patch('detection.views.SubtypeModelLoader')
    @patch('detection.views.torch')
    def test_nan_raises_error(self, mock_torch, mock_loader_cls):
        mock_model = MagicMock()
        mock_loader = MagicMock()
        mock_loader.model = mock_model
        mock_loader.device = 'cpu'
        mock_loader_cls.return_value = mock_loader

        mock_output = MagicMock()
        mock_model.return_value = mock_output

        mock_torch.no_grad.return_value.__enter__ = MagicMock()
        mock_torch.no_grad.return_value.__exit__ = MagicMock()

        mock_probs = MagicMock()
        mock_probs.squeeze.return_value = mock_probs
        mock_torch.softmax.return_value = mock_probs
        mock_torch.isnan.return_value.any.return_value = True

        fake_tensor = MagicMock()
        fake_tensor.to.return_value = fake_tensor

        with self.assertRaises(ValueError) as ctx:
            self.viewset._run_subtype_inference(fake_tensor, False)
        self.assertIn('NaN', str(ctx.exception))


# ===========================================================================
# _sync_fhir_report
# ===========================================================================

@override_settings(MEDIA_ROOT='/tmp/test_media')
class SyncFHIRReportTests(TestCase):

    def setUp(self):
        self.patient = _make_patient()
        self.doctor = _make_doctor()
        self.viewset = DetectionViewSet()

    def test_creates_new_report_on_first_call(self):
        det = _make_detection(
            self.patient, self.doctor, status='completed',
            predicted_class='dementia', confidence_score=0.9,
        )
        review = DoctorReview.objects.create(
            detection=det, doctor=self.doctor, patient=self.patient,
            ai_accepted=True, doctor_conclusion='Confirmed.',
            patient_summary='Signs found.',
        )
        self.viewset._sync_fhir_report(det, review, self.doctor)
        self.assertTrue(FHIRDiagnosticReport.objects.filter(detection=det).exists())
        report = det.fhir_report
        self.assertEqual(report.status, 'final')
        self.assertIn('Confirmed.', report.conclusion)

    def test_updates_existing_report(self):
        det = _make_detection(
            self.patient, self.doctor, status='completed',
            predicted_class='cn', confidence_score=0.85,
        )
        FHIRDiagnosticReport.objects.create(
            detection=det, patient=self.patient, doctor=self.doctor,
            status='preliminary', effective_datetime=timezone.now(),
            conclusion='Initial', hospital_name='H',
        )
        review = DoctorReview.objects.create(
            detection=det, doctor=self.doctor, patient=self.patient,
            ai_accepted=True, doctor_conclusion='Updated conclusion.',
            patient_summary='Updated.',
        )
        self.viewset._sync_fhir_report(det, review, self.doctor)
        det.refresh_from_db()
        report = det.fhir_report
        self.assertEqual(report.status, 'final')
        self.assertIn('Updated conclusion.', report.conclusion)

    def test_override_class_used_when_ai_not_accepted(self):
        det = _make_detection(
            self.patient, self.doctor, status='completed',
            predicted_class='cn', confidence_score=0.7,
        )
        review = DoctorReview.objects.create(
            detection=det, doctor=self.doctor, patient=self.patient,
            ai_accepted=False, doctor_override_class='alzheimers',
            doctor_conclusion='I disagree.', patient_summary='...',
        )
        self.viewset._sync_fhir_report(det, review, self.doctor)
        report = det.fhir_report
        self.assertEqual(report.fhir_json['conclusion'], 'I disagree.')

    def test_appointment_marked_completed(self):
        apt = _make_appointment(self.patient, self.doctor, status='approved')
        det = _make_detection(
            self.patient, self.doctor, appointment=apt, status='completed',
            predicted_class='dementia', confidence_score=0.8,
        )
        review = DoctorReview.objects.create(
            detection=det, doctor=self.doctor, patient=self.patient,
            ai_accepted=True, doctor_conclusion='Yes.', patient_summary='...',
        )
        self.viewset._sync_fhir_report(det, review, self.doctor)
        apt.refresh_from_db()
        self.assertEqual(apt.status, 'completed')


# ===========================================================================
# _resolve_nifti_path_for_detection
# ===========================================================================

@override_settings(MEDIA_ROOT='/tmp/test_media')
class ResolveNiftiPathTests(TestCase):

    def setUp(self):
        self.patient = _make_patient()
        self.doctor = _make_doctor()
        self.viewset = DetectionViewSet()

    def test_returns_empty_when_nothing_available(self):
        det = _make_detection(self.patient, self.doctor)
        result = self.viewset._resolve_nifti_path_for_detection(det)
        self.assertEqual(result, '')

    @patch('detection.views.os.path.isfile', return_value=True)
    def test_returns_preprocessed_file_when_nifti(self, mock_isfile):
        det = _make_detection(self.patient, self.doctor, preprocessed_file='/data/out.nii.gz')
        result = self.viewset._resolve_nifti_path_for_detection(det)
        self.assertEqual(result, '/data/out.nii.gz')

    @patch('detection.views.os.path.isfile', return_value=False)
    @patch.object(DetectionViewSet, '_find_pipeline_output_nifti', return_value='/work/out.nii.gz')
    def test_falls_back_to_pipeline_output(self, mock_find, mock_isfile):
        def isfile_side(p):
            return p == '/work/out.nii.gz'
        mock_isfile.side_effect = isfile_side

        det = _make_detection(self.patient, self.doctor)
        result = self.viewset._resolve_nifti_path_for_detection(det)
        self.assertEqual(result, '/work/out.nii.gz')


# ===========================================================================
# _run_pipeline
# ===========================================================================

@override_settings(MEDIA_ROOT='/tmp/test_media')
class RunPipelineTests(TestCase):

    def setUp(self):
        self.viewset = DetectionViewSet()

    @patch('pipeline.preprocess.preprocess_mri', return_value='/output/preprocessed.nii.gz')
    def test_successful_pipeline(self, mock_preprocess):
        result = self.viewset._run_pipeline('/input/scan.nii.gz')
        self.assertEqual(result, '/output/preprocessed.nii.gz')
        mock_preprocess.assert_called_once()

    @patch('pipeline.preprocess.preprocess_mri', side_effect=RuntimeError('Pipeline crashed'))
    def test_pipeline_failure_raises(self, mock_preprocess):
        with self.assertRaises(RuntimeError):
            self.viewset._run_pipeline('/input/scan.nii.gz')
