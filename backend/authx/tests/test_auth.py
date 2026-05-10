"""
Unit and integration tests for authentication endpoints
"""
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient, APITestCase
from rest_framework_simplejwt.tokens import AccessToken
from authx.models import DoctorProfile

User = get_user_model()


class RegisterViewTests(APITestCase):

    def setUp(self):
        self.client = APIClient()
        self.url = reverse('register')

    def test_register_patient_success(self):
        data = {
            'email': 'newpatient@test.com',
            'password': 'SecurePass123!',
            'first_name': 'New',
            'last_name': 'Patient',
            'role': 'patient',
            'date_of_birth': '1960-05-15',
            'gender': 'M',
        }
        resp = self.client.post(self.url, data, format='json')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertIn('token', resp.data)
        self.assertIn('user', resp.data)
        self.assertEqual(resp.data['user']['email'], 'newpatient@test.com')
        self.assertEqual(resp.data['user']['role'], 'patient')
        self.assertTrue(User.objects.filter(email='newpatient@test.com').exists())

    def test_register_doctor_success(self):
        data = {
            'email': 'newdoc@test.com',
            'password': 'DocPass123!',
            'first_name': 'Dr',
            'last_name': 'Test',
            'role': 'doctor',
            'license_number': 'LIC-REG-001',
            'specialization': 'neurology',
            'qualifications': 'MD, PhD',
            'experience_years': 10,
            'hospital_affiliation': 'General Hospital',
        }
        resp = self.client.post(self.url, data, format='json')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(resp.data['user']['role'], 'doctor')

    def test_register_missing_email(self):
        data = {
            'password': 'SecurePass123!',
            'first_name': 'X', 'last_name': 'Y',
            'role': 'patient', 'date_of_birth': '1990-01-01', 'gender': 'M',
        }
        resp = self.client.post(self.url, data, format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_register_missing_password(self):
        data = {
            'email': 'test@test.com',
            'first_name': 'X', 'last_name': 'Y',
            'role': 'patient', 'date_of_birth': '1990-01-01', 'gender': 'M',
        }
        resp = self.client.post(self.url, data, format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_register_missing_name(self):
        data = {
            'email': 'test@test.com', 'password': 'SecurePass123!',
            'role': 'patient', 'date_of_birth': '1990-01-01', 'gender': 'M',
        }
        resp = self.client.post(self.url, data, format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_register_duplicate_email(self):
        User.objects.create_user(email='existing@test.com', password='pass123')
        data = {
            'email': 'existing@test.com', 'password': 'NewPass123!',
            'first_name': 'X', 'last_name': 'Y',
            'role': 'patient', 'date_of_birth': '1990-01-01', 'gender': 'M',
        }
        resp = self.client.post(self.url, data, format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_register_email_case_insensitive(self):
        data = {
            'email': 'TestUser@TEST.COM', 'password': 'SecurePass123!',
            'first_name': 'Test', 'last_name': 'User',
            'role': 'patient', 'date_of_birth': '1990-01-01', 'gender': 'F',
        }
        resp = self.client.post(self.url, data, format='json')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertTrue(User.objects.filter(email='testuser@test.com').exists())

    def test_register_patient_missing_required_patient_fields(self):
        data = {
            'email': 'miss@test.com', 'password': 'SecurePass123!',
            'first_name': 'X', 'last_name': 'Y',
            'role': 'patient',
        }
        resp = self.client.post(self.url, data, format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)


class LoginViewTests(APITestCase):

    def setUp(self):
        self.client = APIClient()
        self.url = reverse('login_view')
        self.user = User.objects.create_user(
            email='testuser@test.com', password='TestPass123!',
            first_name='Test', last_name='User', role='patient'
        )

    def test_login_success(self):
        resp = self.client.post(self.url, {
            'email': 'testuser@test.com', 'password': 'TestPass123!'
        }, format='json')
        self.assertEqual(resp.status_code, 200)
        self.assertIn('token', resp.data)
        self.assertIn('user', resp.data)
        self.assertEqual(resp.data['user']['email'], 'testuser@test.com')

    def test_login_wrong_password(self):
        resp = self.client.post(self.url, {
            'email': 'testuser@test.com', 'password': 'WrongPass!'
        }, format='json')
        self.assertEqual(resp.status_code, 401)

    def test_login_nonexistent_user(self):
        resp = self.client.post(self.url, {
            'email': 'nope@test.com', 'password': 'SomePass!'
        }, format='json')
        self.assertEqual(resp.status_code, 401)

    def test_login_case_insensitive(self):
        resp = self.client.post(self.url, {
            'email': 'TESTUSER@TEST.COM', 'password': 'TestPass123!'
        }, format='json')
        self.assertEqual(resp.status_code, 200)

    def test_login_missing_email(self):
        resp = self.client.post(self.url, {'password': 'x'}, format='json')
        self.assertEqual(resp.status_code, 400)

    def test_login_missing_password(self):
        resp = self.client.post(self.url, {'email': 'x@t.com'}, format='json')
        self.assertEqual(resp.status_code, 400)

    def test_login_returns_valid_token(self):
        resp = self.client.post(self.url, {
            'email': 'testuser@test.com', 'password': 'TestPass123!'
        }, format='json')
        token = AccessToken(resp.data['token'])
        self.assertEqual(int(token['user_id']), self.user.id)

    def test_login_inactive_user(self):
        self.user.is_active = False
        self.user.save()
        resp = self.client.post(self.url, {
            'email': 'testuser@test.com', 'password': 'TestPass123!'
        }, format='json')
        self.assertEqual(resp.status_code, 401)


class VerifyViewTests(APITestCase):

    def setUp(self):
        self.client = APIClient()
        self.url = reverse('verify')
        self.user = User.objects.create_user(
            email='verify@test.com', password='TestPass123!',
            first_name='Verify', last_name='User', role='patient'
        )
        self.token_str = str(AccessToken.for_user(self.user))

    def test_verify_valid_token(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token_str}')
        resp = self.client.post(self.url, format='json')
        self.assertEqual(resp.status_code, 200)
        self.assertIn('user', resp.data)
        self.assertEqual(resp.data['user']['email'], 'verify@test.com')

    def test_verify_invalid_token(self):
        self.client.credentials(HTTP_AUTHORIZATION='Bearer invalid.token.here')
        resp = self.client.post(self.url, format='json')
        self.assertEqual(resp.status_code, 401)

    def test_verify_missing_token(self):
        resp = self.client.post(self.url, format='json')
        self.assertEqual(resp.status_code, 401)


class ProfileViewTests(APITestCase):

    def setUp(self):
        self.client = APIClient()
        self.url = reverse('get_profile')
        self.user = User.objects.create_user(
            email='profile@test.com', password='TestPass123!',
            first_name='Profile', last_name='User', role='patient'
        )
        self.token_str = str(AccessToken.for_user(self.user))

    def test_get_profile_authenticated(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token_str}')
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data['user']['email'], 'profile@test.com')

    def test_get_profile_unauthenticated(self):
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 401)


class GoogleLoginViewTests(APITestCase):

    def setUp(self):
        self.client = APIClient()
        self.url = reverse('google_login')

    def test_google_login_new_user(self):
        data = {
            'email': 'googleuser@gmail.com',
            'name': 'Google User',
            'google_id': '123456789',
            'role': 'patient'
        }
        resp = self.client.post(self.url, data, format='json')
        self.assertEqual(resp.status_code, 200)
        self.assertIn('token', resp.data)
        self.assertTrue(User.objects.filter(email='googleuser@gmail.com').exists())

    def test_google_login_existing_user(self):
        User.objects.create_user(
            email='existing@gmail.com', first_name='Existing'
        )
        data = {
            'email': 'existing@gmail.com',
            'name': 'Updated',
            'google_id': '987654321',
        }
        resp = self.client.post(self.url, data, format='json')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(User.objects.filter(email='existing@gmail.com').count(), 1)

    def test_google_login_missing_email(self):
        data = {'name': 'X', 'google_id': '123', 'role': 'patient'}
        resp = self.client.post(self.url, data, format='json')
        self.assertEqual(resp.status_code, 400)

    def test_google_login_without_google_id(self):
        data = {'email': 'noid@gmail.com', 'name': 'No Id'}
        resp = self.client.post(self.url, data, format='json')
        self.assertEqual(resp.status_code, 200)

    def test_google_login_default_role(self):
        data = {'email': 'defrole@gmail.com', 'name': 'Def'}
        resp = self.client.post(self.url, data, format='json')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data['user']['role'], 'patient')

    def test_google_login_preserves_existing_name(self):
        User.objects.create_user(
            email='keep@gmail.com', first_name='Original'
        )
        data = {'email': 'keep@gmail.com', 'name': 'New Name'}
        resp = self.client.post(self.url, data, format='json')
        self.assertEqual(resp.status_code, 200)
        user = User.objects.get(email='keep@gmail.com')
        self.assertEqual(user.first_name, 'Original')

    def test_google_login_updates_name_when_missing(self):
        """Covers lines 140-142: existing user with no first_name gets name set."""
        User.objects.create_user(email='nofirst@gmail.com')
        data = {'email': 'nofirst@gmail.com', 'name': 'Jane Doe', 'google_id': 'g1'}
        resp = self.client.post(self.url, data, format='json')
        self.assertEqual(resp.status_code, 200)
        user = User.objects.get(email='nofirst@gmail.com')
        self.assertEqual(user.first_name, 'Jane')
        self.assertEqual(user.last_name, 'Doe')

    def test_google_login_exception_returns_500(self):
        """Covers lines 159-160: exception during google login."""
        from unittest.mock import patch
        with patch('authx.views.User.objects.get_or_create', side_effect=Exception('DB error')):
            data = {'email': 'fail@gmail.com', 'name': 'Fail'}
            resp = self.client.post(self.url, data, format='json')
            self.assertEqual(resp.status_code, 500)
            self.assertIn('Google login failed', resp.data['error'])


class ListDoctorsViewTests(APITestCase):

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            email='ldv@test.com', password='p', role='patient'
        )
        self.doc = User.objects.create_user(
            email='lddoc@test.com', password='p', role='doctor',
            first_name='Dr', last_name='Smith'
        )
        self.token = str(AccessToken.for_user(self.user))

    def test_list_doctors(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token}')
        url = reverse('list_doctors')
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertIsInstance(resp.data, list)

    def test_list_doctors_with_profile(self):
        """Covers lines 184-185: doctor with profile shows specialization etc."""
        DoctorProfile.objects.create(
            user=self.doc, license_number='LIC-PROF1',
            specialization='Neurology', experience_years=10,
        )
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token}')
        resp = self.client.get(reverse('list_doctors'))
        self.assertEqual(resp.status_code, 200)
        doc_data = [d for d in resp.data if d['id'] == self.doc.id][0]
        self.assertEqual(doc_data['specialization'], 'Neurology')
        self.assertEqual(doc_data['experience_years'], 10)

    def test_list_doctors_unauthenticated(self):
        resp = self.client.get(reverse('list_doctors'))
        self.assertEqual(resp.status_code, 401)


