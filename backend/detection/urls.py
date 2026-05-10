from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import DetectionViewSet, ModelMetadataViewSet, PatientReportViewSet
from .appointment_views import AppointmentViewSet, DoctorListViewSet, FHIRDiagnosticReportViewSet

router = DefaultRouter()
router.register(r'detections', DetectionViewSet, basename='detection')
router.register(r'models', ModelMetadataViewSet, basename='model-metadata')
router.register(r'appointments', AppointmentViewSet, basename='appointment')
router.register(r'doctors', DoctorListViewSet, basename='doctor')
router.register(r'fhir-reports', FHIRDiagnosticReportViewSet, basename='fhir-report')
router.register(r'patient-reports', PatientReportViewSet, basename='patient-reports')

urlpatterns = [
    path('', include(router.urls)),
]
