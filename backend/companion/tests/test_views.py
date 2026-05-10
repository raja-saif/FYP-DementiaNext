"""
Comprehensive tests for companion/views.py
Covers ChatViewSet, LifeStoryViewSet, SessionViewSet, CompanionConfigViewSet.
"""
import json
from io import BytesIO
from unittest.mock import patch, MagicMock

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import AccessToken

from companion.models import (
    ConversationMessage,
    ConversationSession,
    LifeStoryEntry,
    PatientCompanionConfig,
)

User = get_user_model()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _auth(client, user):
    token = AccessToken.for_user(user)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")


def _make_audio():
    return SimpleUploadedFile("audio.webm", b"fake-audio-data", content_type="audio/webm")


# ===================================================================
# ChatViewSet
# ===================================================================

class ChatSendMessageTests(APITestCase):
    """POST /api/companion/chat/send/"""

    url = "/api/companion/chat/send/"

    def setUp(self):
        self.patient = User.objects.create_user(
            email="patient@test.com", password="pass", role="patient",
            first_name="Pat", last_name="Ient",
        )
        self.doctor = User.objects.create_user(
            email="doctor@test.com", password="pass", role="doctor",
        )
        self.patient2 = User.objects.create_user(
            email="patient2@test.com", password="pass", role="patient",
        )

    # -- auth ---------------------------------------------------------------

    def test_unauthenticated_rejected(self):
        resp = self.client.post(self.url, {"message": "hi"})
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    # -- patient mode -------------------------------------------------------

    @patch("companion.tts_service.generate_tts_async", return_value="task-1")
    @patch("companion.conversation_engine.chat", return_value=("Hello!", 120))
    def test_patient_mode_success(self, mock_chat, mock_tts):
        _auth(self.client, self.patient)
        resp = self.client.post(self.url, {"message": "hi", "mode": "patient"})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        data = resp.json()
        self.assertEqual(data["reply"], "Hello!")
        self.assertEqual(data["response_time_ms"], 120)
        self.assertIsNotNone(data["session_id"])
        self.assertEqual(data["tts_task_id"], "task-1")
        self.assertIsNone(data["audio_url"])
        mock_chat.assert_called_once()
        mock_tts.assert_called_once()

    @patch("companion.conversation_engine.chat", return_value=("ok", 10))
    def test_patient_mode_forbidden_for_doctor(self, _mock):
        _auth(self.client, self.doctor)
        resp = self.client.post(self.url, {"message": "hi", "mode": "patient"})
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn("Patient mode requires", resp.json()["error"])

    # -- caregiver mode -----------------------------------------------------

    @patch("companion.conversation_engine.chat", return_value=("reply", 50))
    def test_caregiver_mode_patient_self(self, mock_chat):
        """Patient using caregiver mode for themselves (no patient_id needed)."""
        _auth(self.client, self.patient)
        resp = self.client.post(self.url, {"message": "hi", "mode": "caregiver"})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIsNone(resp.json()["tts_task_id"])

    @patch("companion.conversation_engine.chat", return_value=("reply", 50))
    def test_caregiver_mode_doctor_with_patient_id(self, mock_chat):
        _auth(self.client, self.doctor)
        resp = self.client.post(
            self.url,
            {"message": "hi", "mode": "caregiver", "patient_id": self.patient.pk},
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_caregiver_mode_doctor_missing_patient_id(self):
        _auth(self.client, self.doctor)
        resp = self.client.post(self.url, {"message": "hi", "mode": "caregiver"})
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("patient_id is required", resp.json()["error"])

    def test_caregiver_mode_doctor_nonexistent_patient(self):
        _auth(self.client, self.doctor)
        resp = self.client.post(
            self.url,
            {"message": "hi", "mode": "caregiver", "patient_id": 99999},
        )
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    # -- session handling ---------------------------------------------------

    @patch("companion.tts_service.generate_tts_async", return_value="t")
    @patch("companion.conversation_engine.chat", return_value=("r", 1))
    def test_creates_new_session_when_none(self, _m1, _m2):
        _auth(self.client, self.patient)
        resp = self.client.post(self.url, {"message": "hi", "mode": "patient"})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        session_id = resp.json()["session_id"]
        self.assertTrue(ConversationSession.objects.filter(pk=session_id).exists())

    @patch("companion.tts_service.generate_tts_async", return_value="t")
    @patch("companion.conversation_engine.chat", return_value=("r", 1))
    def test_reuses_existing_session(self, _m1, _m2):
        session = ConversationSession.objects.create(
            patient=self.patient, mode="patient", cognitive_stage_at_time="mild",
        )
        _auth(self.client, self.patient)
        resp = self.client.post(
            self.url,
            {"message": "hi", "mode": "patient", "session_id": session.pk},
        )
        self.assertEqual(resp.json()["session_id"], session.pk)

    @patch("companion.tts_service.generate_tts_async", return_value="t")
    @patch("companion.conversation_engine.chat", return_value=("r", 1))
    def test_invalid_session_id_creates_new(self, _m1, _m2):
        _auth(self.client, self.patient)
        resp = self.client.post(
            self.url,
            {"message": "hi", "mode": "patient", "session_id": 99999},
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertNotEqual(resp.json()["session_id"], 99999)

    # -- audio transcription ------------------------------------------------

    @patch("companion.tts_service.generate_tts_async", return_value="t")
    @patch("companion.conversation_engine.chat", return_value=("r", 1))
    @patch("companion.conversation_engine.transcribe_audio", return_value="hello world")
    def test_audio_upload_transcribed(self, mock_tr, mock_chat, _m3):
        _auth(self.client, self.patient)
        resp = self.client.post(
            self.url,
            {"mode": "patient", "audio": _make_audio()},
            format="multipart",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        mock_tr.assert_called_once()
        mock_chat.assert_called_once()
        call_kwargs = mock_chat.call_args
        self.assertEqual(call_kwargs.kwargs.get("user_text") or call_kwargs[1].get("user_text", call_kwargs[0][2] if len(call_kwargs[0]) > 2 else None), "hello world")

    @patch("companion.conversation_engine.transcribe_audio", return_value="ab")
    def test_audio_too_short_rejected(self, _mock):
        _auth(self.client, self.patient)
        resp = self.client.post(
            self.url,
            {"mode": "patient", "audio": _make_audio()},
            format="multipart",
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Could not understand", resp.json()["error"])

    @patch("companion.conversation_engine.transcribe_audio", return_value="")
    def test_audio_empty_transcription_rejected(self, _mock):
        _auth(self.client, self.patient)
        resp = self.client.post(
            self.url,
            {"mode": "patient", "audio": _make_audio()},
            format="multipart",
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    @patch("companion.conversation_engine.transcribe_audio", side_effect=RuntimeError("boom"))
    def test_audio_transcription_error(self, _mock):
        _auth(self.client, self.patient)
        resp = self.client.post(
            self.url,
            {"mode": "patient", "audio": _make_audio()},
            format="multipart",
        )
        self.assertEqual(resp.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        self.assertIn("Transcription failed", resp.json()["error"])

    # -- no message ---------------------------------------------------------

    def test_no_message_or_audio(self):
        _auth(self.client, self.patient)
        resp = self.client.post(self.url, {"mode": "patient"})
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    # -- chat engine errors -------------------------------------------------

    @patch("companion.conversation_engine.chat", side_effect=ValueError("bad value"))
    def test_chat_value_error(self, _mock):
        _auth(self.client, self.patient)
        resp = self.client.post(self.url, {"message": "hi", "mode": "patient"})
        self.assertEqual(resp.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        self.assertEqual(resp.json()["error"], "bad value")

    @patch("companion.conversation_engine.chat", side_effect=RuntimeError("oops"))
    def test_chat_generic_error(self, _mock):
        _auth(self.client, self.patient)
        resp = self.client.post(self.url, {"message": "hi", "mode": "patient"})
        self.assertEqual(resp.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        self.assertIn("Chat failed", resp.json()["error"])

    # -- message text takes priority over audio -----------------------------

    @patch("companion.tts_service.generate_tts_async", return_value="t")
    @patch("companion.conversation_engine.chat", return_value=("r", 1))
    def test_message_text_skips_transcription(self, mock_chat, _m2):
        """When message text IS provided alongside audio, skip transcription."""
        _auth(self.client, self.patient)
        resp = self.client.post(
            self.url,
            {"mode": "patient", "message": "typed msg", "audio": _make_audio()},
            format="multipart",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)


class ChatSendMessageStreamTests(APITestCase):
    """POST /api/companion/chat/send-stream/"""

    url = "/api/companion/chat/send-stream/"

    def setUp(self):
        self.patient = User.objects.create_user(
            email="stream_patient@test.com", password="pass", role="patient",
            first_name="SP", last_name="User",
        )
        self.doctor = User.objects.create_user(
            email="stream_doctor@test.com", password="pass", role="doctor",
        )

    def _consume(self, response):
        """Consume SSE streaming response and return parsed events."""
        events = []
        content = b"".join(response.streaming_content).decode()
        for line in content.split("\n"):
            if line.startswith("data: "):
                events.append(json.loads(line[6:]))
        return events

    # -- auth ---------------------------------------------------------------

    def test_unauthenticated_rejected(self):
        resp = self.client.post(self.url, {"message": "hi"})
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    # -- streaming success --------------------------------------------------

    @patch("companion.tts_service.generate_tts_async", return_value="tts-123")
    @patch("companion.conversation_engine.chat_stream")
    def test_stream_chunks_then_done(self, mock_stream, mock_tts):
        mock_stream.return_value = iter([
            {"type": "chunk", "content": "Hel"},
            {"type": "chunk", "content": "lo!"},
            {"type": "done", "content": "Hello!", "response_time_ms": 200},
        ])
        _auth(self.client, self.patient)
        resp = self.client.post(self.url, {"message": "hi", "mode": "patient"})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp["Content-Type"], "text/event-stream; charset=utf-8")
        self.assertEqual(resp["Cache-Control"], "no-cache, no-store, must-revalidate")
        self.assertEqual(resp["X-Accel-Buffering"], "no")

        events = self._consume(resp)
        self.assertEqual(len(events), 3)
        self.assertEqual(events[0]["type"], "chunk")
        self.assertEqual(events[0]["content"], "Hel")
        self.assertEqual(events[2]["type"], "done")
        self.assertEqual(events[2]["tts_task_id"], "tts-123")

    @patch("companion.conversation_engine.chat_stream")
    def test_stream_caregiver_no_tts(self, mock_stream):
        mock_stream.return_value = iter([
            {"type": "done", "content": "Reply", "response_time_ms": 10},
        ])
        _auth(self.client, self.patient)
        resp = self.client.post(self.url, {"message": "hi", "mode": "caregiver"})
        events = self._consume(resp)
        done = events[-1]
        self.assertIsNone(done["tts_task_id"])

    # -- faq_hit event ------------------------------------------------------

    @patch("companion.tts_service.generate_tts_async", return_value="tts-faq")
    @patch("companion.conversation_engine.chat_stream")
    def test_stream_faq_hit_patient(self, mock_stream, mock_tts):
        mock_stream.return_value = iter([
            {"type": "faq_hit", "content": "Cached answer"},
        ])
        _auth(self.client, self.patient)
        resp = self.client.post(self.url, {"message": "where am I", "mode": "patient"})
        events = self._consume(resp)
        self.assertEqual(events[0]["type"], "faq_hit")
        self.assertEqual(events[0]["tts_task_id"], "tts-faq")

    @patch("companion.conversation_engine.chat_stream")
    def test_stream_faq_hit_caregiver_no_tts(self, mock_stream):
        mock_stream.return_value = iter([
            {"type": "faq_hit", "content": "Cached answer"},
        ])
        _auth(self.client, self.patient)
        resp = self.client.post(
            self.url, {"message": "where am I", "mode": "caregiver"},
        )
        events = self._consume(resp)
        self.assertIsNone(events[0]["tts_task_id"])

    # -- audio transcription in stream --------------------------------------

    @patch("companion.tts_service.generate_tts_async", return_value="t")
    @patch("companion.conversation_engine.chat_stream")
    @patch("companion.conversation_engine.transcribe_audio", return_value="transcribed text")
    def test_stream_audio_sends_transcription_event(self, _tr, mock_stream, _tts):
        mock_stream.return_value = iter([
            {"type": "done", "content": "reply", "response_time_ms": 5},
        ])
        _auth(self.client, self.patient)
        resp = self.client.post(
            self.url,
            {"mode": "patient", "audio": _make_audio()},
            format="multipart",
        )
        events = self._consume(resp)
        self.assertEqual(events[0]["type"], "transcription")
        self.assertEqual(events[0]["content"], "transcribed text")

    @patch("companion.conversation_engine.transcribe_audio", return_value="ab")
    def test_stream_audio_too_short(self, _mock):
        _auth(self.client, self.patient)
        resp = self.client.post(
            self.url,
            {"mode": "patient", "audio": _make_audio()},
            format="multipart",
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    @patch("companion.conversation_engine.transcribe_audio", side_effect=RuntimeError("boom"))
    def test_stream_audio_transcription_error(self, _mock):
        _auth(self.client, self.patient)
        resp = self.client.post(
            self.url,
            {"mode": "patient", "audio": _make_audio()},
            format="multipart",
        )
        self.assertEqual(resp.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)

    def test_stream_no_message_or_audio(self):
        _auth(self.client, self.patient)
        resp = self.client.post(self.url, {"mode": "patient"})
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    # -- streaming errors ---------------------------------------------------

    @patch("companion.conversation_engine.chat_stream", side_effect=ValueError("bad"))
    def test_stream_value_error(self, _mock):
        """ValueError inside the generator yields an error event."""
        _auth(self.client, self.patient)
        resp = self.client.post(self.url, {"message": "hi", "mode": "patient"})
        events = self._consume(resp)
        error_events = [e for e in events if e["type"] == "error"]
        self.assertTrue(len(error_events) >= 1)
        self.assertIn("bad", error_events[0]["message"])

    @patch("companion.conversation_engine.chat_stream", side_effect=RuntimeError("crash"))
    def test_stream_generic_error(self, _mock):
        _auth(self.client, self.patient)
        resp = self.client.post(self.url, {"message": "hi", "mode": "patient"})
        events = self._consume(resp)
        error_events = [e for e in events if e["type"] == "error"]
        self.assertTrue(len(error_events) >= 1)
        self.assertIn("Chat failed", error_events[0]["message"])

    # -- _get_patient_and_session branches for stream -----------------------

    def test_stream_patient_mode_forbidden_for_doctor(self):
        _auth(self.client, self.doctor)
        resp = self.client.post(self.url, {"message": "hi", "mode": "patient"})
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_stream_caregiver_doctor_missing_patient_id(self):
        _auth(self.client, self.doctor)
        resp = self.client.post(self.url, {"message": "hi", "mode": "caregiver"})
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_stream_caregiver_doctor_nonexistent_patient(self):
        _auth(self.client, self.doctor)
        resp = self.client.post(
            self.url,
            {"message": "hi", "mode": "caregiver", "patient_id": 99999},
        )
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)


class ChatTTSStatusTests(APITestCase):
    """GET /api/companion/chat/tts-status/<task_id>/"""

    def setUp(self):
        self.user = User.objects.create_user(
            email="tts_user@test.com", password="pass", role="patient",
        )

    def _url(self, task_id):
        return f"/api/companion/chat/tts-status/{task_id}/"

    def test_unauthenticated(self):
        resp = self.client.get(self._url("abc"))
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    @patch("companion.tts_service.cleanup_tts_task")
    @patch("companion.tts_service.get_tts_status", return_value={"status": "completed", "audio_url": "/a.mp3"})
    def test_completed_cleans_up(self, mock_get, mock_cleanup):
        _auth(self.client, self.user)
        resp = self.client.get(self._url("task-1"))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.json()["status"], "completed")
        mock_cleanup.assert_called_once_with("task-1")

    @patch("companion.tts_service.get_tts_status", return_value={"status": "pending"})
    def test_pending_no_cleanup(self, mock_get):
        _auth(self.client, self.user)
        resp = self.client.get(self._url("task-2"))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.json()["status"], "pending")

    @patch("companion.tts_service.get_tts_status", return_value=None)
    def test_task_not_found(self, _mock):
        _auth(self.client, self.user)
        resp = self.client.get(self._url("nope"))
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)


class ChatTranscribeTests(APITestCase):
    """POST /api/companion/chat/transcribe/"""

    url = "/api/companion/chat/transcribe/"

    def setUp(self):
        self.user = User.objects.create_user(
            email="tr_user@test.com", password="pass", role="patient",
        )

    def test_unauthenticated(self):
        resp = self.client.post(self.url)
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    @patch("companion.conversation_engine.transcribe_audio", return_value="hello")
    def test_success(self, mock_tr):
        _auth(self.client, self.user)
        resp = self.client.post(
            self.url, {"audio": _make_audio()}, format="multipart",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.json()["text"], "hello")

    def test_no_audio(self):
        _auth(self.client, self.user)
        resp = self.client.post(self.url)
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    @patch("companion.conversation_engine.transcribe_audio", side_effect=RuntimeError("fail"))
    def test_transcription_error(self, _mock):
        _auth(self.client, self.user)
        resp = self.client.post(
            self.url, {"audio": _make_audio()}, format="multipart",
        )
        self.assertEqual(resp.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        self.assertIn("Transcription failed", resp.json()["error"])


# ===================================================================
# LifeStoryViewSet
# ===================================================================

class LifeStoryListCreateTests(APITestCase):
    """GET/POST /api/companion/life-story/"""

    url = "/api/companion/life-story/"

    def setUp(self):
        self.patient = User.objects.create_user(
            email="ls_pat@test.com", password="pass", role="patient",
            first_name="Pat", last_name="Ient",
        )
        self.patient2 = User.objects.create_user(
            email="ls_pat2@test.com", password="pass", role="patient",
        )
        self.doctor = User.objects.create_user(
            email="ls_doc@test.com", password="pass", role="doctor",
        )
        self.admin = User.objects.create_user(
            email="ls_admin@test.com", password="pass", role="admin",
        )
        self.entry = LifeStoryEntry.objects.create(
            patient=self.patient,
            category="family",
            title="Daughter",
            description="Sarah visits Sundays",
            created_by=self.patient,
        )

    # -- GET queryset -------------------------------------------------------

    def test_patient_sees_own_entries(self):
        _auth(self.client, self.patient)
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp.json()), 1)

    def test_patient2_sees_nothing(self):
        _auth(self.client, self.patient2)
        resp = self.client.get(self.url)
        self.assertEqual(len(resp.json()), 0)

    def test_doctor_with_patient_id(self):
        _auth(self.client, self.doctor)
        resp = self.client.get(self.url, {"patient_id": self.patient.pk})
        self.assertEqual(len(resp.json()), 1)

    def test_admin_with_patient_id(self):
        _auth(self.client, self.admin)
        resp = self.client.get(self.url, {"patient_id": self.patient.pk})
        self.assertEqual(len(resp.json()), 1)

    def test_doctor_without_patient_id_empty(self):
        _auth(self.client, self.doctor)
        resp = self.client.get(self.url)
        self.assertEqual(len(resp.json()), 0)

    def test_unauthenticated(self):
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    # -- POST perform_create ------------------------------------------------

    def test_patient_create_entry(self):
        _auth(self.client, self.patient)
        resp = self.client.post(self.url, {
            "category": "memories",
            "title": "Wedding day",
            "description": "Married in 1970",
        })
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        entry = LifeStoryEntry.objects.get(pk=resp.json()["id"])
        self.assertEqual(entry.patient, self.patient)
        self.assertEqual(entry.created_by, self.patient)

    def test_doctor_create_entry_with_patient_id(self):
        _auth(self.client, self.doctor)
        resp = self.client.post(self.url, {
            "category": "health",
            "title": "Allergy",
            "description": "Penicillin",
            "patient_id": self.patient.pk,
        })
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        entry = LifeStoryEntry.objects.get(pk=resp.json()["id"])
        self.assertEqual(entry.patient, self.patient)
        self.assertEqual(entry.created_by, self.doctor)

    def test_doctor_create_entry_invalid_patient(self):
        _auth(self.client, self.doctor)
        resp = self.client.post(self.url, {
            "category": "health",
            "title": "Allergy",
            "description": "Penicillin",
            "patient_id": 99999,
        })
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_doctor_create_entry_no_patient_id(self):
        _auth(self.client, self.doctor)
        resp = self.client.post(self.url, {
            "category": "health",
            "title": "Allergy",
            "description": "Penicillin",
        })
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)


class LifeStoryUploadVoiceTests(APITestCase):
    """POST /api/companion/life-story/upload-voice/"""

    url = "/api/companion/life-story/upload-voice/"

    def setUp(self):
        self.patient = User.objects.create_user(
            email="uv_pat@test.com", password="pass", role="patient",
            first_name="UV", last_name="Pat",
        )
        self.doctor = User.objects.create_user(
            email="uv_doc@test.com", password="pass", role="doctor",
        )

    def test_unauthenticated(self):
        resp = self.client.post(self.url)
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_no_audio_file(self):
        _auth(self.client, self.patient)
        resp = self.client.post(self.url)
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("No audio file", resp.json()["error"])

    @patch("companion.conversation_engine.transcribe_audio", return_value="My story")
    def test_patient_upload_voice(self, _mock):
        _auth(self.client, self.patient)
        resp = self.client.post(
            self.url,
            {
                "audio": _make_audio(),
                "title": "My Childhood",
                "category": "memories",
                "emotional_valence": "positive",
                "priority": 2,
                "trigger_questions": json.dumps(["Tell me about childhood"]),
            },
            format="multipart",
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        data = resp.json()
        self.assertEqual(data["entry_type"], "voice")
        self.assertEqual(data["audio_transcript"], "My story")
        self.assertEqual(data["title"], "My Childhood")

        entry = LifeStoryEntry.objects.get(pk=data["id"])
        self.assertEqual(entry.patient, self.patient)
        self.assertEqual(entry.created_by, self.patient)
        self.assertEqual(entry.priority, 2)
        self.assertEqual(entry.emotional_valence, "positive")
        self.assertEqual(entry.trigger_questions, ["Tell me about childhood"])

    @patch("companion.conversation_engine.transcribe_audio", return_value="doc story")
    def test_doctor_upload_voice_with_patient_id(self, _mock):
        _auth(self.client, self.doctor)
        resp = self.client.post(
            self.url,
            {
                "audio": _make_audio(),
                "patient_id": self.patient.pk,
            },
            format="multipart",
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        entry = LifeStoryEntry.objects.get(pk=resp.json()["id"])
        self.assertEqual(entry.patient, self.patient)
        self.assertEqual(entry.created_by, self.doctor)

    def test_doctor_upload_voice_no_patient_id(self):
        _auth(self.client, self.doctor)
        resp = self.client.post(
            self.url,
            {"audio": _make_audio()},
            format="multipart",
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("patient_id is required", resp.json()["error"])

    def test_doctor_upload_voice_invalid_patient(self):
        _auth(self.client, self.doctor)
        resp = self.client.post(
            self.url,
            {"audio": _make_audio(), "patient_id": 99999},
            format="multipart",
        )
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    @patch("companion.conversation_engine.transcribe_audio", side_effect=RuntimeError("fail"))
    def test_transcription_failure(self, _mock):
        _auth(self.client, self.patient)
        resp = self.client.post(
            self.url,
            {"audio": _make_audio()},
            format="multipart",
        )
        self.assertEqual(resp.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        self.assertIn("Transcription failed", resp.json()["error"])

    @patch("companion.conversation_engine.transcribe_audio", return_value="ok")
    def test_trigger_questions_bad_json_fallback(self, _mock):
        _auth(self.client, self.patient)
        resp = self.client.post(
            self.url,
            {
                "audio": _make_audio(),
                "trigger_questions": "not valid json",
            },
            format="multipart",
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        entry = LifeStoryEntry.objects.get(pk=resp.json()["id"])
        self.assertEqual(entry.trigger_questions, [])

    @patch("companion.conversation_engine.transcribe_audio", return_value="defaults test")
    def test_defaults_applied(self, _mock):
        """When optional fields are omitted, defaults are used."""
        _auth(self.client, self.patient)
        resp = self.client.post(
            self.url,
            {"audio": _make_audio()},
            format="multipart",
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        data = resp.json()
        self.assertEqual(data["title"], "Voice Message")
        self.assertEqual(data["category"], "instructions")


class LifeStoryRetranscribeTests(APITestCase):
    """POST /api/companion/life-story/<pk>/retranscribe/"""

    def setUp(self):
        self.patient = User.objects.create_user(
            email="retr_pat@test.com", password="pass", role="patient",
            first_name="R", last_name="P",
        )

    def _url(self, pk):
        return f"/api/companion/life-story/{pk}/retranscribe/"

    def test_unauthenticated(self):
        resp = self.client.post(self._url(1))
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_non_voice_entry_rejected(self):
        entry = LifeStoryEntry.objects.create(
            patient=self.patient, category="family", entry_type="text",
            title="Text", description="desc", created_by=self.patient,
        )
        _auth(self.client, self.patient)
        resp = self.client.post(self._url(entry.pk))
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("no audio", resp.json()["error"])

    def test_voice_entry_no_audio_file(self):
        entry = LifeStoryEntry.objects.create(
            patient=self.patient, category="family", entry_type="voice",
            title="Voice", audio_file="", created_by=self.patient,
        )
        _auth(self.client, self.patient)
        resp = self.client.post(self._url(entry.pk))
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    @patch("os.path.exists", return_value=False)
    def test_audio_file_not_on_disk(self, _mock):
        entry = LifeStoryEntry.objects.create(
            patient=self.patient, category="family", entry_type="voice",
            title="Voice", audio_file="/media/life_story_audio/missing.webm",
            created_by=self.patient,
        )
        _auth(self.client, self.patient)
        resp = self.client.post(self._url(entry.pk))
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)
        self.assertIn("Audio file not found", resp.json()["error"])

    @patch("companion.conversation_engine.transcribe_audio", return_value="new transcript")
    @patch("builtins.open", MagicMock())
    @patch("os.path.exists", return_value=True)
    def test_retranscribe_success(self, _exists, mock_tr):
        entry = LifeStoryEntry.objects.create(
            patient=self.patient, category="family", entry_type="voice",
            title="Voice", audio_file="/media/life_story_audio/test.webm",
            audio_transcript="old transcript", created_by=self.patient,
        )
        _auth(self.client, self.patient)
        resp = self.client.post(self._url(entry.pk))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        entry.refresh_from_db()
        self.assertEqual(entry.audio_transcript, "new transcript")

    @patch("companion.conversation_engine.transcribe_audio", side_effect=RuntimeError("fail"))
    @patch("builtins.open", MagicMock())
    @patch("os.path.exists", return_value=True)
    def test_retranscribe_failure(self, _exists, _mock):
        entry = LifeStoryEntry.objects.create(
            patient=self.patient, category="family", entry_type="voice",
            title="Voice", audio_file="/media/life_story_audio/test.webm",
            created_by=self.patient,
        )
        _auth(self.client, self.patient)
        resp = self.client.post(self._url(entry.pk))
        self.assertEqual(resp.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        self.assertIn("Transcription failed", resp.json()["error"])


# ===================================================================
# SessionViewSet
# ===================================================================

class SessionViewSetTests(APITestCase):
    """GET/DELETE /api/companion/sessions/"""

    url = "/api/companion/sessions/"

    def setUp(self):
        self.patient = User.objects.create_user(
            email="sess_pat@test.com", password="pass", role="patient",
            first_name="S", last_name="P",
        )
        self.patient2 = User.objects.create_user(
            email="sess_pat2@test.com", password="pass", role="patient",
        )
        self.doctor = User.objects.create_user(
            email="sess_doc@test.com", password="pass", role="doctor",
        )
        self.session = ConversationSession.objects.create(
            patient=self.patient, mode="patient", cognitive_stage_at_time="mild",
        )
        self.session2 = ConversationSession.objects.create(
            patient=self.patient2, mode="patient", cognitive_stage_at_time="mild",
        )

    # -- GET queryset -------------------------------------------------------

    def test_patient_sees_own_sessions(self):
        _auth(self.client, self.patient)
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        ids = [s["id"] for s in resp.json()]
        self.assertIn(self.session.pk, ids)
        self.assertNotIn(self.session2.pk, ids)

    def test_doctor_with_patient_id(self):
        _auth(self.client, self.doctor)
        resp = self.client.get(self.url, {"patient_id": self.patient.pk})
        self.assertEqual(len(resp.json()), 1)

    def test_doctor_without_patient_id_empty(self):
        _auth(self.client, self.doctor)
        resp = self.client.get(self.url)
        self.assertEqual(len(resp.json()), 0)

    def test_unauthenticated(self):
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    # -- DELETE destroy ------------------------------------------------------

    def test_patient_delete_own_session(self):
        _auth(self.client, self.patient)
        resp = self.client.delete(f"{self.url}{self.session.pk}/")
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(ConversationSession.objects.filter(pk=self.session.pk).exists())

    def test_doctor_delete_patient_session(self):
        _auth(self.client, self.doctor)
        resp = self.client.delete(
            f"{self.url}{self.session.pk}/",
            QUERY_STRING=f"patient_id={self.patient.pk}",
        )
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)

    def test_patient_cannot_delete_other_session(self):
        """Patient tries to delete another patient's session - 404 from queryset."""
        _auth(self.client, self.patient)
        resp = self.client.delete(f"{self.url}{self.session2.pk}/")
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    # -- method restrictions ------------------------------------------------

    def test_post_not_allowed(self):
        _auth(self.client, self.patient)
        resp = self.client.post(self.url, {"mode": "patient"})
        self.assertEqual(resp.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_put_not_allowed(self):
        _auth(self.client, self.patient)
        resp = self.client.put(f"{self.url}{self.session.pk}/", {"mode": "caregiver"})
        self.assertEqual(resp.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    # -- messages action ----------------------------------------------------

    def test_list_messages(self):
        ConversationMessage.objects.create(
            session=self.session, role="user", content_text="Hello",
        )
        ConversationMessage.objects.create(
            session=self.session, role="assistant", content_text="Hi there",
        )
        _auth(self.client, self.patient)
        resp = self.client.get(f"{self.url}{self.session.pk}/messages/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp.json()), 2)
        self.assertEqual(resp.json()[0]["role"], "user")

    def test_list_messages_other_patient_404(self):
        _auth(self.client, self.patient)
        resp = self.client.get(f"{self.url}{self.session2.pk}/messages/")
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_list_messages_empty(self):
        _auth(self.client, self.patient)
        resp = self.client.get(f"{self.url}{self.session.pk}/messages/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.json(), [])


# ===================================================================
# CompanionConfigViewSet
# ===================================================================

class CompanionConfigListTests(APITestCase):
    """GET /api/companion/config/"""

    url = "/api/companion/config/"

    def setUp(self):
        self.patient = User.objects.create_user(
            email="cfg_pat@test.com", password="pass", role="patient",
            first_name="C", last_name="P",
        )
        self.doctor = User.objects.create_user(
            email="cfg_doc@test.com", password="pass", role="doctor",
        )
        self.admin = User.objects.create_user(
            email="cfg_admin@test.com", password="pass", role="admin",
        )

    def test_unauthenticated(self):
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_patient_gets_own_config(self):
        _auth(self.client, self.patient)
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(int(resp.json()["patient"]), self.patient.pk)
        self.assertEqual(resp.json()["cognitive_stage"], "mild")

    def test_patient_config_created_if_missing(self):
        self.assertFalse(PatientCompanionConfig.objects.filter(patient=self.patient).exists())
        _auth(self.client, self.patient)
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertTrue(PatientCompanionConfig.objects.filter(patient=self.patient).exists())

    def test_doctor_with_patient_id(self):
        _auth(self.client, self.doctor)
        resp = self.client.get(self.url, {"patient_id": self.patient.pk})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(int(resp.json()["patient"]), self.patient.pk)

    def test_admin_with_patient_id(self):
        _auth(self.client, self.admin)
        resp = self.client.get(self.url, {"patient_id": self.patient.pk})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_doctor_without_patient_id_forbidden(self):
        _auth(self.client, self.doctor)
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn("Insufficient permissions", resp.json()["error"])


class CompanionConfigUpdateTests(APITestCase):
    """PATCH /api/companion/config/<pk>/"""

    url = "/api/companion/config/"

    def setUp(self):
        self.patient = User.objects.create_user(
            email="cfgu_pat@test.com", password="pass", role="patient",
            first_name="CU", last_name="P",
        )
        self.doctor = User.objects.create_user(
            email="cfgu_doc@test.com", password="pass", role="doctor",
        )
        self.config = PatientCompanionConfig.objects.create(
            patient=self.patient, cognitive_stage="mild",
        )

    def _url(self, pk):
        return f"{self.url}{pk}/"

    def test_unauthenticated(self):
        resp = self.client.patch(self._url(self.patient.pk), {})
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_patient_updates_own_config(self):
        _auth(self.client, self.patient)
        resp = self.client.patch(
            self._url(self.patient.pk),
            {"cognitive_stage": "moderate"},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.config.refresh_from_db()
        self.assertEqual(self.config.cognitive_stage, "moderate")

    def test_patient_ignores_pk_uses_own(self):
        """Patient always edits their own config regardless of pk in URL."""
        other = User.objects.create_user(
            email="other_pat@test.com", password="pass", role="patient",
        )
        PatientCompanionConfig.objects.create(patient=other, cognitive_stage="mild")
        _auth(self.client, self.patient)
        resp = self.client.patch(
            self._url(other.pk),
            {"preferred_voice": "en-GB"},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.config.refresh_from_db()
        self.assertEqual(self.config.preferred_voice, "en-GB")

    def test_doctor_updates_patient_config(self):
        _auth(self.client, self.doctor)
        resp = self.client.patch(
            self._url(self.patient.pk),
            {"cognitive_stage": "severe"},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.config.refresh_from_db()
        self.assertEqual(self.config.cognitive_stage, "severe")

    def test_doctor_config_not_found(self):
        _auth(self.client, self.doctor)
        resp = self.client.patch(
            self._url(99999),
            {"cognitive_stage": "mild"},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_doctor_no_pk_bad_request(self):
        """Doctor hits /config// (empty pk) — should 404 from router."""
        _auth(self.client, self.doctor)
        resp = self.client.patch(
            self.url,
            {"cognitive_stage": "mild"},
            format="json",
        )
        self.assertIn(resp.status_code, [
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_405_METHOD_NOT_ALLOWED,
        ])

    def test_consent_given_sets_date(self):
        self.assertIsNone(self.config.consent_date)
        _auth(self.client, self.patient)
        resp = self.client.patch(
            self._url(self.patient.pk),
            {"consent_given": True},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.config.refresh_from_db()
        self.assertTrue(self.config.consent_given)
        self.assertIsNotNone(self.config.consent_date)

    def test_consent_given_false_does_not_set_date(self):
        _auth(self.client, self.patient)
        resp = self.client.patch(
            self._url(self.patient.pk),
            {"consent_given": False},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.config.refresh_from_db()
        self.assertIsNone(self.config.consent_date)

    def test_patient_config_auto_created(self):
        """If patient has no config yet, partial_update creates one."""
        new_patient = User.objects.create_user(
            email="newcfg@test.com", password="pass", role="patient",
        )
        _auth(self.client, new_patient)
        resp = self.client.patch(
            self._url(new_patient.pk),
            {"language": "fr"},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertTrue(PatientCompanionConfig.objects.filter(patient=new_patient).exists())
        self.assertEqual(
            PatientCompanionConfig.objects.get(patient=new_patient).language, "fr",
        )
