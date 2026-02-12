from django.contrib import admin
from .models import DetectionResult, ModelMetadata, Appointment, FHIRDiagnosticReport


@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = ['appointment_id', 'patient', 'doctor', 'appointment_date', 'status', 'created_at']
    list_filter = ['status', 'appointment_date']
    search_fields = ['appointment_id', 'patient__email', 'doctor__email', 'reason']
    readonly_fields = ['appointment_id', 'created_at', 'updated_at']
    
    fieldsets = (
        ('Appointment Info', {'fields': ('appointment_id', 'patient', 'doctor', 'appointment_date', 'status')}),
        ('Details', {'fields': ('reason', 'notes', 'doctor_notes')}),
        ('Timestamps', {'fields': ('created_at', 'updated_at')}),
    )


@admin.register(DetectionResult)
class DetectionResultAdmin(admin.ModelAdmin):
    list_display = ['detection_id', 'patient', 'doctor', 'status', 'predicted_class', 'confidence_score', 'upload_date']
    list_filter = ['status', 'predicted_class', 'upload_date']
    search_fields = ['detection_id', 'patient__email', 'doctor__email', 'notes']
    readonly_fields = ['detection_id', 'predicted_class', 'confidence_score', 'processing_time', 'created_at', 'updated_at']
    
    fieldsets = (
        ('Detection Info', {'fields': ('detection_id', 'appointment', 'patient', 'doctor', 'status')}),
        ('Upload', {'fields': ('uploaded_file', 'file_size', 'upload_date')}),
        ('Patient Info', {'fields': ('patient_age', 'patient_gender', 'notes')}),
        ('Results', {'fields': ('predicted_class', 'confidence_score', 'prediction_probability', 'analysis_details')}),
        ('Processing', {'fields': ('model_version', 'processing_time', 'error_message')}),
        ('Clinical Review', {'fields': ('clinician_notes', 'reviewed_date')}),
        ('Timestamps', {'fields': ('created_at', 'updated_at')}),
    )


@admin.register(FHIRDiagnosticReport)
class FHIRDiagnosticReportAdmin(admin.ModelAdmin):
    list_display = ['report_id', 'patient', 'doctor', 'status', 'hospital_name', 'issued']
    list_filter = ['status', 'department', 'issued']
    search_fields = ['report_id', 'patient__email', 'doctor__email', 'hospital_name']
    readonly_fields = ['report_id', 'fhir_json', 'created_at', 'updated_at']
    
    fieldsets = (
        ('FHIR Info', {'fields': ('report_id', 'fhir_resource_type', 'fhir_version', 'status')}),
        ('Relationships', {'fields': ('detection', 'patient', 'doctor')}),
        ('Hospital', {'fields': ('hospital_name', 'hospital_system_id', 'department')}),
        ('Clinical', {'fields': ('effective_datetime', 'issued', 'conclusion')}),
        ('FHIR Data', {'fields': ('fhir_json',)}),
        ('Timestamps', {'fields': ('created_at', 'updated_at')}),
    )


@admin.register(ModelMetadata)
class ModelMetadataAdmin(admin.ModelAdmin):
    list_display = ['name', 'version', 'architecture', 'accuracy', 'auc_score', 'is_active']
    list_filter = ['is_active', 'trained_on']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Model Info', {'fields': ('name', 'version', 'architecture', 'description')}),
        ('Performance Metrics', {'fields': ('accuracy', 'auc_score', 'sensitivity', 'specificity')}),
        ('Deployment', {'fields': ('model_path', 'is_active', 'trained_on')}),
        ('Timestamps', {'fields': ('created_at', 'updated_at')}),
    )
