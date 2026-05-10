from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.http import StreamingHttpResponse
from django.utils import timezone
import json
import logging

from .models import (
    LifeStoryEntry,
    ConversationSession,
    ConversationMessage,
    PatientCompanionConfig,
)
from .serializers import (
    LifeStoryEntrySerializer,
    ConversationSessionSerializer,
    ConversationMessageSerializer,
    PatientCompanionConfigSerializer,
    ChatRequestSerializer,
    ChatResponseSerializer,
)
from . import conversation_engine, tts_service

logger = logging.getLogger(__name__)


class ChatViewSet(viewsets.ViewSet):
    permission_classes = [permissions.IsAuthenticated]

    def _get_patient_and_session(self, request, data):
        """
        Common logic to resolve patient and session from request data.
        Returns (patient, session, config, error_response).
        If error_response is not None, return it immediately.
        """
        mode = data.get("mode", "patient")
        session_id = data.get("session_id")
        patient_id = data.get("patient_id")

        if mode == "patient":
            if request.user.role != "patient":
                return None, None, None, Response(
                    {"error": "Patient mode requires a patient account."},
                    status=status.HTTP_403_FORBIDDEN,
                )
            patient = request.user
        else:
            # Caregiver mode - if user is a patient, they can use caregiver mode for themselves
            if request.user.role == "patient":
                # Patient using caregiver mode for themselves (no patient_id needed)
                patient = request.user
            elif patient_id:
                # Doctor/caregiver accessing a specific patient
                from django.contrib.auth import get_user_model
                User = get_user_model()
                try:
                    patient = User.objects.get(pk=patient_id, role="patient")
                except User.DoesNotExist:
                    return None, None, None, Response(
                        {"error": "Patient not found."},
                        status=status.HTTP_404_NOT_FOUND,
                    )
            else:
                return None, None, None, Response(
                    {"error": "patient_id is required for caregiver mode."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        config, _ = PatientCompanionConfig.objects.get_or_create(
            patient=patient,
            defaults={"cognitive_stage": "mild"},
        )

        session = None
        if session_id:
            try:
                session = ConversationSession.objects.get(
                    pk=session_id, patient=patient
                )
            except ConversationSession.DoesNotExist:
                pass

        if session is None:
            session = ConversationSession.objects.create(
                patient=patient,
                mode=mode,
                cognitive_stage_at_time=config.cognitive_stage,
            )

        return patient, session, config, None

    @action(detail=False, methods=["post"], url_path="send")
    def send_message(self, request):
        """Original non-streaming endpoint (kept for backwards compatibility)."""
        serializer = ChatRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        mode = data.get("mode", "patient")
        message_text = data.get("message", "")

        # Handle audio upload
        audio_file = request.FILES.get("audio")
        if audio_file and not message_text:
            try:
                message_text = conversation_engine.transcribe_audio(audio_file)
                
                # Validate transcription - reject empty or too short transcriptions
                if not message_text or len(message_text.strip()) < 3:
                    return Response(
                        {"error": "Could not understand the audio. Please try speaking more clearly or type your message."},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
            except Exception as e:
                return Response(
                    {"error": f"Transcription failed: {str(e)}"},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )

        if not message_text:
            return Response(
                {"error": "No message or audio provided."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        patient, session, config, error_response = self._get_patient_and_session(request, data)
        if error_response:
            return error_response

        try:
            reply, response_time_ms = conversation_engine.chat(
                patient=patient,
                session=session,
                user_text=message_text,
                mode=mode,
                cognitive_stage=config.cognitive_stage,
            )
        except ValueError as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        except Exception as e:
            return Response(
                {"error": f"Chat failed: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        # Generate TTS asynchronously for patient mode
        audio_url = None
        tts_task_id = None
        if mode == "patient":
            # Start async TTS - don't block response
            tts_task_id = tts_service.generate_tts_async(reply, voice=config.preferred_voice)

        response_data = {
            "reply": reply,
            "audio_url": audio_url,  # Will be None initially for async TTS
            "session_id": session.pk,
            "response_time_ms": response_time_ms,
            "tts_task_id": tts_task_id,  # Client can poll for audio
        }

        return Response(response_data)

    @action(detail=False, methods=["post"], url_path="send-stream")
    def send_message_stream(self, request):
        """
        Streaming endpoint using Server-Sent Events (SSE).
        Returns text chunks as they arrive from the LLM.
        
        Events format:
          data: {"type": "chunk", "content": "Hello"}
          data: {"type": "done", "content": "full reply", "session_id": 123, "response_time_ms": 1234, "tts_task_id": "abc123"}
          data: {"type": "faq_hit", "content": "cached answer", "session_id": 123, "response_time_ms": 0}
          data: {"type": "error", "message": "error details"}
        """
        serializer = ChatRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        mode = data.get("mode", "patient")
        message_text = data.get("message", "")
        transcribed_text = None  # Track if we transcribed audio

        # Handle audio upload
        audio_file = request.FILES.get("audio")
        if audio_file and not message_text:
            try:
                message_text = conversation_engine.transcribe_audio(audio_file)
                transcribed_text = message_text  # Store for sending to frontend
                
                # Validate transcription - reject empty or too short transcriptions
                if not message_text or len(message_text.strip()) < 3:
                    return Response(
                        {"error": "Could not understand the audio. Please try speaking more clearly or type your message."},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
            except Exception as e:
                return Response(
                    {"error": f"Transcription failed: {str(e)}"},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )

        if not message_text:
            return Response(
                {"error": "No message or audio provided."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        patient, session, config, error_response = self._get_patient_and_session(request, data)
        if error_response:
            return error_response

        def event_stream():
            try:
                # If audio was transcribed, send transcription first
                if transcribed_text:
                    transcription_data = json.dumps({
                        "type": "transcription", 
                        "content": transcribed_text
                    })
                    yield f"data: {transcription_data}\n\n"
                
                full_reply = ""
                for event in conversation_engine.chat_stream(
                    patient=patient,
                    session=session,
                    user_text=message_text,
                    mode=mode,
                    cognitive_stage=config.cognitive_stage,
                ):
                    if event["type"] == "chunk":
                        full_reply += event["content"]
                        # Yield SSE formatted data with explicit flush marker
                        data = json.dumps({"type": "chunk", "content": event["content"]})
                        yield f"data: {data}\n\n"
                    
                    elif event["type"] == "faq_hit":
                        # FAQ hit - return full response immediately
                        full_reply = event["content"]
                        tts_task_id = None
                        if mode == "patient":
                            tts_task_id = tts_service.generate_tts_async(
                                full_reply, voice=config.preferred_voice
                            )
                        data = json.dumps({
                            "type": "faq_hit",
                            "content": full_reply,
                            "session_id": session.pk,
                            "response_time_ms": 0,
                            "tts_task_id": tts_task_id,
                        })
                        yield f"data: {data}\n\n"
                    
                    elif event["type"] == "done":
                        # Start async TTS for patient mode
                        tts_task_id = None
                        if mode == "patient":
                            tts_task_id = tts_service.generate_tts_async(
                                event["content"], voice=config.preferred_voice
                            )
                        data = json.dumps({
                            "type": "done",
                            "content": event["content"],
                            "session_id": session.pk,
                            "response_time_ms": event["response_time_ms"],
                            "tts_task_id": tts_task_id,
                        })
                        yield f"data: {data}\n\n"

            except ValueError as e:
                yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
            except Exception as e:
                import traceback
                error_msg = f"Chat failed: {str(e)}"
                logger.exception("Streaming chat error")
                yield f"data: {json.dumps({'type': 'error', 'message': error_msg})}\n\n"

        response = StreamingHttpResponse(
            streaming_content=event_stream(),
            content_type='text/event-stream; charset=utf-8'
        )
        response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response['X-Accel-Buffering'] = 'no'  # Disable nginx buffering
        return response

    @action(detail=False, methods=["get"], url_path="tts-status/(?P<task_id>[^/]+)")
    def tts_status(self, request, task_id=None):
        """Poll for TTS generation status."""
        if not task_id:
            return Response(
                {"error": "task_id required"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        
        status_info = tts_service.get_tts_status(task_id)
        if status_info is None:
            return Response(
                {"error": "Task not found"},
                status=status.HTTP_404_NOT_FOUND,
            )
        
        # If completed, clean up the task
        if status_info["status"] == "completed":
            tts_service.cleanup_tts_task(task_id)
        
        return Response(status_info)

    @action(detail=False, methods=["post"], url_path="transcribe")
    def transcribe(self, request):
        audio_file = request.FILES.get("audio")
        if not audio_file:
            return Response(
                {"error": "No audio file provided."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            text = conversation_engine.transcribe_audio(audio_file)
            return Response({"text": text})
        except Exception as e:
            return Response(
                {"error": f"Transcription failed: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class LifeStoryViewSet(viewsets.ModelViewSet):
    serializer_class = LifeStoryEntrySerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        patient_id = self.request.query_params.get("patient_id")

        if patient_id and user.role in ("doctor", "admin"):
            return LifeStoryEntry.objects.filter(patient_id=patient_id)

        if user.role == "patient":
            return LifeStoryEntry.objects.filter(patient=user)

        return LifeStoryEntry.objects.none()

    def perform_create(self, serializer):
        user = self.request.user
        patient_id = self.request.data.get("patient_id")

        if user.role == "patient":
            serializer.save(patient=user, created_by=user)
        elif patient_id:
            from django.contrib.auth import get_user_model
            User = get_user_model()
            try:
                patient = User.objects.get(pk=patient_id, role="patient")
            except User.DoesNotExist:
                from rest_framework import serializers as drf_serializers
                raise drf_serializers.ValidationError({"patient_id": "Patient not found."})
            serializer.save(patient=patient, created_by=user)
        else:
            from rest_framework import serializers as drf_serializers
            raise drf_serializers.ValidationError(
                {"patient_id": "Required for non-patient users."}
            )

    @action(detail=False, methods=["post"], url_path="upload-voice")
    def upload_voice(self, request):
        """
        Upload a voice message for a life story entry.
        Transcribes the audio and creates/updates the entry.
        """
        import os
        import uuid
        
        audio_file = request.FILES.get("audio")
        if not audio_file:
            return Response(
                {"error": "No audio file provided."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        
        # Get form data
        title = request.data.get("title", "Voice Message")
        category = request.data.get("category", "instructions")
        patient_id = request.data.get("patient_id")
        emotional_valence = request.data.get("emotional_valence", "neutral")
        trigger_questions = request.data.get("trigger_questions", "[]")
        priority = int(request.data.get("priority", 1))
        
        # Parse trigger_questions if it's a string
        if isinstance(trigger_questions, str):
            try:
                trigger_questions = json.loads(trigger_questions)
            except json.JSONDecodeError:
                trigger_questions = []
        
        user = request.user
        
        # Determine patient
        if user.role == "patient":
            patient = user
        elif patient_id:
            from django.contrib.auth import get_user_model
            User = get_user_model()
            try:
                patient = User.objects.get(pk=patient_id, role="patient")
            except User.DoesNotExist:
                return Response(
                    {"error": "Patient not found."},
                    status=status.HTTP_404_NOT_FOUND,
                )
        else:
            return Response(
                {"error": "patient_id is required for non-patient users."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        
        # Save audio file
        audio_dir = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), "media", "life_story_audio"
        )
        os.makedirs(audio_dir, exist_ok=True)
        
        filename = f"{uuid.uuid4().hex}.webm"
        filepath = os.path.join(audio_dir, filename)
        
        with open(filepath, "wb") as f:
            for chunk in audio_file.chunks():
                f.write(chunk)
        
        # Transcribe the audio
        try:
            with open(filepath, "rb") as f:
                transcript = conversation_engine.transcribe_audio(f)
        except Exception as e:
            logger.exception("Failed to transcribe life story audio")
            return Response(
                {"error": f"Transcription failed: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        
        # Create the life story entry
        entry = LifeStoryEntry.objects.create(
            patient=patient,
            category=category,
            entry_type="voice",
            title=title,
            description="",  # Voice entries use transcript instead
            audio_file=f"/media/life_story_audio/{filename}",
            audio_transcript=transcript,
            trigger_questions=trigger_questions,
            emotional_valence=emotional_valence,
            priority=priority,
            created_by=user,
        )
        
        serializer = LifeStoryEntrySerializer(entry)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"], url_path="retranscribe")
    def retranscribe(self, request, pk=None):
        """Re-transcribe an existing voice entry's audio."""
        import os
        
        entry = self.get_object()
        
        if entry.entry_type != "voice" or not entry.audio_file:
            return Response(
                {"error": "This entry has no audio to transcribe."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        
        # Get full path
        audio_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            entry.audio_file.lstrip("/")
        )
        
        if not os.path.exists(audio_path):
            return Response(
                {"error": "Audio file not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        
        try:
            with open(audio_path, "rb") as f:
                transcript = conversation_engine.transcribe_audio(f)
            
            entry.audio_transcript = transcript
            entry.save(update_fields=["audio_transcript", "updated_at"])
            
            serializer = LifeStoryEntrySerializer(entry)
            return Response(serializer.data)
        except Exception as e:
            return Response(
                {"error": f"Transcription failed: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class SessionViewSet(viewsets.ModelViewSet):
    serializer_class = ConversationSessionSerializer
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ['get', 'delete', 'head', 'options']  # Only allow read and delete

    def get_queryset(self):
        user = self.request.user
        patient_id = self.request.query_params.get("patient_id")

        if patient_id and user.role in ("doctor", "admin"):
            return ConversationSession.objects.filter(patient_id=patient_id)

        if user.role == "patient":
            return ConversationSession.objects.filter(patient=user)

        return ConversationSession.objects.none()
    
    def destroy(self, request, pk=None):
        """Delete a conversation session and all its messages."""
        session = self.get_object()
        
        # Verify ownership/permission
        user = request.user
        if user.role == "patient" and session.patient != user:
            return Response(
                {"error": "You can only delete your own conversations."},
                status=status.HTTP_403_FORBIDDEN,
            )
        
        session.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=["get"], url_path="messages")
    def messages(self, request, pk=None):
        session = self.get_object()
        messages = session.messages.order_by("timestamp")
        serializer = ConversationMessageSerializer(messages, many=True)
        return Response(serializer.data)


class CompanionConfigViewSet(viewsets.ViewSet):
    permission_classes = [permissions.IsAuthenticated]

    def list(self, request):
        user = request.user
        patient_id = request.query_params.get("patient_id")

        if patient_id and user.role in ("doctor", "admin"):
            target_id = patient_id
        elif user.role == "patient":
            target_id = user.pk
        else:
            return Response(
                {"error": "Insufficient permissions."},
                status=status.HTTP_403_FORBIDDEN,
            )

        config, _ = PatientCompanionConfig.objects.get_or_create(
            patient_id=target_id,
            defaults={"cognitive_stage": "mild"},
        )
        serializer = PatientCompanionConfigSerializer(config)
        return Response(serializer.data)

    def partial_update(self, request, pk=None):
        user = request.user

        if user.role == "patient":
            config, _ = PatientCompanionConfig.objects.get_or_create(
                patient=user, defaults={"cognitive_stage": "mild"}
            )
        elif pk:
            try:
                config = PatientCompanionConfig.objects.get(patient_id=pk)
            except PatientCompanionConfig.DoesNotExist:
                return Response(
                    {"error": "Config not found."},
                    status=status.HTTP_404_NOT_FOUND,
                )
        else:
            return Response(
                {"error": "Patient ID required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = PatientCompanionConfigSerializer(
            config, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)

        if "consent_given" in request.data and request.data["consent_given"]:
            config.consent_date = timezone.now()

        serializer.save()
        return Response(serializer.data)
