from django.urls import path, include
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register(r"chat", views.ChatViewSet, basename="chat")
router.register(r"life-story", views.LifeStoryViewSet, basename="life-story")
router.register(r"sessions", views.SessionViewSet, basename="sessions")
router.register(r"config", views.CompanionConfigViewSet, basename="config")

urlpatterns = [
    path("", include(router.urls)),
]
