from django.db import models
from django.conf import settings
import json
from datetime import datetime


class Appointment(models.Model):
    """Appointment booking between patient and doctor"""
    
    STATUS_CHOICES = [
        ('pending', 'Pending Approval'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]
    
    appointment_id = models.CharField(max_length=30, unique=True, editable=False, blank=True)
    patient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='patient_appointments')
    doctor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='doctor_appointments')
    appointment_date = models.DateTimeField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    reason = models.TextField()
    notes = models.TextField(blank=True, null=True)
    doctor_notes = models.TextField(blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-appointment_date']
        indexes = [
            models.Index(fields=['patient', 'status']),
            models.Index(fields=['doctor', 'status']),
            models.Index(fields=['appointment_date']),
        ]
    
    def save(self, *args, **kwargs):
        if not self.appointment_id:
            import time
            import random
            self.appointment_id = f"APT{int(time.time())}{random.randint(1000, 9999)}"
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.appointment_id} - {self.patient.get_full_name()} with Dr. {self.doctor.get_full_name()}"


class DetectionResult(models.Model):
    DISEASE_CHOICES = [
        ('alzheimers', "Alzheimer's Disease"),
        ('cn', 'Control/Normal'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]

    detection_id = models.CharField(max_length=30, unique=True, editable=False, blank=True)
    appointment = models.ForeignKey(Appointment, on_delete=models.CASCADE, related_name='detections', null=True, blank=True)
    patient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='patient_detections')
    doctor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='doctor_detections', null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # Input data
    uploaded_file = models.FileField(upload_to='mri_uploads/%Y/%m/%d/')
    file_size = models.IntegerField()  # in bytes
    upload_date = models.DateTimeField(auto_now_add=True)
    
    # Results
    # Store the choice key (e.g. 'alzheimers'/'cn') to enable get_predicted_class_display()
    predicted_class = models.CharField(max_length=50, choices=DISEASE_CHOICES, null=True, blank=True)
    confidence_score = models.FloatField(null=True, blank=True)  # 0-1
    prediction_probability = models.JSONField(null=True, blank=True)  # Store all class probabilities
    
    # Model metadata
    model_version = models.CharField(max_length=50, default='v1.0')
    processing_time = models.FloatField(null=True, blank=True)  # in seconds
    
    # Additional analysis
    analysis_details = models.JSONField(null=True, blank=True)  # Store detailed analysis
    error_message = models.TextField(null=True, blank=True)
    
    # Patient info
    patient_age = models.IntegerField(null=True, blank=True)
    patient_gender = models.CharField(max_length=10, null=True, blank=True)
    notes = models.TextField(null=True, blank=True)
    
    # Clinical follow-up
    clinician_notes = models.TextField(null=True, blank=True)
    reviewed_date = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['patient', '-created_at']),
            models.Index(fields=['doctor', '-created_at']),
            models.Index(fields=['appointment']),
            models.Index(fields=['status']),
        ]
    
    def save(self, *args, **kwargs):
        if not self.detection_id:
            import time
            import random
            self.detection_id = f"DET{int(time.time())}{random.randint(1000, 9999)}"
        super().save(*args, **kwargs)

    def __str__(self):
        # Use the human-readable label when possible
        if self.predicted_class:
            try:
                display_label = self.get_predicted_class_display()
            except Exception:
                display_label = self.predicted_class
            return f"{self.detection_id} - {display_label} ({self.confidence_score:.2%})"
        return f"{self.detection_id} - Pending"


