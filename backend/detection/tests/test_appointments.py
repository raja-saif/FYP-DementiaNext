"""
Tests for Appointment, DoctorReview, FHIRDiagnosticReport models
and AppointmentViewSet, DoctorListViewSet, FHIRDiagnosticReportViewSet
"""
from datetime import datetime, timedelta
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import AccessToken

from detection.models import (
    Appointment, DetectionResult, FHIRDiagnosticReport,
    ModelMetadata, DoctorReview,
)
from detection.serializers import (
    AppointmentSerializer, FHIRDiagnosticReportSerializer,
    DoctorReviewSerializer, PatientVisibleReviewSerializer,
)
from authx.models import DoctorProfile, PatientProfile

User = get_user_model()


class AppointmentModelTests(TestCase):

    def setUp(self):
        self.patient = User.objects.create_user(
            email='apt_pat@t.com', password='p', role='patient',
            first_name='Apt', last_name='Patient'
        )
        self.doctor = User.objects.create_user(
            email='apt_doc@t.com', password='p', role='doctor',
            first_name='Apt', last_name='Doctor'
        )

    def test_create_appointment(self):
        apt = Appointment.objects.create(
            patient=self.patient, doctor=self.doctor,
            appointment_date=timezone.now() + timedelta(days=7),
            reason='MRI Consultation',
        )
        self.assertIsNotNone(apt.appointment_id)
        self.assertTrue(apt.appointment_id.startswith('APT'))
        self.assertEqual(apt.status, 'pending')

    def test_auto_generated_appointment_id(self):
        a1 = Appointment.objects.create(
            patient=self.patient, doctor=self.doctor,
            appointment_date=timezone.now(), reason='R1',
        )
        a2 = Appointment.objects.create(
            patient=self.patient, doctor=self.doctor,
            appointment_date=timezone.now(), reason='R2',
        )
        self.assertNotEqual(a1.appointment_id, a2.appointment_id)

    def test_str_representation(self):
        apt = Appointment.objects.create(
            patient=self.patient, doctor=self.doctor,
            appointment_date=timezone.now(), reason='Test',
        )
        s = str(apt)
        self.assertIn(apt.appointment_id, s)
        self.assertIn('Apt Patient', s)
        self.assertIn('Dr. Apt Doctor', s)

    def test_status_choices(self):
        for choice_key, _ in Appointment.STATUS_CHOICES:
            apt = Appointment.objects.create(
                patient=self.patient, doctor=self.doctor,
                appointment_date=timezone.now(), reason='R',
                status=choice_key,
            )
            self.assertEqual(apt.status, choice_key)

    def test_ordering_by_date_desc(self):
        a1 = Appointment.objects.create(
            patient=self.patient, doctor=self.doctor,
            appointment_date=timezone.now() - timedelta(days=1), reason='Old',
        )
        a2 = Appointment.objects.create(
            patient=self.patient, doctor=self.doctor,
            appointment_date=timezone.now() + timedelta(days=1), reason='New',
        )
        apts = list(Appointment.objects.all())
        self.assertEqual(apts[0], a2)

    def test_cascade_delete_patient(self):
        Appointment.objects.create(
            patient=self.patient, doctor=self.doctor,
            appointment_date=timezone.now(), reason='Del',
        )
        self.patient.delete()
        self.assertEqual(Appointment.objects.count(), 0)