class ListPatientsViewTests(APITestCase):

    def setUp(self):
        self.client = APIClient()
        self.patient = User.objects.create_user(
            email='lp_pat@test.com', password='p', role='patient'
        )
        self.doctor = User.objects.create_user(
            email='lp_doc@test.com', password='p', role='doctor'
        )
        self.pat_token = str(AccessToken.for_user(self.patient))
        self.doc_token = str(AccessToken.for_user(self.doctor))

    def test_doctor_lists_patients(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.doc_token}')
        resp = self.client.get(reverse('list_patients'))
        self.assertEqual(resp.status_code, 200)
        self.assertIsInstance(resp.data, list)

    def test_patient_cannot_list_patients(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.pat_token}')
        resp = self.client.get(reverse('list_patients'))
        self.assertEqual(resp.status_code, 403)


class TokenUtilityTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            email='token@test.com', first_name='Token', last_name='User',
            role='patient'
        )

    def test_issue_token_creates_valid_token(self):
        from authx.views import issue_token
        token_str = issue_token(self.user)
        token = AccessToken(token_str)
        self.assertEqual(int(token['user_id']), self.user.id)
        self.assertEqual(token['role'], 'patient')
        self.assertEqual(token['name'], 'Token User')

    def test_make_user_payload(self):
        from authx.views import make_user_payload
        payload = make_user_payload(self.user)
        self.assertEqual(payload['id'], str(self.user.id))
        self.assertEqual(payload['email'], 'token@test.com')
        self.assertEqual(payload['name'], 'Token User')
        self.assertEqual(payload['role'], 'patient')

    def test_make_user_payload_empty_name(self):
        user = User.objects.create_user(email='noname@test.com')
        from authx.views import make_user_payload
        payload = make_user_payload(user)
        self.assertEqual(payload['name'], '')
