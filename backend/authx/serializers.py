from rest_framework import serializers
from .models import User, PatientProfile, DoctorProfile


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'email', 'first_name', 'last_name', 'role', 'phone_number', 'is_active']
        read_only_fields = ['id']


class PatientProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    user_id = serializers.IntegerField(write_only=True, required=False)
    
    class Meta:
        model = PatientProfile
        fields = '__all__'
        read_only_fields = ['patient_id', 'created_at', 'updated_at']


class DoctorProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    user_id = serializers.IntegerField(write_only=True, required=False)
    
    class Meta:
        model = DoctorProfile
        fields = '__all__'
        read_only_fields = ['doctor_id', 'created_at', 'updated_at', 'is_verified']


class RegisterSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)
    password = serializers.CharField(write_only=True, required=True, min_length=8)
    first_name = serializers.CharField(required=True, max_length=150)
    last_name = serializers.CharField(required=True, max_length=150)
    role = serializers.ChoiceField(choices=['patient', 'doctor'], required=True)
    phone_number = serializers.CharField(required=False, max_length=15, allow_blank=True)
    
    # Patient fields
    date_of_birth = serializers.DateField(required=False)
    gender = serializers.ChoiceField(choices=['M', 'F', 'O'], required=False)
    blood_group = serializers.ChoiceField(
        choices=['A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-'],
        required=False,
        allow_blank=True
    )
    address = serializers.CharField(required=False, allow_blank=True)
    emergency_contact = serializers.CharField(required=False, max_length=15, allow_blank=True)
    
    # Doctor fields
    license_number = serializers.CharField(required=False, max_length=50)
    specialization = serializers.ChoiceField(
        choices=['neurology', 'radiology', 'psychiatry', 'geriatrics', 'general'],
        required=False
    )
    qualifications = serializers.CharField(required=False, allow_blank=True)
    experience_years = serializers.IntegerField(required=False)
    hospital_affiliation = serializers.CharField(required=False, max_length=200)
    consultation_fee = serializers.DecimalField(
        required=False,
        max_digits=10,
        decimal_places=2,
        default=0
    )
    
    def validate_email(self, value):
        if User.objects.filter(email=value.lower()).exists():
            raise serializers.ValidationError("User with this email already exists.")
        return value.lower()
    
    def validate(self, data):
        role = data.get('role')
        
        if role == 'patient':
            required_fields = ['date_of_birth', 'gender']
            missing = [field for field in required_fields if not data.get(field)]
            if missing:
                raise serializers.ValidationError({
                    field: "This field is required for patient registration."
                    for field in missing
                })
        
        elif role == 'doctor':
            required_fields = ['license_number', 'specialization', 'qualifications', 
                             'experience_years', 'hospital_affiliation']
            missing = [field for field in required_fields if not data.get(field)]
            if missing:
                raise serializers.ValidationError({
                    field: "This field is required for doctor registration."
                    for field in missing
                })
        
        return data
    
    def create(self, validated_data):
        role = validated_data.pop('role')
        
        # Create user
        user = User.objects.create_user(
            email=validated_data.pop('email'),
            password=validated_data.pop('password'),
            first_name=validated_data.pop('first_name'),
            last_name=validated_data.pop('last_name'),
            role=role,
            phone_number=validated_data.pop('phone_number', '')
        )
        
        # Create profile based on role
        if role == 'patient':
            PatientProfile.objects.create(
                user=user,
                date_of_birth=validated_data.pop('date_of_birth'),
                gender=validated_data.pop('gender'),
                blood_group=validated_data.pop('blood_group', ''),
                address=validated_data.pop('address', ''),
                emergency_contact=validated_data.pop('emergency_contact', '')
            )
        elif role == 'doctor':
            DoctorProfile.objects.create(
                user=user,
                license_number=validated_data.pop('license_number'),
                specialization=validated_data.pop('specialization'),
                qualifications=validated_data.pop('qualifications'),
                experience_years=validated_data.pop('experience_years'),
                hospital_affiliation=validated_data.pop('hospital_affiliation'),
                consultation_fee=validated_data.pop('consultation_fee', 0)
            )
        
        return user


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)
    password = serializers.CharField(write_only=True, required=True)