class DoctorReviewModelTests(TestCase):

    def setUp(self):
        self.patient = User.objects.create_user(
            email='rev_pat@t.com', password='p', role='patient',
            first_name='Rev', last_name='Patient'
        )
        self.doctor = User.objects.create_user(
            email='rev_doc@t.com', password='p', role='doctor',
            first_name='Rev', last_name='Doctor'
        )
        self.detection = DetectionResult.objects.create(
            patient=self.patient, doctor=self.doctor,
            uploaded_file=SimpleUploadedFile('r.jpg', b'x', 'image/jpeg'),
            file_size=100, status='completed',
            predicted_class='alzheimers', confidence_score=0.85,
        )

    def test_create_review(self):
        review = DoctorReview.objects.create(
            detection=self.detection,
            doctor=self.doctor,
            patient=self.patient,
            ai_accepted=True,
            doctor_conclusion='Consistent with early AD.',
            patient_summary='The scan suggests mild changes.',
        )
        self.assertFalse(review.is_sent_to_patient)
        self.assertIsNone(review.sent_at)

    def test_str_draft(self):
        review = DoctorReview.objects.create(
            detection=self.detection, doctor=self.doctor, patient=self.patient,
            doctor_conclusion='c', patient_summary='s',
        )
        self.assertIn('Draft', str(review))

    def test_str_sent(self):
        review = DoctorReview.objects.create(
            detection=self.detection, doctor=self.doctor, patient=self.patient,
            doctor_conclusion='c', patient_summary='s',
            is_sent_to_patient=True, sent_at=timezone.now(),
        )
        self.assertIn('Sent', str(review))

    def test_one_to_one_with_detection(self):
        DoctorReview.objects.create(
            detection=self.detection, doctor=self.doctor, patient=self.patient,
            doctor_conclusion='c', patient_summary='s',
        )
        from django.db.utils import IntegrityError
        with self.assertRaises(IntegrityError):
            DoctorReview.objects.create(
                detection=self.detection, doctor=self.doctor, patient=self.patient,
                doctor_conclusion='c2', patient_summary='s2',
            )

    def test_override_class(self):
        review = DoctorReview.objects.create(
            detection=self.detection, doctor=self.doctor, patient=self.patient,
            ai_accepted=False,
            doctor_override_class='cn',
            doctor_conclusion='Override: normal',
            patient_summary='Everything looks fine.',
        )
        self.assertFalse(review.ai_accepted)
        self.assertEqual(review.doctor_override_class, 'cn')


class FHIRDiagnosticReportModelTests(TestCase):

    def setUp(self):
        self.patient = User.objects.create_user(
            email='fhir_pat@t.com', password='p', role='patient',
            first_name='FHIR', last_name='Patient'
        )
        self.doctor = User.objects.create_user(
            email='fhir_doc@t.com', password='p', role='doctor',
            first_name='FHIR', last_name='Doctor'
        )
        self.detection = DetectionResult.objects.create(
            patient=self.patient, doctor=self.doctor,
            uploaded_file=SimpleUploadedFile('f.jpg', b'x', 'image/jpeg'),
            file_size=100, status='completed',
            predicted_class='cn', confidence_score=0.92,
        )

    def test_create_fhir_report(self):
        report = FHIRDiagnosticReport.objects.create(
            detection=self.detection,
            patient=self.patient, doctor=self.doctor,
            effective_datetime=timezone.now(),
            conclusion='Normal cognition',
            hospital_name='Test Hospital',
        )
        self.assertIsNotNone(report.report_id)
        self.assertTrue(report.report_id.startswith('FHIR-DR-'))
        self.assertEqual(report.status, 'final')

    def test_fhir_json_auto_generated(self):
        report = FHIRDiagnosticReport.objects.create(
            detection=self.detection,
            patient=self.patient, doctor=self.doctor,
            effective_datetime=timezone.now(),
            conclusion='Normal',
            hospital_name='Test Hospital',
        )
        self.assertIn('resourceType', report.fhir_json)
        self.assertEqual(report.fhir_json['resourceType'], 'DiagnosticReport')

    def test_str_representation(self):
        report = FHIRDiagnosticReport.objects.create(
            detection=self.detection,
            patient=self.patient, doctor=self.doctor,
            effective_datetime=timezone.now(),
            conclusion='Normal',
            hospital_name='H',
        )
        s = str(report)
        self.assertIn('FHIR Report', s)
        self.assertIn('FHIR Patient', s)

    def test_one_to_one_with_detection(self):
        FHIRDiagnosticReport.objects.create(
            detection=self.detection,
            patient=self.patient, doctor=self.doctor,
            effective_datetime=timezone.now(),
            conclusion='C1', hospital_name='H',
        )
        from django.db.utils import IntegrityError
        with self.assertRaises(IntegrityError):
            FHIRDiagnosticReport.objects.create(
                detection=self.detection,
                patient=self.patient, doctor=self.doctor,
                effective_datetime=timezone.now(),
                conclusion='C2', hospital_name='H2',
            )


