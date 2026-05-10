from django.contrib import admin
from .models import (
    LifeStoryEntry,
    ConversationSession,
    ConversationMessage,
    PatientCompanionConfig,
)


@admin.register(LifeStoryEntry)
class LifeStoryEntryAdmin(admin.ModelAdmin):
    list_display = ["title", "patient", "category", "emotional_valence", "created_at"]
    list_filter = ["category", "emotional_valence"]
    search_fields = ["title", "description", "patient__email"]


@admin.register(ConversationSession)
class ConversationSessionAdmin(admin.ModelAdmin):
    list_display = ["id", "patient", "mode", "message_count", "started_at"]
    list_filter = ["mode", "cognitive_stage_at_time"]
    search_fields = ["patient__email"]


@admin.register(ConversationMessage)
class ConversationMessageAdmin(admin.ModelAdmin):
    list_display = ["id", "session", "role", "timestamp"]
    list_filter = ["role"]


@admin.register(PatientCompanionConfig)
class PatientCompanionConfigAdmin(admin.ModelAdmin):
    list_display = ["patient", "cognitive_stage", "language", "consent_given"]
    list_filter = ["cognitive_stage", "language"]
