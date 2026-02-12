from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q
from .models import Appointment, FHIRDiagnosticReport
from .serializers import AppointmentSerializer, FHIRDiagnosticReportSerializer
from authx.models import User


class AppointmentViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing appointments between patients and doctors
    """
    serializer_class = AppointmentSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Return appointments for the current user based on their role"""
        user = self.request.user
        if user.role == 'patient':
            return Appointment.objects.filter(patient=user)
        elif user.role == 'doctor':
            return Appointment.objects.filter(doctor=user)
        elif user.role == 'admin':
            return Appointment.objects.all()
        return Appointment.objects.none()
    
    def create(self, request, *args, **kwargs):
        """Create new appointment (patients only)"""
        if request.user.role != 'patient':
            return Response(
                {'error': 'Only patients can book appointments'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(patient=request.user)
        
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    @action(detail=True, methods=['post'], url_path='approve')
    def approve_appointment(self, request, pk=None):
        """Approve appointment (doctors only)"""
        if request.user.role != 'doctor':
            return Response(
                {'error': 'Only doctors can approve appointments'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        appointment = self.get_object()
        if appointment.doctor != request.user:
            return Response(
                {'error': 'You can only approve your own appointments'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        appointment.status = 'approved'
        appointment.doctor_notes = request.data.get('doctor_notes', appointment.doctor_notes)
        appointment.save()
        
        return Response(AppointmentSerializer(appointment).data)
    
    @action(detail=True, methods=['post'], url_path='reject')
    def reject_appointment(self, request, pk=None):
        """Reject appointment (doctors only)"""
        if request.user.role != 'doctor':
            return Response(
                {'error': 'Only doctors can reject appointments'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        appointment = self.get_object()
        if appointment.doctor != request.user:
            return Response(
                {'error': 'You can only reject your own appointments'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        appointment.status = 'rejected'
        appointment.doctor_notes = request.data.get('reason', appointment.doctor_notes)
        appointment.save()
        
        return Response(AppointmentSerializer(appointment).data)
    
    @action(detail=True, methods=['post'], url_path='cancel')
    def cancel_appointment(self, request, pk=None):
        """Cancel appointment (patients can cancel their own)"""
        appointment = self.get_object()
        
        if request.user.role == 'patient' and appointment.patient != request.user:
            return Response(
                {'error': 'You can only cancel your own appointments'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        appointment.status = 'cancelled'
        appointment.notes = request.data.get('reason', appointment.notes)
        appointment.save()
        
        return Response(AppointmentSerializer(appointment).data)
    
    @action(detail=False, methods=['get'], url_path='pending')
    def pending_appointments(self, request):
        """Get pending appointments for doctor"""
        if request.user.role != 'doctor':
            return Response(
                {'error': 'Only doctors can view pending appointments'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        pending = Appointment.objects.filter(
            doctor=request.user,
            status='pending'
        )
        serializer = self.get_serializer(pending, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'], url_path='my-appointments')
    def my_appointments(self, request):
        """Get all appointments for current user"""
        appointments = self.get_queryset()
        serializer = self.get_serializer(appointments, many=True)
        return Response(serializer.data)


class DoctorListViewSet(viewsets.ViewSet):
    """
    ViewSet for listing available doctors
    """
    permission_classes = [IsAuthenticated]
    
    def list(self, request):
        """Get all verified doctors"""
        doctors = User.objects.filter(
            role='doctor',
            is_active=True,
            doctor_profile__is_verified=True
        ).select_related('doctor_profile')
        
        doctor_list = []
        for doctor in doctors:
            try:
                profile = doctor.doctor_profile
                doctor_list.append({
                    'id': doctor.id,
                    'name': doctor.get_full_name(),
                    'email': doctor.email,
                    'phone_number': doctor.phone_number,
                    'doctor_id': profile.doctor_id,
                    'specialization': profile.get_specialization_display(),
                    'qualifications': profile.qualifications,
                    'experience_years': profile.experience_years,
                    'hospital_affiliation': profile.hospital_affiliation,
                    'consultation_fee': str(profile.consultation_fee),
                    'availability': profile.availability,
                })
            except:
                continue
        
        return Response(doctor_list)


class FHIRDiagnosticReportViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for FHIR Diagnostic Reports (read-only for patients/doctors)
    """
    serializer_class = FHIRDiagnosticReportSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Return FHIR reports based on user role"""
        user = self.request.user
        if user.role == 'patient':
            return FHIRDiagnosticReport.objects.filter(patient=user)
        elif user.role == 'doctor':
            return FHIRDiagnosticReport.objects.filter(doctor=user)
        elif user.role == 'admin':
            return FHIRDiagnosticReport.objects.all()
        return FHIRDiagnosticReport.objects.none()
    
    @action(detail=True, methods=['get'], url_path='fhir-json')
    def get_fhir_json(self, request, pk=None):
        """Get complete FHIR JSON for the report"""
        report = self.get_object()
        return Response(report.fhir_json)
    
    @action(detail=False, methods=['get'], url_path='my-reports')
    def my_reports(self, request):
        """Get all reports for current user"""
        reports = self.get_queryset().order_by('-issued')
        serializer = self.get_serializer(reports, many=True)
        return Response(serializer.data)