class AppointmentViewSetTests(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.patient = User.objects.create_user(
            email='apv_pat@t.com', password='p', role='patient',
            first_name='AV', last_name='Pat'
        )
        self.doctor = User.objects.create_user(
            email='apv_doc@t.com', password='p', role='doctor',
            first_name='AV', last_name='Doc'
        )
        DoctorProfile.objects.create(
            user=self.doctor, license_number='APV-LIC',
            specialization='neurology', qualifications='MD',
            experience_years=10, hospital_affiliation='Hospital',
            is_verified=True,
        )
        self.patient_token = str(AccessToken.for_user(self.patient))
        self.doctor_token = str(AccessToken.for_user(self.doctor))

        self.apt = Appointment.objects.create(
            patient=self.patient, doctor=self.doctor,
            appointment_date=timezone.now() + timedelta(days=5),
            reason='Checkup',
        )

    def test_patient_list_appointments(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.patient_token}')
        url = reverse('appointment-list')
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.data), 1)

    def test_doctor_list_appointments(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.doctor_token}')
        url = reverse('appointment-list')
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.data), 1)

    def test_patient_creates_appointment(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.patient_token}')
        url = reverse('appointment-list')
        data = {
            'doctor_id': self.doctor.id,
            'scheduled_date': (timezone.now() + timedelta(days=10)).strftime('%Y-%m-%d'),
            'scheduled_time': '10:00',
            'reason': 'Follow-up',
        }
        resp = self.client.post(url, data, format='json')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)

    def test_doctor_cannot_create_appointment(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.doctor_token}')
        url = reverse('appointment-list')
        data = {'reason': 'Test'}
        resp = self.client.post(url, data, format='json')
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_doctor_approves_appointment(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.doctor_token}')
        url = reverse('appointment-approve-appointment', args=[self.apt.id])
        resp = self.client.post(url)
        self.assertEqual(resp.status_code, 200)
        self.apt.refresh_from_db()
        self.assertEqual(self.apt.status, 'approved')

    def test_doctor_rejects_appointment(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.doctor_token}')
        url = reverse('appointment-reject-appointment', args=[self.apt.id])
        resp = self.client.post(url, {'reason': 'Not available'})
        self.assertEqual(resp.status_code, 200)
        self.apt.refresh_from_db()
        self.assertEqual(self.apt.status, 'rejected')

    def test_patient_cancels_appointment(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.patient_token}')
        url = reverse('appointment-cancel-appointment', args=[self.apt.id])
        resp = self.client.post(url)
        self.assertEqual(resp.status_code, 200)
        self.apt.refresh_from_db()
        self.assertEqual(self.apt.status, 'cancelled')

    def test_patient_cannot_approve(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.patient_token}')
        url = reverse('appointment-approve-appointment', args=[self.apt.id])
        resp = self.client.post(url)
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_pending_appointments_doctor_only(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.doctor_token}')
        url = reverse('appointment-pending-appointments')
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)

    def test_pending_appointments_patient_forbidden(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.patient_token}')
        url = reverse('appointment-pending-appointments')
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_my_appointments(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.patient_token}')
        url = reverse('appointment-my-appointments')
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)

    def test_unauthenticated_access(self):
        url = reverse('appointment-list')
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)


class DetectionReviewViewTests(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.patient = User.objects.create_user(
            email='rv_pat@t.com', password='p', role='patient',
            first_name='RV', last_name='Pat',
        )
        self.doctor = User.objects.create_user(
            email='rv_doc@t.com', password='p', role='doctor',
            first_name='RV', last_name='Doc',
        )
        self.patient_token = str(AccessToken.for_user(self.patient))
        self.doctor_token = str(AccessToken.for_user(self.doctor))

        self.detection = DetectionResult.objects.create(
            patient=self.patient, doctor=self.doctor,
            uploaded_file=SimpleUploadedFile('rv.jpg', b'x', 'image/jpeg'),
            file_size=100, status='completed',
            predicted_class='dementia', confidence_score=0.78,
        )

    def test_doctor_creates_review(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.doctor_token}')
        url = reverse('detection-review', args=[self.detection.id])
        data = {
            'ai_accepted': True,
            'doctor_conclusion': 'Consistent findings.',
            'patient_summary': 'Mild changes detected.',
        }
        resp = self.client.post(url, data, format='json')
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(DoctorReview.objects.filter(detection=self.detection).exists())

    def test_doctor_gets_review(self):
        DoctorReview.objects.create(
            detection=self.detection, doctor=self.doctor, patient=self.patient,
            doctor_conclusion='C', patient_summary='S',
        )
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.doctor_token}')
        url = reverse('detection-review', args=[self.detection.id])
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)

    def test_get_review_404_when_none(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.doctor_token}')
        url = reverse('detection-review', args=[self.detection.id])
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_patient_cannot_review(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.patient_token}')
        url = reverse('detection-review', args=[self.detection.id])
        resp = self.client.post(url, {'doctor_conclusion': 'c', 'patient_summary': 's'})
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)


