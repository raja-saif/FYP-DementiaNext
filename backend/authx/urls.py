from django.urls import path
from . import views

urlpatterns = [
    path('register', views.register, name='register'),
    path('login', views.login_view, name='login_view'),
    path('auth/verify', views.verify, name='verify'),
    path('auth/google', views.google_login, name='google_login'),
    path('profile', views.get_profile, name='get_profile'),
    path('auth/doctors/', views.list_doctors, name='list_doctors'),
]




