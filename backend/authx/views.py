from django.contrib.auth import authenticate
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework import status
from rest_framework_simplejwt.tokens import AccessToken
from allauth.socialaccount.models import SocialAccount
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
import json
import os
from .models import User, PatientProfile, DoctorProfile
from .serializers import (
    RegisterSerializer, LoginSerializer, UserSerializer,
    PatientProfileSerializer, DoctorProfileSerializer
)


def issue_token(user):
    token = AccessToken.for_user(user)
    token['role'] = user.role
    token['name'] = user.get_full_name() or user.email
    token['email'] = user.email
    return str(token)


def make_user_payload(user):
    payload = {
        'id': str(user.id),
        'email': user.email,
        'name': user.get_full_name(),
        'first_name': user.first_name,
        'last_name': user.last_name,
        'role': user.role,
        'phone_number': user.phone_number,
    }
    
    # Add profile data
    if user.role == 'patient' and hasattr(user, 'patient_profile'):
        payload['profile'] = PatientProfileSerializer(user.patient_profile).data
    elif user.role == 'doctor' and hasattr(user, 'doctor_profile'):
        payload['profile'] = DoctorProfileSerializer(user.doctor_profile).data
    
    return payload


@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny])
def register(request):
    serializer = RegisterSerializer(data=request.data)
    if serializer.is_valid():
        user = serializer.save()
        token = issue_token(user)
        return Response({
            'token': token,
            'user': make_user_payload(user)
        }, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny])
def login_view(request):
    serializer = LoginSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    email = serializer.validated_data['email'].lower()
    password = serializer.validated_data['password']
    
    try:
        user = User.objects.get(email=email)
    except User.DoesNotExist:
        return Response({'error': 'Invalid credentials'}, status=status.HTTP_401_UNAUTHORIZED)
    
    if not user.check_password(password):
        return Response({'error': 'Invalid credentials'}, status=status.HTTP_401_UNAUTHORIZED)
    
    if not user.is_active:
        return Response({'error': 'Account is deactivated'}, status=status.HTTP_401_UNAUTHORIZED)
    
    token = issue_token(user)
    return Response({
        'token': token,
        'user': make_user_payload(user)
    })


@csrf_exempt
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def verify(request):
    user = request.user
    return Response({'user': make_user_payload(user)})


@csrf_exempt
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_profile(request):
    user = request.user
    return Response({'user': make_user_payload(user)})


@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny])
def google_login(request):
    """
    Handle Google OAuth login - SIMPLIFIED VERSION.
    Frontend verifies with Google and sends user info directly.
    Expects: { "email": "user@email.com", "name": "User Name", "google_id": "123", "role": "patient|doctor" }
    Returns: { "token": "jwt_token", "user": {...} }
    """
    data = request.data if hasattr(request, 'data') else json.loads(request.body)
    email = data.get('email')
    name = data.get('name', '')
    google_id = data.get('google_id')
    role = data.get('role', 'patient')
    
    if not email:
        return Response({'error': 'Email is required'}, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        # Find or create user
        user, created = User.objects.get_or_create(
            email=email.lower(),
            defaults={
                'first_name': name.split()[0] if name else '',
                'last_name': ' '.join(name.split()[1:]) if name and len(name.split()) > 1 else '',
                'role': role,
            }
        )
        
        # If user exists, update name if provided
        if not created and name and not user.first_name:
            user.first_name = name.split()[0] if name else ''
            user.last_name = ' '.join(name.split()[1:]) if name and len(name.split()) > 1 else ''
            user.save()
        
        # Create or update social account link if google_id provided
        if google_id:
            SocialAccount.objects.get_or_create(
                user=user,
                provider='google',
                defaults={'uid': str(google_id)}
            )
        
        # Issue JWT token
        token = issue_token(user)
        return Response({
            'token': token,
            'user': make_user_payload(user)
        })
        
    except Exception as e:
        return Response({'error': f'Google login failed: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@csrf_exempt
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_doctors(request):
    """Get all available doctors with their profiles"""
    doctors = User.objects.filter(role='doctor', is_active=True)
    
    doctors_list = []
    for doctor in doctors:
        doctor_data = {
            'id': doctor.id,
            'user': {
                'id': doctor.id,
                'email': doctor.email,
                'first_name': doctor.first_name,
                'last_name': doctor.last_name,
            }
        }
        
        # Add profile data if exists
        if hasattr(doctor, 'doctor_profile'):
            profile = doctor.doctor_profile
            doctor_data.update({
                'specialization': profile.specialization,
                'qualifications': profile.qualifications,
                'experience_years': profile.experience_years,
                'consultation_fee': str(profile.consultation_fee) if profile.consultation_fee else '0.00',
            })
        else:
            doctor_data.update({
                'specialization': 'General',
                'qualifications': '',
                'experience_years': 0,
                'consultation_fee': '0.00',
            })
        
        doctors_list.append(doctor_data)
    
    return Response(doctors_list)
