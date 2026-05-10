"""
API Integration tests for detection endpoints
"""
import io
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

    def setUp(self):
        self.client = APIClient()

        import uuid
        uid = uuid.uuid4().hex[:8]
        self.patient1 = User.objects.create_user(
            email=f'patient1_{uid}@test.com', password='testpass123',
            first_name='Patient', last_name='One', role='patient'
        )
        self.patient2 = User.objects.create_user(
            email=f'patient2_{uid}@test.com', password='testpass123',
            first_name='Patient', last_name='Two', role='patient'
        )
        self.doctor = User.objects.create_user(
            email=f'doctor_{uid}@test.com', password='testpass123',
            first_name='Dr', last_name='Test', role='doctor'
        )

        self.token1 = str(AccessToken.for_user(self.patient1))
        self.token2 = str(AccessToken.for_user(self.patient2))
        self.doc_token = str(AccessToken.for_user(self.doctor))

        self.detection1 = DetectionResult.objects.create(
            patient=self.patient1, doctor=self.doctor,
            uploaded_file=SimpleUploadedFile('t1.jpg', b'c1', 'image/jpeg'),
            file_size=1024, status='completed',
            predicted_class='alzheimers', confidence_score=0.88
        )
        self.detection2 = DetectionResult.objects.create(
            patient=self.patient1,
            uploaded_file=SimpleUploadedFile('t2.jpg', b'c2', 'image/jpeg'),
            file_size=2048, status='pending'
        )
        self.detection_p2 = DetectionResult.objects.create(
            patient=self.patient2,
            uploaded_file=SimpleUploadedFile('t3.jpg', b'c3', 'image/jpeg'),
            file_size=1536, status='completed',
            predicted_class='cn', confidence_score=0.92
        )

    def _make_image(self):
        img = Image.new('RGB', (224, 224), color='gray')
        buf = io.BytesIO()
        img.save(buf, format='JPEG')
        buf.seek(0)
        return SimpleUploadedFile('scan.jpg', buf.read(), content_type='image/jpeg')

    def test_list_detections_authenticated(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token1}')
        url = reverse('detection-list')
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.data), 2)

    def test_list_detections_unauthenticated(self):
        resp = self.client.get(reverse('detection-list'))
        self.assertEqual(resp.status_code, 401)

    def test_list_detections_isolation(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token1}')
        resp = self.client.get(reverse('detection-list'))
        self.assertEqual(len(resp.data), 2)

        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token2}')
        resp = self.client.get(reverse('detection-list'))
        self.assertEqual(len(resp.data), 1)

    def test_retrieve_detection_detail(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token1}')
        url = reverse('detection-detail', args=[self.detection1.id])
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data['confidence_score'], 0.88)

    def test_retrieve_detection_unauthorized_user(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token2}')
        url = reverse('detection-detail', args=[self.detection1.id])
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 404)

    def test_upload_missing_file(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token1}')
        url = reverse('detection-upload-and-detect')
        resp = self.client.post(url, {'patient_age': 65}, format='multipart')
        self.assertEqual(resp.status_code, 400)

    def test_upload_invalid_file_type(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token1}')
        url = reverse('detection-upload-and-detect')
        bad = SimpleUploadedFile('doc.txt', b'text', content_type='text/plain')
        resp = self.client.post(url, {'uploaded_file': bad}, format='multipart')
        self.assertEqual(resp.status_code, 400)

    def test_upload_unauthenticated(self):
        url = reverse('detection-upload-and-detect')
        resp = self.client.post(url, {'uploaded_file': self._make_image()}, format='multipart')
        self.assertEqual(resp.status_code, 401)

    def test_history_endpoint(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token1}')
        resp = self.client.get(reverse('detection-history'))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.data), 2)

    def test_stats_endpoint(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token1}')
        resp = self.client.get(reverse('detection-stats'))
        self.assertEqual(resp.status_code, 200)
        self.assertIn('total_detections', resp.data)
        self.assertIn('completed', resp.data)
        self.assertIn('alzheimers_cases', resp.data)
        self.assertEqual(resp.data['total_detections'], 2)
        self.assertEqual(resp.data['completed'], 1)

    def test_delete_requires_doctor(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token1}')
        url = reverse('detection-detail', args=[self.detection2.id])
        resp = self.client.delete(url)
        self.assertEqual(resp.status_code, 403)

    def test_doctor_deletes_own_detection(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.doc_token}')
        url = reverse('detection-detail', args=[self.detection1.id])
        resp = self.client.delete(url)
        self.assertEqual(resp.status_code, 204)
        self.assertFalse(DetectionResult.objects.filter(id=self.detection1.id).exists())

    def test_my_uploads_doctor_only(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token1}')
        resp = self.client.get(reverse('detection-my-uploads'))
        self.assertEqual(resp.status_code, 403)

    def test_my_uploads_doctor(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.doc_token}')
        resp = self.client.get(reverse('detection-my-uploads'))
        self.assertEqual(resp.status_code, 200)


class ModelMetadataAPITests(APITestCase):

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            email='mm@test.com', password='testpass123'
        )
        self.token = str(AccessToken.for_user(self.user))

        self.active_model = ModelMetadata.objects.create(
            name='Active Model', version='1.0', architecture='ResNet-34',
            accuracy=0.92, auc_score=0.94, sensitivity=0.90, specificity=0.92,
            trained_on=datetime(2024, 1, 1).date(), is_active=True,
            model_path='models/active.pth'
        )
        ModelMetadata.objects.create(
            name='Inactive Model', version='0.9', architecture='ResNet-18',
            accuracy=0.85, auc_score=0.87, sensitivity=0.83, specificity=0.86,
            trained_on=datetime(2023, 6, 1).date(), is_active=False,
            model_path='models/inactive.pth'
        )

    def test_list_active_only(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token}')
        resp = self.client.get(reverse('model-metadata-list'))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.data), 1)
        self.assertEqual(resp.data[0]['name'], 'Active Model')

    def test_unauthenticated(self):
        resp = self.client.get(reverse('model-metadata-list'))
        self.assertEqual(resp.status_code, 401)

    def test_retrieve_detail(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token}')
        resp = self.client.get(reverse('model-metadata-detail', args=[self.active_model.id]))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data['accuracy'], 0.92)

    def test_read_only(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token}')
        resp = self.client.post(reverse('model-metadata-list'), {'name': 'X'}, format='json')
        self.assertEqual(resp.status_code, 405)
        resp = self.client.put(reverse('model-metadata-detail', args=[self.active_model.id]), {'name': 'X'}, format='json')
        self.assertEqual(resp.status_code, 405)
        resp = self.client.delete(reverse('model-metadata-detail', args=[self.active_model.id]))
        self.assertEqual(resp.status_code, 405)