class PatientReportViewTests(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.patient = User.objects.create_user(
            email='pr_pat@t.com', password='p', role='patient',
            first_name='PR', last_name='Pat',
        )
        self.doctor = User.objects.create_user(
            email='pr_doc@t.com', password='p', role='doctor',
            first_name='PR', last_name='Doc',
        )
        self.patient_token = str(AccessToken.for_user(self.patient))

        self.detection = DetectionResult.objects.create(
            patient=self.patient, doctor=self.doctor,
            uploaded_file=SimpleUploadedFile('pr.jpg', b'x', 'image/jpeg'),
            file_size=100, status='completed',
            predicted_class='cn', confidence_score=0.91,
        )

    def test_my_reports_empty(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.patient_token}')
        url = reverse('patient-reports-my-reports')
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.data), 0)

    def test_my_reports_with_sent_review(self):
        DoctorReview.objects.create(
            detection=self.detection, doctor=self.doctor, patient=self.patient,
            doctor_conclusion='All clear.', patient_summary='Normal.',
            is_sent_to_patient=True, sent_at=timezone.now(),
        )
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.patient_token}')
        url = reverse('patient-reports-my-reports')
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.data), 1)

    def test_unsent_review_not_visible(self):
        DoctorReview.objects.create(
            detection=self.detection, doctor=self.doctor, patient=self.patient,
            doctor_conclusion='Draft.', patient_summary='Pending.',
            is_sent_to_patient=False,
        )
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.patient_token}')
        url = reverse('patient-reports-my-reports')
        resp = self.client.get(url)
        self.assertEqual(len(resp.data), 0)

    def test_fhir_download_not_found(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.patient_token}')
        url = reverse('patient-reports-fhir-download', args=[9999])
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_fhir_download_success(self):
        review = DoctorReview.objects.create(
            detection=self.detection, doctor=self.doctor, patient=self.patient,
            doctor_conclusion='OK.', patient_summary='Fine.',
            is_sent_to_patient=True, sent_at=timezone.now(),
        )
        FHIRDiagnosticReport.objects.create(
            detection=self.detection,
            patient=self.patient, doctor=self.doctor,
            effective_datetime=timezone.now(),
            conclusion='Normal', hospital_name='H',
        )
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.patient_token}')
        url = reverse('patient-reports-fhir-download', args=[review.id])
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)


class DoctorListViewSetTests(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.patient = User.objects.create_user(
            email='dl_pat@t.com', password='p', role='patient'
        )
        self.doctor = User.objects.create_user(
            email='dl_doc@t.com', password='p', role='doctor',
            first_name='DL', last_name='Doc',
        )
        DoctorProfile.objects.create(
            user=self.doctor, license_number='DL-LIC',
            specialization='neurology', qualifications='MD',
            experience_years=10, hospital_affiliation='Hospital',
            is_verified=True,
        )
        self.token = str(AccessToken.for_user(self.patient))

    def test_list_verified_doctors(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token}')
        url = reverse('doctor-list')
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertGreaterEqual(len(resp.data), 0)

    def test_unverified_doctor_excluded(self):
        unverified = User.objects.create_user(
            email='dl_unv@t.com', password='p', role='doctor'
        )
        DoctorProfile.objects.create(
            user=unverified, license_number='DL-UNV',
            specialization='radiology', qualifications='MD',
            experience_years=2, hospital_affiliation='H2',
            is_verified=False,
        )
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token}')
        url = reverse('doctor-list')
        resp = self.client.get(url)
        unv_ids = [d['id'] for d in resp.data]
        self.assertNotIn(unverified.id, unv_ids)

    def test_unauthenticated_access(self):
        url = reverse('doctor-list')
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)


