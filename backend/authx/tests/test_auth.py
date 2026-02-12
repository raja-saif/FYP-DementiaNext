"""
Unit and integration tests for authentication endpoints
Tests registration, login, verification, and Google OAuth
"""
import json
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient, APITestCase
from rest_framework_simplejwt.tokens import AccessToken
from allauth.socialaccount.models import SocialAccount

User = get_user_model()


class RegisterViewTests(APITestCase):
    """Tests for user registration endpoint"""
    
    def setUp(self):
        self.client = APIClient()
        self.url = reverse('register')
    
    def test_register_success(self):
        """Test successful user registration"""
        data = {
            'email': 'newuser@test.com',
            'password': 'SecurePass123!',
            'name': 'New User',
            'role': 'patient'
        }
        
        response = self.client.post(self.url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('token', response.data)
        self.assertIn('user', response.data)
        
        # Verify user data
        user_data = response.data['user']
        self.assertEqual(user_data['email'], 'newuser@test.com')
        self.assertEqual(user_data['name'], 'New User')
        self.assertEqual(user_data['role'], 'patient')
        
        # Verify user was created in database
        self.assertTrue(User.objects.filter(email='newuser@test.com').exists())
    
    def test_register_doctor_role(self):
        """Test registration with doctor role"""
        data = {
            'email': 'doctor@test.com',
            'password': 'DocPass123!',
            'name': 'Dr. Test',
            'role': 'doctor'
        }
        
        response = self.client.post(self.url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['user']['role'], 'doctor')
    
    def test_register_missing_email(self):
        """Test registration fails without email"""
        data = {
            'password': 'SecurePass123!',
            'name': 'Test User',
            'role': 'patient'
        }
        
        response = self.client.post(self.url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)
    
    def test_register_missing_password(self):
        """Test registration fails without password"""
        data = {
            'email': 'test@test.com',
            'name': 'Test User',
            'role': 'patient'
        }
        
        response = self.client.post(self.url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)
    
    def test_register_missing_name(self):
        """Test registration fails without name"""
        data = {
            'email': 'test@test.com',
            'password': 'SecurePass123!',
            'role': 'patient'
        }
        
        response = self.client.post(self.url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)
    
    def test_register_duplicate_email(self):
        """Test registration fails with existing email"""
        # Create existing user
        User.objects.create_user(
            username='existing@test.com',
            email='existing@test.com',
            password='password123'
        )
        
        data = {
            'email': 'existing@test.com',
            'password': 'NewPass123!',
            'name': 'New User',
            'role': 'patient'
        }
        
        response = self.client.post(self.url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)
        self.assertIn('already exists', response.data['error'].lower())
    
    def test_register_email_case_insensitive(self):
        """Test registration converts email to lowercase"""
        data = {
            'email': 'TestUser@TEST.COM',
            'password': 'SecurePass123!',
            'name': 'Test User',
            'role': 'patient'
        }
        
        response = self.client.post(self.url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify email was stored in lowercase
        user = User.objects.get(email='testuser@test.com')
        self.assertEqual(user.email, 'testuser@test.com')
    
    def test_register_default_role(self):
        """Test registration defaults to patient role"""
        data = {
            'email': 'test@test.com',
            'password': 'SecurePass123!',
            'name': 'Test User'
            # No role specified
        }
        
        response = self.client.post(self.url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['user']['role'], 'patient')


class LoginViewTests(APITestCase):
    """Tests for user login endpoint"""
    
    def setUp(self):
        self.client = APIClient()
        self.url = reverse('login_view')
        
        # Create test user
        self.user = User.objects.create_user(
            username='testuser@test.com',
            email='testuser@test.com',
            password='TestPass123!',
            first_name='Test User'
        )
    
    def test_login_success(self):
        """Test successful login"""
        data = {
            'email': 'testuser@test.com',
            'password': 'TestPass123!'
        }
        
        response = self.client.post(self.url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('token', response.data)
        self.assertIn('user', response.data)
        
        # Verify user data
        user_data = response.data['user']
        self.assertEqual(user_data['email'], 'testuser@test.com')
        self.assertEqual(user_data['name'], 'Test User')
    
    def test_login_wrong_password(self):
        """Test login fails with incorrect password"""
        data = {
            'email': 'testuser@test.com',
            'password': 'WrongPassword123!'
        }
        
        response = self.client.post(self.url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertIn('error', response.data)
        self.assertIn('invalid', response.data['error'].lower())
    
    def test_login_nonexistent_user(self):
        """Test login fails for non-existent user"""
        data = {
            'email': 'nonexistent@test.com',
            'password': 'SomePass123!'
        }
        
        response = self.client.post(self.url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertIn('error', response.data)
    
    def test_login_email_case_insensitive(self):
        """Test login works with different email case"""
        data = {
            'email': 'TESTUSER@TEST.COM',
            'password': 'TestPass123!'
        }
        
        response = self.client.post(self.url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
    
    def test_login_missing_email(self):
        """Test login fails without email"""
        data = {
            'password': 'TestPass123!'
        }
        
        response = self.client.post(self.url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_login_missing_password(self):
        """Test login fails without password"""
        data = {
            'email': 'testuser@test.com'
        }
        
        response = self.client.post(self.url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_login_returns_valid_token(self):
        """Test login returns a valid JWT token"""
        data = {
            'email': 'testuser@test.com',
            'password': 'TestPass123!'
        }
        
        response = self.client.post(self.url, data, format='json')
        
        token_str = response.data['token']
        
        # Verify token is valid
        try:
            token = AccessToken(token_str)
            user_id = token.get('user_id')
            self.assertEqual(int(user_id), self.user.id)
        except Exception:
            self.fail('Token is not valid')


class VerifyViewTests(APITestCase):
    """Tests for token verification endpoint"""
    
    def setUp(self):
        self.client = APIClient()
        self.url = reverse('verify')
        
        self.user = User.objects.create_user(
            username='testuser@test.com',
            email='testuser@test.com',
            password='TestPass123!',
            first_name='Test User'
        )
        
        self.token = AccessToken.for_user(self.user)
        self.token['role'] = 'patient'
        self.token_str = str(self.token)
    
    def test_verify_valid_token(self):
        """Test verification with valid token"""
        data = {'token': self.token_str}
        
        response = self.client.post(self.url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('user', response.data)
        self.assertEqual(response.data['user']['email'], 'testuser@test.com')
    
    def test_verify_invalid_token(self):
        """Test verification with invalid token"""
        data = {'token': 'invalid.token.here'}
        
        response = self.client.post(self.url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertIn('error', response.data)
    
    def test_verify_missing_token(self):
        """Test verification without token"""
        data = {}
        
        response = self.client.post(self.url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertIn('error', response.data)
    
    def test_verify_expired_token(self):
        """Test verification with expired token"""
        from datetime import timedelta
        # Create an expired token
        token = AccessToken.for_user(self.user)
        token.set_exp(lifetime=timedelta(seconds=-1))  # Set to expired
        expired_token_str = str(token)
        
        data = {'token': expired_token_str}
        
        response = self.client.post(self.url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class GoogleLoginViewTests(APITestCase):
    """Tests for Google OAuth login endpoint"""
    
    def setUp(self):
        self.client = APIClient()
        self.url = reverse('google_login')
    
    def test_google_login_new_user(self):
        """Test Google login creates new user"""
        data = {
            'email': 'googleuser@gmail.com',
            'name': 'Google User',
            'google_id': '123456789',
            'role': 'patient'
        }
        
        response = self.client.post(self.url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('token', response.data)
        self.assertIn('user', response.data)
        
        # Verify user was created
        user = User.objects.get(email='googleuser@gmail.com')
        self.assertEqual(user.first_name, 'Google User')
        
        # Verify social account was created
        social = SocialAccount.objects.filter(user=user, provider='google').first()
        self.assertIsNotNone(social)
        self.assertEqual(social.uid, '123456789')
    
    def test_google_login_existing_user(self):
        """Test Google login with existing user"""
        # Create existing user
        existing_user = User.objects.create_user(
            username='existing@gmail.com',
            email='existing@gmail.com',
            first_name='Existing User'
        )
        
        data = {
            'email': 'existing@gmail.com',
            'name': 'Updated Name',
            'google_id': '987654321',
            'role': 'patient'
        }
        
        response = self.client.post(self.url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify no new user was created
        self.assertEqual(User.objects.filter(email='existing@gmail.com').count(), 1)
        
        # Verify social account was linked
        social = SocialAccount.objects.filter(user=existing_user, provider='google').first()
        self.assertIsNotNone(social)
    
    def test_google_login_missing_email(self):
        """Test Google login fails without email"""
        data = {
            'name': 'Test User',
            'google_id': '123456789',
            'role': 'patient'
        }
        
        response = self.client.post(self.url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_google_login_without_google_id(self):
        """Test Google login works without google_id"""
        data = {
            'email': 'user@gmail.com',
            'name': 'User Name',
            'role': 'patient'
        }
        
        response = self.client.post(self.url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # User should be created
        self.assertTrue(User.objects.filter(email='user@gmail.com').exists())
    
    def test_google_login_default_role(self):
        """Test Google login defaults to patient role"""
        data = {
            'email': 'user@gmail.com',
            'name': 'User Name'
            # No role specified
        }
        
        response = self.client.post(self.url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['user']['role'], 'patient')
    
    def test_google_login_updates_name_if_missing(self):
        """Test Google login updates name if user exists without name"""
        # Create user without first_name
        User.objects.create_user(
            username='user@gmail.com',
            email='user@gmail.com'
        )
        
        data = {
            'email': 'user@gmail.com',
            'name': 'New Name',
            'role': 'patient'
        }
        
        response = self.client.post(self.url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify name was updated
        user = User.objects.get(email='user@gmail.com')
        self.assertEqual(user.first_name, 'New Name')
    
    def test_google_login_preserves_existing_name(self):
        """Test Google login doesn't overwrite existing name"""
        # Create user with existing name
        User.objects.create_user(
            username='user@gmail.com',
            email='user@gmail.com',
            first_name='Original Name'
        )
        
        data = {
            'email': 'user@gmail.com',
            'name': 'New Name',
            'role': 'patient'
        }
        
        response = self.client.post(self.url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify original name was preserved
        user = User.objects.get(email='user@gmail.com')
        self.assertEqual(user.first_name, 'Original Name')


class TokenUtilityTests(TestCase):
    """Tests for token utility functions"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@test.com',
            first_name='Test User'
        )
    
    def test_issue_token_creates_valid_token(self):
        """Test issue_token creates a valid JWT token"""
        from authx.views import issue_token
        
        token_str = issue_token(self.user, 'patient')
        
        # Verify token is valid
        token = AccessToken(token_str)
        self.assertEqual(str(token['user_id']), str(self.user.id))
        self.assertEqual(token['role'], 'patient')
        self.assertEqual(token['name'], 'Test User')
    
    def test_make_user_payload(self):
        """Test make_user_payload creates correct user data"""
        from authx.views import make_user_payload
        
        payload = make_user_payload(self.user, 'doctor')
        
        self.assertEqual(payload['id'], str(self.user.id))
        self.assertEqual(payload['email'], 'test@test.com')
        self.assertEqual(payload['name'], 'Test User')
        self.assertEqual(payload['role'], 'doctor')
    
    def test_make_user_payload_uses_username_if_no_name(self):
        """Test make_user_payload falls back to username"""
        user = User.objects.create_user(
            username='useronly',
            email='user@test.com'
            # No first_name
        )
        
        from authx.views import make_user_payload
        
        payload = make_user_payload(user, 'patient')
        
        self.assertEqual(payload['name'], 'useronly')
