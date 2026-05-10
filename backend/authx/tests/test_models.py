"""
Unit tests for authx models: User, PatientProfile, DoctorProfile
"""
from datetime import date
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.db.utils import IntegrityError
from authx.models import PatientProfile, DoctorProfile

User = get_user_model()


class CustomUserManagerTests(TestCase):

    def test_create_user_with_email(self):
        user = User.objects.create_user(
            email='test@example.com', password='pass1234'
        )
        self.assertEqual(user.email, 'test@example.com')
        self.assertTrue(user.check_password('pass1234'))
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)

    def test_create_user_normalizes_email(self):
        user = User.objects.create_user(
            email='Test@EXAMPLE.COM', password='pass1234'
        )
        self.assertEqual(user.email, 'Test@example.com')

    def test_create_user_without_email_raises(self):
        with self.assertRaises(ValueError):
            User.objects.create_user(email='', password='pass1234')

    def test_create_superuser(self):
        admin = User.objects.create_superuser(
            email='admin@example.com', password='adminpass'
        )
        self.assertTrue(admin.is_staff)
        self.assertTrue(admin.is_superuser)
        self.assertEqual(admin.role, 'admin')

    def test_create_user_default_role(self):
        user = User.objects.create_user(
            email='default@test.com', password='pass1234'
        )
        self.assertEqual(user.role, 'patient')


class UserModelTests(TestCase):

    def test_str_with_full_name(self):
        user = User.objects.create_user(
            email='str@test.com', password='pass1234',
            first_name='John', last_name='Doe', role='patient'
        )
        self.assertIn('John Doe', str(user))
        self.assertIn('Patient', str(user))

    def test_str_without_name_falls_back_to_email(self):
        user = User.objects.create_user(email='noname@test.com', password='p')
        self.assertIn('noname@test.com', str(user))

    def test_role_choices(self):
        for role in ('patient', 'doctor', 'admin'):
            user = User.objects.create_user(
                email=f'{role}@test.com', password='p', role=role
            )
            self.assertEqual(user.role, role)

    def test_email_unique(self):
        User.objects.create_user(email='dup@test.com', password='p')
        with self.assertRaises(IntegrityError):
            User.objects.create_user(email='dup@test.com', password='p2')

    def test_phone_number_optional(self):
        user = User.objects.create_user(
            email='phone@test.com', password='p', phone_number='1234567890'
        )
        self.assertEqual(user.phone_number, '1234567890')

    def test_username_field_is_email(self):
        self.assertEqual(User.USERNAME_FIELD, 'email')

    def test_required_fields_empty(self):
        self.assertEqual(User.REQUIRED_FIELDS, [])


class PatientProfileTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            email='patient@test.com', password='p', role='patient',
            first_name='Pat', last_name='Ient'
        )

    def test_create_profile(self):
        profile = PatientProfile.objects.create(
            user=self.user,
            date_of_birth=date(1960, 5, 15),
            gender='M'
        )
        self.assertIsNotNone(profile.patient_id)
        self.assertTrue(profile.patient_id.startswith('P'))

    def test_auto_generated_patient_id(self):
        p1 = PatientProfile.objects.create(
            user=self.user, date_of_birth=date(1960, 1, 1), gender='M'
        )
        u2 = User.objects.create_user(email='p2@test.com', password='p')
        p2 = PatientProfile.objects.create(
            user=u2, date_of_birth=date(1970, 1, 1), gender='F'
        )
        self.assertNotEqual(p1.patient_id, p2.patient_id)

    def test_str_representation(self):
        profile = PatientProfile.objects.create(
            user=self.user, date_of_birth=date(1960, 1, 1), gender='M'
        )
        s = str(profile)
        self.assertIn(profile.patient_id, s)
        self.assertIn('Pat Ient', s)

    def test_optional_fields(self):
        profile = PatientProfile.objects.create(
            user=self.user,
            date_of_birth=date(1960, 1, 1),
            gender='M',
            blood_group='O+',
            address='123 Main St',
            emergency_contact='0987654321',
            allergies='None',
            current_medications='Aspirin',
            medical_history={'condition': 'MCI'}
        )
        self.assertEqual(profile.blood_group, 'O+')
        self.assertEqual(profile.medical_history['condition'], 'MCI')

    def test_one_to_one_relationship(self):
        PatientProfile.objects.create(
            user=self.user, date_of_birth=date(1960, 1, 1), gender='M'
        )
        with self.assertRaises(IntegrityError):
            PatientProfile.objects.create(
                user=self.user, date_of_birth=date(1970, 1, 1), gender='F'
            )

    def test_cascade_delete(self):
        PatientProfile.objects.create(
            user=self.user, date_of_birth=date(1960, 1, 1), gender='M'
        )
        self.user.delete()
        self.assertEqual(PatientProfile.objects.count(), 0)


class DoctorProfileTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            email='doctor@test.com', password='p', role='doctor',
            first_name='Dr', last_name='Smith'
        )

    def test_create_profile(self):
        profile = DoctorProfile.objects.create(
            user=self.user,
            license_number='LIC-001',
            specialization='neurology',
            qualifications='MD, PhD',
            experience_years=10,
            hospital_affiliation='General Hospital'
        )
        self.assertIsNotNone(profile.doctor_id)
        self.assertTrue(profile.doctor_id.startswith('D'))

    def test_str_representation(self):
        profile = DoctorProfile.objects.create(
            user=self.user,
            license_number='LIC-002',
            specialization='radiology',
            qualifications='MD',
            experience_years=5,
            hospital_affiliation='City Hospital'
        )
        s = str(profile)
        self.assertIn('Dr. Dr Smith', s)
        self.assertIn('Radiology', s)

    def test_license_number_unique(self):
        DoctorProfile.objects.create(
            user=self.user,
            license_number='UNIQUE-LIC',
            specialization='neurology',
            qualifications='MD',
            experience_years=5,
            hospital_affiliation='Hosp'
        )
        u2 = User.objects.create_user(email='doc2@t.com', password='p', role='doctor')
        with self.assertRaises(IntegrityError):
            DoctorProfile.objects.create(
                user=u2,
                license_number='UNIQUE-LIC',
                specialization='psychiatry',
                qualifications='MD',
                experience_years=3,
                hospital_affiliation='Hosp2'
            )

    def test_is_verified_default_false(self):
        profile = DoctorProfile.objects.create(
            user=self.user,
            license_number='LIC-V',
            specialization='neurology',
            qualifications='MD',
            experience_years=5,
            hospital_affiliation='Hosp'
        )
        self.assertFalse(profile.is_verified)

    def test_optional_fields(self):
        profile = DoctorProfile.objects.create(
            user=self.user,
            license_number='LIC-OPT',
            specialization='geriatrics',
            qualifications='MD',
            experience_years=15,
            hospital_affiliation='Senior Care',
            consultation_fee=150.00,
            available_days=['Monday', 'Wednesday'],
            bio='Specialist in elderly care'
        )
        self.assertEqual(profile.consultation_fee, 150.00)
        self.assertEqual(len(profile.available_days), 2)
        self.assertEqual(profile.bio, 'Specialist in elderly care')

    def test_cascade_delete(self):
        DoctorProfile.objects.create(
            user=self.user,
            license_number='LIC-DEL',
            specialization='neurology',
            qualifications='MD',
            experience_years=5,
            hospital_affiliation='Hosp'
        )
        self.user.delete()
        self.assertEqual(DoctorProfile.objects.count(), 0)
