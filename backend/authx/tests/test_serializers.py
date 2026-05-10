"""
Unit tests for authx serializers
"""
from datetime import date
from django.test import TestCase
from django.contrib.auth import get_user_model
from authx.serializers import (
    UserSerializer, RegisterSerializer, LoginSerializer,
    PatientProfileSerializer, DoctorProfileSerializer
)
from authx.models import PatientProfile, DoctorProfile

User = get_user_model()


class UserSerializerTests(TestCase):

    def test_serializes_user_fields(self):
        user = User.objects.create_user(
            email='u@t.com', password='p',
            first_name='A', last_name='B', role='patient'
        )
        data = UserSerializer(user).data
        self.assertEqual(data['email'], 'u@t.com')
        self.assertEqual(data['first_name'], 'A')
        self.assertEqual(data['role'], 'patient')
        self.assertNotIn('password', data)


class RegisterSerializerTests(TestCase):

    def test_valid_patient_registration(self):
        data = {
            'email': 'pat@test.com', 'password': 'SecurePass1',
            'first_name': 'Pat', 'last_name': 'Test',
            'role': 'patient',
            'date_of_birth': '1960-01-15', 'gender': 'M',
        }
        ser = RegisterSerializer(data=data)
        self.assertTrue(ser.is_valid(), ser.errors)
        user = ser.save()
        self.assertEqual(user.role, 'patient')
        self.assertTrue(hasattr(user, 'patient_profile'))

    def test_valid_doctor_registration(self):
        data = {
            'email': 'doc@test.com', 'password': 'SecurePass1',
            'first_name': 'Dr', 'last_name': 'Doc',
            'role': 'doctor',
            'license_number': 'LIC-REG',
            'specialization': 'neurology',
            'qualifications': 'MD',
            'experience_years': 10,
            'hospital_affiliation': 'General Hospital',
        }
        ser = RegisterSerializer(data=data)
        self.assertTrue(ser.is_valid(), ser.errors)
        user = ser.save()
        self.assertEqual(user.role, 'doctor')
        self.assertTrue(hasattr(user, 'doctor_profile'))

    def test_patient_missing_required_fields(self):
        data = {
            'email': 'miss@test.com', 'password': 'SecurePass1',
            'first_name': 'X', 'last_name': 'Y',
            'role': 'patient',
        }
        ser = RegisterSerializer(data=data)
        self.assertFalse(ser.is_valid())

    def test_doctor_missing_required_fields(self):
        data = {
            'email': 'miss@test.com', 'password': 'SecurePass1',
            'first_name': 'X', 'last_name': 'Y',
            'role': 'doctor',
        }
        ser = RegisterSerializer(data=data)
        self.assertFalse(ser.is_valid())

    def test_duplicate_email_rejected(self):
        User.objects.create_user(email='dup@test.com', password='p')
        data = {
            'email': 'dup@test.com', 'password': 'SecurePass1',
            'first_name': 'X', 'last_name': 'Y',
            'role': 'patient', 'date_of_birth': '1990-01-01', 'gender': 'F',
        }
        ser = RegisterSerializer(data=data)
        self.assertFalse(ser.is_valid())
        self.assertIn('email', ser.errors)

    def test_duplicate_license_rejected(self):
        doc = User.objects.create_user(email='d1@t.com', password='p', role='doctor')
        DoctorProfile.objects.create(
            user=doc, license_number='DUP-LIC', specialization='neurology',
            qualifications='MD', experience_years=5, hospital_affiliation='H'
        )
        data = {
            'email': 'd2@t.com', 'password': 'SecurePass1',
            'first_name': 'X', 'last_name': 'Y',
            'role': 'doctor',
            'license_number': 'DUP-LIC',
            'specialization': 'radiology',
            'qualifications': 'MD',
            'experience_years': 3,
            'hospital_affiliation': 'H2',
        }
        ser = RegisterSerializer(data=data)
        self.assertFalse(ser.is_valid())
        self.assertIn('license_number', ser.errors)

    def test_short_password_rejected(self):
        data = {
            'email': 'short@test.com', 'password': 'ab',
            'first_name': 'X', 'last_name': 'Y',
            'role': 'patient', 'date_of_birth': '1990-01-01', 'gender': 'M',
        }
        ser = RegisterSerializer(data=data)
        self.assertFalse(ser.is_valid())

    def test_email_lowered_on_validation(self):
        data = {
            'email': 'UPPER@TEST.COM', 'password': 'SecurePass1',
            'first_name': 'X', 'last_name': 'Y',
            'role': 'patient', 'date_of_birth': '1990-01-01', 'gender': 'F',
        }
        ser = RegisterSerializer(data=data)
        self.assertTrue(ser.is_valid(), ser.errors)
        self.assertEqual(ser.validated_data['email'], 'upper@test.com')


class LoginSerializerTests(TestCase):

    def test_valid_data(self):
        ser = LoginSerializer(data={'email': 'x@t.com', 'password': 'pass'})
        self.assertTrue(ser.is_valid())

    def test_missing_email(self):
        ser = LoginSerializer(data={'password': 'pass'})
        self.assertFalse(ser.is_valid())

    def test_missing_password(self):
        ser = LoginSerializer(data={'email': 'x@t.com'})
        self.assertFalse(ser.is_valid())


class PatientProfileSerializerTests(TestCase):

    def test_serializes_profile(self):
        user = User.objects.create_user(
            email='pp@t.com', password='p', first_name='P', last_name='P'
        )
        profile = PatientProfile.objects.create(
            user=user, date_of_birth=date(1960, 1, 1), gender='M'
        )
        data = PatientProfileSerializer(profile).data
        self.assertIn('patient_id', data)
        self.assertIn('user', data)
        self.assertEqual(data['gender'], 'M')


class DoctorProfileSerializerTests(TestCase):

    def test_serializes_profile(self):
        user = User.objects.create_user(
            email='dp@t.com', password='p', first_name='D', last_name='P', role='doctor'
        )
        profile = DoctorProfile.objects.create(
            user=user, license_number='L1', specialization='neurology',
            qualifications='MD', experience_years=5, hospital_affiliation='H'
        )
        data = DoctorProfileSerializer(profile).data
        self.assertIn('doctor_id', data)
        self.assertIn('user', data)
        self.assertEqual(data['specialization'], 'neurology')