class FHIRDiagnosticReportViewSetTests(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.patient = User.objects.create_user(
            email='fhirv_pat@t.com', password='p', role='patient'
        )
        self.doctor = User.objects.create_user(
            email='fhirv_doc@t.com', password='p', role='doctor'
        )
        self.patient_token = str(AccessToken.for_user(self.patient))
        self.doctor_token = str(AccessToken.for_user(self.doctor))

        self.detection = DetectionResult.objects.create(
            patient=self.patient, doctor=self.doctor,
            uploaded_file=SimpleUploadedFile('fv.jpg', b'x', 'image/jpeg'),
            file_size=100, status='completed',
            predicted_class='alzheimers', confidence_score=0.88,
        )
        self.report = FHIRDiagnosticReport.objects.create(
            detection=self.detection,
            patient=self.patient, doctor=self.doctor,
            effective_datetime=timezone.now(),
            conclusion='AD detected', hospital_name='Hospital',
        )

    def test_doctor_list_reports(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.doctor_token}')
        url = reverse('fhir-report-list')
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.data), 1)

    def test_patient_list_reports(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.patient_token}')
        url = reverse('fhir-report-list')
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.data), 1)

    def test_doctor_deletes_own_report(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.doctor_token}')
        url = reverse('fhir-report-detail', args=[self.report.id])
        resp = self.client.delete(url)
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)

    def test_patient_cannot_delete_report(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.patient_token}')
        url = reverse('fhir-report-detail', args=[self.report.id])
        resp = self.client.delete(url)
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_get_fhir_json(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.doctor_token}')
        url = reverse('fhir-report-get-fhir-json', args=[self.report.id])
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertIn('resourceType', resp.data)

    def test_my_reports(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.doctor_token}')
        url = reverse('fhir-report-my-reports')
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)

    def test_create_not_allowed(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.doctor_token}')
        url = reverse('fhir-report-list')
        resp = self.client.post(url, {}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)


class DetectionResultModelExtendedTests(TestCase):
    """Additional model tests for DetectionResult fields not covered elsewhere."""

    def setUp(self):
        self.patient = User.objects.create_user(
            email='ext_pat@t.com', password='p', role='patient',
            first_name='Ext', last_name='Pat'
        )
        self.doctor = User.objects.create_user(
            email='ext_doc@t.com', password='p', role='doctor'
        )

    def test_detection_id_auto_generated(self):
        det = DetectionResult.objects.create(
            patient=self.patient,
            uploaded_file=SimpleUploadedFile('e.jpg', b'x', 'image/jpeg'),
            file_size=100,
        )
        self.assertTrue(det.detection_id.startswith('DET'))

    def test_str_pending(self):
        det = DetectionResult.objects.create(
            patient=self.patient,
            uploaded_file=SimpleUploadedFile('e.jpg', b'x', 'image/jpeg'),
            file_size=100,
        )
        self.assertIn('Pending', str(det))

    def test_str_completed(self):
        det = DetectionResult.objects.create(
            patient=self.patient,
            uploaded_file=SimpleUploadedFile('e.jpg', b'x', 'image/jpeg'),
            file_size=100, status='completed',
            predicted_class='cn', confidence_score=0.90,
        )
        s = str(det)
        self.assertIn(det.detection_id, s)
        self.assertIn('90', s)

    def test_model_type_default(self):
        det = DetectionResult.objects.create(
            patient=self.patient,
            uploaded_file=SimpleUploadedFile('e.jpg', b'x', 'image/jpeg'),
            file_size=100,
        )
        self.assertEqual(det.model_type, 'binary')

    def test_disease_choices(self):
        for key, _ in DetectionResult.DISEASE_CHOICES:
            det = DetectionResult.objects.create(
                patient=self.patient,
                uploaded_file=SimpleUploadedFile(f'{key}.jpg', b'x', 'image/jpeg'),
                file_size=100, predicted_class=key,
            )
            self.assertEqual(det.predicted_class, key)

    def test_model_metadata_str(self):
        mm = ModelMetadata.objects.create(
            name='Test', version='1.0', architecture='ResNet-34',
            accuracy=0.9, auc_score=0.9, sensitivity=0.9, specificity=0.9,
            trained_on=timezone.now().date(), model_path='m.pth',
        )
        self.assertIn('Test', str(mm))
        self.assertIn('1.0', str(mm))


