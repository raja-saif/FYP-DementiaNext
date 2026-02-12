from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, PatientProfile, DoctorProfile


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ['email', 'get_full_name', 'role', 'is_staff', 'is_active', 'date_joined']
    list_filter = ['role', 'is_staff', 'is_active']
    search_fields = ['email', 'first_name', 'last_name']
    ordering = ['-date_joined']
    
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Personal Info', {'fields': ('first_name', 'last_name', 'phone_number')}),
        ('Role', {'fields': ('role',)}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'password1', 'password2', 'role', 'first_name', 'last_name'),
        }),
    )


@admin.register(PatientProfile)
class PatientProfileAdmin(admin.ModelAdmin):
    list_display = ['patient_id', 'user', 'gender', 'date_of_birth', 'blood_group', 'created_at']
    list_filter = ['gender', 'blood_group']
    search_fields = ['patient_id', 'user__email', 'user__first_name', 'user__last_name']
    readonly_fields = ['patient_id', 'created_at', 'updated_at']
    
    fieldsets = (
        ('Patient Info', {'fields': ('patient_id', 'user')}),
        ('Demographics', {'fields': ('date_of_birth', 'gender', 'blood_group')}),
        ('Contact', {'fields': ('address', 'emergency_contact')}),
        ('Medical', {'fields': ('medical_history', 'allergies', 'current_medications')}),
        ('Timestamps', {'fields': ('created_at', 'updated_at')}),
    )


@admin.register(DoctorProfile)
class DoctorProfileAdmin(admin.ModelAdmin):
    list_display = ['doctor_id', 'user', 'specialization', 'license_number', 'hospital_affiliation', 'is_verified', 'created_at']
    list_filter = ['specialization', 'is_verified']
    search_fields = ['doctor_id', 'user__email', 'user__first_name', 'user__last_name', 'license_number']
    readonly_fields = ['doctor_id', 'created_at', 'updated_at']
    
    fieldsets = (
        ('Doctor Info', {'fields': ('doctor_id', 'user', 'license_number', 'is_verified')}),
        ('Professional', {'fields': ('specialization', 'qualifications', 'experience_years')}),
        ('Hospital', {'fields': ('hospital_affiliation', 'consultation_fee')}),
        ('Availability', {'fields': ('available_days', 'available_time_start', 'available_time_end')}),
        ('Bio', {'fields': ('bio',)}),
        ('Timestamps', {'fields': ('created_at', 'updated_at')}),
    )

