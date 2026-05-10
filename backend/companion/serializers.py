from rest_framework import serializers
from .models import (
    LifeStoryEntry,
    ConversationSession,
    ConversationMessage,
    PatientCompanionConfig,
)


class LifeStoryEntrySerializer(serializers.ModelSerializer):
    created_by_name = serializers.SerializerMethodField()
    content = serializers.SerializerMethodField()

    class Meta:
        model = LifeStoryEntry
        fields = [
            "id",
            "patient",
            "category",
            "entry_type",
            "title",
            "description",
            "audio_file",
            "audio_transcript",
            "content",  # Combined content (transcript or description)
            "people_involved",
            "time_period",
            "trigger_questions",
            "emotional_valence",
            "priority",
            "usage_count",
            "last_positive_response",
            "created_by",
            "created_by_name",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "patient",
            "audio_transcript",  # Set by backend after transcription
            "content",
            "usage_count",
            "last_positive_response",
            "created_at",
            "updated_at",
        ]

    def get_created_by_name(self, obj):
        if obj.created_by:
            return obj.created_by.get_full_name() or obj.created_by.email
        return None
    
    def get_content(self, obj):
        return obj.get_content()


class ConversationMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ConversationMessage
        fields = [
            "id",
            "role",
            "content_text",
            "audio_url",
            "timestamp",
            "response_time_ms",
        ]
        read_only_fields = fields


class ConversationSessionSerializer(serializers.ModelSerializer):
    last_message = serializers.SerializerMethodField()

    class Meta:
        model = ConversationSession
        fields = [
            "id",
            "patient",
            "mode",
            "started_at",
            "ended_at",
            "message_count",
            "cognitive_stage_at_time",
            "summary",
            "last_message",
        ]
        read_only_fields = fields

    def get_last_message(self, obj):
        msg = obj.messages.order_by("-timestamp").first()
        if msg:
            return {
                "role": msg.role,
                "content_text": msg.content_text[:100],
                "timestamp": msg.timestamp,
            }
        return None


class PatientCompanionConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = PatientCompanionConfig
        fields = [
            "id",
            "patient",
            "cognitive_stage",
            "stage_last_updated",
            "preferred_voice",
            "life_story_enabled",
            "language",
            "consent_given",
            "consent_date",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "patient",
            "stage_last_updated",
            "created_at",
            "updated_at",
        ]


class ChatRequestSerializer(serializers.Serializer):
    message = serializers.CharField(required=False, allow_blank=True)
    session_id = serializers.IntegerField(required=False)
    mode = serializers.ChoiceField(
        choices=["patient", "caregiver"], default="patient"
    )
    patient_id = serializers.IntegerField(
        required=False,
        help_text="Required for caregiver mode to specify which patient.",
    )


class ChatResponseSerializer(serializers.Serializer):
    reply = serializers.CharField()
    audio_url = serializers.CharField(allow_null=True, required=False)
    session_id = serializers.IntegerField()
    response_time_ms = serializers.IntegerField()
    tts_task_id = serializers.CharField(allow_null=True, required=False)