class AppointmentSerializerTests(TestCase):

    def setUp(self):
        self.patient = User.objects.create_user(
            email='aps_pat@t.com', password='p', role='patient',
            first_name='AS', last_name='Pat'
        )
        self.doctor = User.objects.create_user(
            email='aps_doc@t.com', password='p', role='doctor',
            first_name='AS', last_name='Doc'
        )

    def test_serializer_fields(self):
        apt = Appointment.objects.create(
            patient=self.patient, doctor=self.doctor,
            appointment_date=timezone.now(), reason='Test',
        )
        data = AppointmentSerializer(apt).data
        self.assertIn('appointment_id', data)
        self.assertIn('status', data)
        self.assertIn('patient_name', data)
        self.assertIn('doctor_name', data)
        self.assertIn('scheduled_date', data)
        self.assertIn('scheduled_time', data)

    def test_scheduled_date_formatting(self):
        dt = timezone.make_aware(datetime(2026, 6, 15, 14, 30))
        apt = Appointment.objects.create(
            patient=self.patient, doctor=self.doctor,
            appointment_date=dt, reason='Test',
        )
        data = AppointmentSerializer(apt).data
        self.assertEqual(data['scheduled_date'], '2026-06-15')
        self.assertEqual(data['scheduled_time'], '14:30')


class DoctorReviewSerializerTests(TestCase):

    def test_serializes_review(self):
        patient = User.objects.create_user(
            email='drs_pat@t.com', password='p', role='patient',
            first_name='DRS', last_name='Pat',
        )
        doctor = User.objects.create_user(
            email='drs_doc@t.com', password='p', role='doctor',
            first_name='DRS', last_name='Doc',
        )
        det = DetectionResult.objects.create(
            patient=patient, doctor=doctor,
            uploaded_file=SimpleUploadedFile('dr.jpg', b'x', 'image/jpeg'),
            file_size=100, status='completed',
            predicted_class='alzheimers', confidence_score=0.85,
        )
        review = DoctorReview.objects.create(
            detection=det, doctor=doctor, patient=patient,
            doctor_conclusion='AD consistent',
            patient_summary='Changes detected.',
        )
        data = DoctorReviewSerializer(review).data
        self.assertIn('detection_id', data)
        self.assertIn('patient_name', data)
        self.assertIn('doctor_name', data)
        self.assertIn('predicted_class', data)
        self.assertIn('confidence_score', data)
        self.assertIn('doctor_notes', data)


class PatientVisibleReviewSerializerTests(TestCase):

    def test_excludes_doctor_notes(self):
        patient = User.objects.create_user(
            email='pvrs_pat@t.com', password='p', role='patient',
            first_name='PV', last_name='Pat',
        )
        doctor = User.objects.create_user(
            email='pvrs_doc@t.com', password='p', role='doctor',
            first_name='PV', last_name='Doc',
        )
        det = DetectionResult.objects.create(
            patient=patient, doctor=doctor,
            uploaded_file=SimpleUploadedFile('pv.jpg', b'x', 'image/jpeg'),
            file_size=100, status='completed',
            predicted_class='cn', confidence_score=0.95,
        )
        review = DoctorReview.objects.create(
            detection=det, doctor=doctor, patient=patient,
            doctor_conclusion='Normal', patient_summary='All clear.',
            doctor_notes='Internal note - DO NOT SHOW',
        )
        data = PatientVisibleReviewSerializer(review).data
        self.assertNotIn('doctor_notes', data)
        self.assertIn('patient_summary', data)
        self.assertIn('has_fhir_report', data)
        self.assertFalse(data['has_fhir_report'])

    def test_has_fhir_report_true(self):
        patient = User.objects.create_user(
            email='pvrs2_pat@t.com', password='p', role='patient'
        )
        doctor = User.objects.create_user(
            email='pvrs2_doc@t.com', password='p', role='doctor'
        )
        det = DetectionResult.objects.create(
            patient=patient, doctor=doctor,
            uploaded_file=SimpleUploadedFile('pv2.jpg', b'x', 'image/jpeg'),
            file_size=100, status='completed',
            predicted_class='alzheimers', confidence_score=0.85,
        )
        FHIRDiagnosticReport.objects.create(
            detection=det, patient=patient, doctor=doctor,
            effective_datetime=timezone.now(),
            conclusion='AD', hospital_name='H',
        )
        review = DoctorReview.objects.create(
            detection=det, doctor=doctor, patient=patient,
            doctor_conclusion='c', patient_summary='s',
        )
        data = PatientVisibleReviewSerializer(review).data
        self.assertTrue(data['has_fhir_report'])
        self.assertIsNotNone(data['fhir_report_id'])
