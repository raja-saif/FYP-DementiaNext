from rest_framework import serializers
from .models import Appointment, DetectionResult, FHIRDiagnosticReport, ModelMetadata, DoctorReview
from datetime import datetime


class AppointmentSerializer(serializers.ModelSerializer):
    patient_name = serializers.CharField(source='patient.get_full_name', read_only=True)
    doctor_name = serializers.CharField(source='doctor.get_full_name', read_only=True)
    patient_email = serializers.EmailField(source='patient.email', read_only=True)
    doctor_email = serializers.EmailField(source='doctor.email', read_only=True)
    doctor_specialization = serializers.SerializerMethodField()
    
    # Frontend-friendly date/time fields
    scheduled_date = serializers.SerializerMethodField()
    scheduled_time = serializers.SerializerMethodField()
    
    # Nested objects for frontend
    doctor = serializers.SerializerMethodField()
    patient = serializers.SerializerMethodField()
    
    # For creating appointments - make these write_only and not required in serializer
    # They'll be processed in create() method
    doctor_id = serializers.IntegerField(write_only=True, required=False)
    
    # Override model fields to make them optional for create (we set them in create method)
    appointment_date = serializers.DateTimeField(required=False, allow_null=True)
    reason = serializers.CharField(required=False, allow_blank=True, default='General Consultation')
    
    class Meta:
        model = Appointment
        fields = [
            'id', 'appointment_id', 'doctor', 'patient', 'doctor_id',
            'appointment_date', 'scheduled_date', 'scheduled_time',
            'status', 'reason', 'notes', 'doctor_notes',
            'patient_name', 'doctor_name', 'patient_email', 'doctor_email',
            'doctor_specialization', 'created_at', 'updated_at'
        ]
        read_only_fields = ['appointment_id', 'created_at', 'updated_at']
    
    def get_doctor(self, obj):
        if obj.doctor:
            doctor_data = {
                'id': obj.doctor.id,
                'user': {
                    'id': obj.doctor.id,
                    'email': obj.doctor.email,
                    'first_name': obj.doctor.first_name,
                    'last_name': obj.doctor.last_name,
                },
                'specialization': 'General',
            }
            if hasattr(obj.doctor, 'doctor_profile') and obj.doctor.doctor_profile:
                doctor_data['specialization'] = obj.doctor.doctor_profile.specialization
            return doctor_data
        return None
    
    def get_patient(self, obj):
        if obj.patient:
            patient_data = {
                'id': obj.patient.id,
                'user': {
                    'id': obj.patient.id,
                    'email': obj.patient.email,
                    'first_name': obj.patient.first_name,
                    'last_name': obj.patient.last_name,
                },
                'gender': '',
                'date_of_birth': '',
            }
            if hasattr(obj.patient, 'patient_profile') and obj.patient.patient_profile:
                patient_data['gender'] = obj.patient.patient_profile.gender
                if obj.patient.patient_profile.date_of_birth:
                    patient_data['date_of_birth'] = str(obj.patient.patient_profile.date_of_birth)
            return patient_data
        return None
    
    def get_doctor_specialization(self, obj):
        if hasattr(obj.doctor, 'doctor_profile') and obj.doctor.doctor_profile:
            return obj.doctor.doctor_profile.specialization
        return 'General'
    
    def get_scheduled_date(self, obj):
        if obj.appointment_date:
            return obj.appointment_date.strftime('%Y-%m-%d')
        return None
    
    def get_scheduled_time(self, obj):
        if obj.appointment_date:
            return obj.appointment_date.strftime('%H:%M')
        return None
    
    def validate(self, data):
        """Validate appointment data"""
        request = self.context.get('request')
        
        # Get scheduled_date and scheduled_time from request.data or initial_data
        request_data = getattr(request, 'data', {}) if request else {}
        scheduled_date = request_data.get('scheduled_date') or self.initial_data.get('scheduled_date')
        scheduled_time = request_data.get('scheduled_time', '09:00') or self.initial_data.get('scheduled_time', '09:00')
        
        if scheduled_date and scheduled_time:
            try:
                datetime_str = f"{scheduled_date} {scheduled_time}"
                appointment_datetime = datetime.strptime(datetime_str, '%Y-%m-%d %H:%M')
                
                # Check if appointment is in the past
                if appointment_datetime < datetime.now():
                    raise serializers.ValidationError({
                        'scheduled_date': 'Cannot book appointments in the past. Please select a future date and time.'
                    })
            except ValueError as e:
                raise serializers.ValidationError({
                    'scheduled_date': 'Invalid date or time format.'
                })
        
        return data
    
    def create(self, validated_data):
        # Handle scheduled_date and scheduled_time from request or initial_data
        request = self.context.get('request')
        request_data = getattr(request, 'data', {}) if request else {}
        
        # Fall back to initial_data if request.data is empty
        scheduled_date = request_data.get('scheduled_date') or self.initial_data.get('scheduled_date')
        scheduled_time = request_data.get('scheduled_time', '09:00') or self.initial_data.get('scheduled_time', '09:00')
        doctor_id = request_data.get('doctor_id') or self.initial_data.get('doctor_id')
        reason = request_data.get('reason') or self.initial_data.get('reason') or 'General Consultation'
        
        if scheduled_date and scheduled_time:
            datetime_str = f"{scheduled_date} {scheduled_time}"
            validated_data['appointment_date'] = datetime.strptime(datetime_str, '%Y-%m-%d %H:%M')
        elif scheduled_date:
            datetime_str = f"{scheduled_date} 09:00"
            validated_data['appointment_date'] = datetime.strptime(datetime_str, '%Y-%m-%d %H:%M')
        
        if doctor_id:
            from authx.models import User
            try:
                validated_data['doctor'] = User.objects.get(id=doctor_id, role='doctor')
            except User.DoesNotExist:
                raise serializers.ValidationError({'doctor_id': 'Doctor not found.'})
        
        # Set reason with default if not provided
        if 'reason' not in validated_data or not validated_data.get('reason'):
            validated_data['reason'] = reason
        
        # Remove doctor_id from validated_data as it's write_only
        validated_data.pop('doctor_id', None)
        
        return super().create(validated_data)