class FHIRDiagnosticReport(models.Model):
    """HL7 FHIR-compliant Diagnostic Report for hospital integration"""
    
    STATUS_CHOICES = [
        ('registered', 'Registered'),
        ('partial', 'Partial'),
        ('preliminary', 'Preliminary'),
        ('final', 'Final'),
        ('amended', 'Amended'),
        ('corrected', 'Corrected'),
        ('cancelled', 'Cancelled'),
    ]
    
    # FHIR Resource identifiers
    report_id = models.CharField(max_length=50, unique=True, editable=False, blank=True)
    fhir_resource_type = models.CharField(max_length=50, default='DiagnosticReport')
    fhir_version = models.CharField(max_length=10, default='4.0.1')
    
    # Relationships
    detection = models.OneToOneField(DetectionResult, on_delete=models.CASCADE, related_name='fhir_report')
    patient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='fhir_reports_patient')
    doctor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='fhir_reports_doctor')
    
    # FHIR Standard Fields
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='final')
    category = models.JSONField(default=dict)  # Diagnostic service category
    code = models.JSONField(default=dict)  # Type of diagnostic report (LOINC/SNOMED)
    subject = models.JSONField(default=dict)  # Patient reference
    encounter = models.JSONField(null=True, blank=True)  # Encounter reference
    effective_datetime = models.DateTimeField()  # Clinically relevant time
    issued = models.DateTimeField(auto_now_add=True)  # Report release time
    performer = models.JSONField(default=list)  # Responsible diagnostic service
    
    # Results and Observations
    result = models.JSONField(default=list)  # Observations (FHIR Observation references)
    imaging_study = models.JSONField(null=True, blank=True)  # ImagingStudy reference
    media = models.JSONField(default=list)  # Key images
    conclusion = models.TextField()  # Clinical interpretation
    conclusion_code = models.JSONField(default=list)  # Coded conclusions (SNOMED CT)
    
    # Presentation
    presented_form = models.JSONField(default=list)  # Entire report as attachment
    
    # Hospital Integration
    hospital_system_id = models.CharField(max_length=100, blank=True, null=True)
    hospital_name = models.CharField(max_length=200)
    department = models.CharField(max_length=100, default='Neurology')
    
    # Metadata
    fhir_json = models.JSONField(default=dict)  # Complete FHIR JSON representation
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-issued']
        indexes = [
            models.Index(fields=['report_id']),
            models.Index(fields=['patient', '-issued']),
            models.Index(fields=['doctor', '-issued']),
            models.Index(fields=['status']),
        ]
    
    def save(self, *args, **kwargs):
        if not self.report_id:
            import time
            import random
            self.report_id = f"FHIR-DR-{int(time.time())}-{random.randint(1000, 9999)}"
        
        # Auto-generate FHIR JSON before saving
        if not self.fhir_json or self.pk is None:
            self.generate_fhir_json()
        
        super().save(*args, **kwargs)
    
    def generate_fhir_json(self):
        """Generate HL7 FHIR R4 compliant DiagnosticReport JSON"""
        
        # Handle None datetime fields with fallback to current time
        effective_dt = self.effective_datetime or datetime.now()
        issued_dt = self.issued or datetime.now()
        
        # Get patient and doctor profiles
        try:
            patient_profile = self.patient.patient_profile
            patient_id = patient_profile.patient_id
        except:
            patient_id = f"P{self.patient.id}"
        
        try:
            doctor_profile = self.doctor.doctor_profile
            doctor_id = doctor_profile.doctor_id
        except:
            doctor_id = f"D{self.doctor.id}"
        
        # Build encounter reference only if appointment exists
        encounter_ref = None
        if self.detection.appointment:
            encounter_ref = {
                "reference": f"Encounter/{self.detection.appointment.appointment_id}",
                "display": f"Appointment on {self.detection.appointment.appointment_date.strftime('%Y-%m-%d')}"
            }
        
        self.fhir_json = {
            "resourceType": "DiagnosticReport",
            "id": self.report_id,
            "meta": {
                "versionId": "1",
                "lastUpdated": datetime.now().isoformat(),
                "profile": [
                    "http://hl7.org/fhir/StructureDefinition/DiagnosticReport"
                ]
            },
            "identifier": [
                {
                    "use": "official",
                    "system": f"http://dementianext.com/fhir/DiagnosticReport",
                    "value": self.report_id
                }
            ],
            "status": self.status,
            "category": [
                {
                    "coding": [
                        {
                            "system": "http://terminology.hl7.org/CodeSystem/v2-0074",
                            "code": "RAD",
                            "display": "Radiology"
                        },
                        {
                            "system": "http://terminology.hl7.org/CodeSystem/v2-0074",
                            "code": "NMS",
                            "display": "Nuclear Medicine Scan"
                        }
                    ],
                    "text": "Neurological Imaging"
                }
            ],
            "code": {
                "coding": [
                    {
                        "system": "http://loinc.org",
                        "code": "24604-1",
                        "display": "MRI Brain"
                    },
                    {
                        "system": "http://snomed.info/sct",
                        "code": "448761000",
                        "display": "Alzheimer disease detection by imaging"
                    }
                ],
                "text": "Alzheimer's Disease Detection - MRI Brain Analysis"
            },
            "subject": {
                "reference": f"Patient/{patient_id}",
                "display": self.patient.get_full_name() or self.patient.email
            },
            "encounter": encounter_ref,
            "effectiveDateTime": effective_dt.isoformat(),
            "issued": issued_dt.isoformat(),
            "performer": [
                {
                    "reference": f"Practitioner/{doctor_id}",
                    "display": f"Dr. {self.doctor.get_full_name()}",
                    "role": {
                        "coding": [
                            {
                                "system": "http://terminology.hl7.org/CodeSystem/v2-0912",
                                "code": "OP",
                                "display": "Ordering Provider"
                            }
                        ]
                    }
                }
            ],
            "result": [
                {
                    "reference": f"Observation/{self.detection.detection_id}-prediction",
                    "display": "Alzheimer's Disease Detection Result"
                },
                {
                    "reference": f"Observation/{self.detection.detection_id}-confidence",
                    "display": "Prediction Confidence Score"
                }
            ],
            "imagingStudy": [
                {
                    "reference": f"ImagingStudy/{self.detection.detection_id}",
                    "display": "Brain MRI Study"
                }
            ],
            "conclusion": self.conclusion,
            "conclusionCode": self.conclusion_code if self.conclusion_code else [
                {
                    "coding": [
                        {
                            "system": "http://snomed.info/sct",
                            "code": "26929004" if self.detection.predicted_class == 'alzheimers' else "17886001",
                            "display": "Alzheimer's disease" if self.detection.predicted_class == 'alzheimers' else "Normal cognition"
                        }
                    ]
                }
            ],
            "presentedForm": [
                {
                    "contentType": "application/pdf",
                    "language": "en-US",
                    "title": f"Alzheimer's Detection Report - {self.report_id}",
                    "creation": issued_dt.isoformat()
                }
            ]
        }
        
        # Add observations data
        self.result = [
            {
                "resourceType": "Observation",
                "id": f"{self.detection.detection_id}-prediction",
                "status": "final",
                "category": [
                    {
                        "coding": [
                            {
                                "system": "http://terminology.hl7.org/CodeSystem/observation-category",
                                "code": "imaging",
                                "display": "Imaging"
                            }
                        ]
                    }
                ],
                "code": {
                    "coding": [
                        {
                            "system": "http://loinc.org",
                            "code": "89208-8",
                            "display": "Alzheimer disease [Interpretation]"
                        }
                    ],
                    "text": "Alzheimer's Disease Detection"
                },
                "subject": {
                    "reference": f"Patient/{patient_id}"
                },
                "effectiveDateTime": effective_dt.isoformat(),
                "valueCodeableConcept": {
                    "coding": [
                        {
                            "system": "http://snomed.info/sct",
                            "code": "26929004" if self.detection.predicted_class == 'alzheimers' else "17886001",
                            "display": "Alzheimer's disease" if self.detection.predicted_class == 'alzheimers' else "Normal cognition"
                        }
                    ],
                    "text": self.detection.get_predicted_class_display() if self.detection.predicted_class else "Pending"
                }
            },
            {
                "resourceType": "Observation",
                "id": f"{self.detection.detection_id}-confidence",
                "status": "final",
                "category": [
                    {
                        "coding": [
                            {
                                "system": "http://terminology.hl7.org/CodeSystem/observation-category",
                                "code": "imaging",
                                "display": "Imaging"
                            }
                        ]
                    }
                ],
                "code": {
                    "coding": [
                        {
                            "system": "http://loinc.org",
                            "code": "89202-1",
                            "display": "Probability score"
                        }
                    ],
                    "text": "Prediction Confidence Score"
                },
                "subject": {
                    "reference": f"Patient/{patient_id}"
                },
                "effectiveDateTime": effective_dt.isoformat(),
                "valueQuantity": {
                    "value": self.detection.confidence_score * 100 if self.detection.confidence_score else 0,
                    "unit": "%",
                    "system": "http://unitsofmeasure.org",
                    "code": "%"
                }
            }
        ]
    
    def __str__(self):
        return f"FHIR Report {self.report_id} - {self.patient.get_full_name()}"


class ModelMetadata(models.Model):
    """Store information about deployed models"""
    name = models.CharField(max_length=100)
    version = models.CharField(max_length=50)
    architecture = models.CharField(max_length=50)  # e.g., "ResNet-34"
    accuracy = models.FloatField()
    auc_score = models.FloatField()
    sensitivity = models.FloatField()  # Recall for positive class
    specificity = models.FloatField()
    trained_on = models.DateField()
    is_active = models.BooleanField(default=True)
    model_path = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} v{self.version}"