class DetectionResultSerializer(serializers.ModelSerializer):
    patient_name = serializers.CharField(source='patient.get_full_name', read_only=True)
    patient_email = serializers.EmailField(source='patient.email', read_only=True)
    doctor_name = serializers.CharField(source='doctor.get_full_name', read_only=True)
    appointment_id = serializers.CharField(source='appointment.appointment_id', read_only=True)
    patient_id = serializers.CharField(source='patient.patient_profile.patient_id', read_only=True)
    
    class Meta:
        model = DetectionResult
        fields = '__all__'
        read_only_fields = [
            'detection_id', 'upload_date', 'created_at', 'updated_at',
            'predicted_class', 'confidence_score', 'prediction_probability',
            'processing_time', 'analysis_details', 'patient', 'doctor'
        ]

    # Provide human-friendly display value for the predicted_class choice field
    predicted_class_display = serializers.CharField(source='get_predicted_class_display', read_only=True)
    
    # Custom property to surface review status directly on the detection result
    review_status = serializers.SerializerMethodField()
    
    def get_review_status(self, obj):
        try:
            review = obj.doctor_review
        except DoctorReview.DoesNotExist:
            return 'needs_review'
        return 'sent' if review.is_sent_to_patient else 'draft'


class DetectionUploadSerializer(serializers.ModelSerializer):
    class Meta:
        model = DetectionResult
        fields = [
            'uploaded_file',
            'patient_age',
            'patient_gender',
            'notes',
            'appointment',
        ]
    
    def validate_uploaded_file(self, value):
        """Validate file type - accept images, NIfTI, DICOM, and ZIP of DICOMs"""
        allowed_extensions = [
            '.jpg', '.jpeg', '.png',
            '.nii', '.nii.gz',
            '.dcm',
            '.zip',
        ]
        allowed_mimetypes = [
            'image/jpeg', 'image/png',
            'application/gzip', 'application/octet-stream',
            'application/dicom',
            'application/zip', 'application/x-zip-compressed',
        ]

        file_name = value.name.lower()
        mime_type = value.content_type

        is_valid_extension = any(file_name.endswith(ext) for ext in allowed_extensions)
        is_valid_mimetype = mime_type in allowed_mimetypes

        if not (is_valid_extension or is_valid_mimetype):
            raise serializers.ValidationError(
                "Unsupported file type. Allowed: JPG, PNG, NIfTI (.nii, .nii.gz), "
                f"DICOM (.dcm), ZIP of DICOMs. Got: {file_name}"
            )

        is_large_format = file_name.endswith(('.nii', '.nii.gz', '.dcm', '.zip'))
        max_size = 200 * 1024 * 1024 if is_large_format else 10 * 1024 * 1024
        if value.size > max_size:
            max_mb = max_size / (1024 * 1024)
            raise serializers.ValidationError(
                f"File too large. Maximum size: {max_mb:.0f}MB"
            )

        return value


class FHIRDiagnosticReportSerializer(serializers.ModelSerializer):
    patient_name = serializers.CharField(source='patient.get_full_name', read_only=True)
    doctor_name = serializers.CharField(source='doctor.get_full_name', read_only=True)
    detection_id = serializers.CharField(source='detection.detection_id', read_only=True)
    patient_id = serializers.CharField(source='patient.patient_profile.patient_id', read_only=True)
    
    class Meta:
        model = FHIRDiagnosticReport
        fields = '__all__'
        read_only_fields = ['report_id', 'fhir_json', 'created_at', 'updated_at']


class ModelMetadataSerializer(serializers.ModelSerializer):
    class Meta:
        model = ModelMetadata
        fields = '__all__'
        read_only_fields = ['id']


class DoctorReviewSerializer(serializers.ModelSerializer):
    """Full review serializer for doctors — includes internal notes."""
    patient_name = serializers.CharField(source='patient.get_full_name', read_only=True)
    patient_email = serializers.EmailField(source='patient.email', read_only=True)
    doctor_name = serializers.CharField(source='doctor.get_full_name', read_only=True)
    detection_id = serializers.CharField(source='detection.detection_id', read_only=True)
    predicted_class = serializers.CharField(source='detection.predicted_class', read_only=True)
    predicted_class_display = serializers.CharField(source='detection.get_predicted_class_display', read_only=True)
    confidence_score = serializers.FloatField(source='detection.confidence_score', read_only=True)

    class Meta:
        model = DoctorReview
        fields = [
            'id', 'detection', 'detection_id',
            'predicted_class', 'predicted_class_display', 'confidence_score',
            'doctor', 'patient',
            'patient_name', 'patient_email', 'doctor_name',
            'ai_accepted', 'doctor_override_class', 'doctor_conclusion', 'doctor_notes', 'patient_summary',
            'is_sent_to_patient', 'sent_at',
            'created_at', 'updated_at',
        ]
        read_only_fields = [
            'id', 'detection_id', 'doctor', 'patient',
            'patient_name', 'patient_email', 'doctor_name',
            'predicted_class', 'predicted_class_display', 'confidence_score',
            'sent_at', 'created_at', 'updated_at',
        ]


class PatientVisibleReviewSerializer(serializers.ModelSerializer):
    """Patient-facing serializer — excludes internal doctor_notes."""
    doctor_name = serializers.CharField(source='doctor.get_full_name', read_only=True)
    detection_id = serializers.CharField(source='detection.detection_id', read_only=True)
    predicted_class = serializers.CharField(source='detection.predicted_class', read_only=True)
    predicted_class_display = serializers.CharField(source='detection.get_predicted_class_display', read_only=True)
    confidence_score = serializers.FloatField(source='detection.confidence_score', read_only=True)
    model_type = serializers.CharField(source='detection.model_type', read_only=True)
    processing_time = serializers.FloatField(source='detection.processing_time', read_only=True)
    has_fhir_report = serializers.SerializerMethodField()
    fhir_report_id = serializers.SerializerMethodField()

    class Meta:
        model = DoctorReview
        fields = [
            'id', 'detection_id',
            'doctor_name',
            'ai_accepted', 'doctor_override_class', 'doctor_conclusion', 'patient_summary',
            'predicted_class', 'predicted_class_display', 'confidence_score',
            'model_type', 'processing_time',
            'has_fhir_report', 'fhir_report_id',
            'sent_at', 'created_at',
        ]
        read_only_fields = fields

    def get_has_fhir_report(self, obj):
        return hasattr(obj.detection, 'fhir_report')

    def get_fhir_report_id(self, obj):
        try:
            return obj.detection.fhir_report.id
        except Exception:
            return None
