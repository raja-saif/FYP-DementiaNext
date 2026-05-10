import os
import io
import pickle
import time
import threading
from datetime import date, timedelta
from unittest.mock import patch, MagicMock, PropertyMock, call

import numpy as np
from django.test import TestCase
from django.utils import timezone
from django.contrib.auth import get_user_model

User = get_user_model()


# =============================================================================
# 1. conversation_engine.py tests
# =============================================================================

class ConversationEngineGetClientTests(TestCase):

    def setUp(self):
        import companion.conversation_engine as mod
        self._mod = mod
        self._orig_client = mod._client

    def tearDown(self):
        self._mod._client = self._orig_client

    @patch.dict(os.environ, {"GROQ_API_KEY": ""})
    def test_get_client_raises_without_api_key(self):
        self._mod._client = None
        with self.assertRaises(ValueError) as ctx:
            self._mod._get_client()
        self.assertIn("GROQ_API_KEY", str(ctx.exception))

    @patch.dict(os.environ, {"GROQ_API_KEY": "   "})
    def test_get_client_raises_with_whitespace_only_key(self):
        self._mod._client = None
        with self.assertRaises(ValueError):
            self._mod._get_client()

    @patch("companion.conversation_engine.Groq")
    @patch.dict(os.environ, {"GROQ_API_KEY": "test-key-123"})
    def test_get_client_returns_groq_client(self, mock_groq_cls):
        self._mod._client = None
        mock_groq_cls.return_value = MagicMock()
        client = self._mod._get_client()
        mock_groq_cls.assert_called_once_with(api_key="test-key-123")
        self.assertIsNotNone(client)

    @patch("companion.conversation_engine.Groq")
    @patch.dict(os.environ, {"GROQ_API_KEY": "test-key"})
    def test_get_client_caches_instance(self, mock_groq_cls):
        self._mod._client = None
        self._mod._get_client()
        self._mod._get_client()
        mock_groq_cls.assert_called_once()


class ConversationEngineStripThinkingTests(TestCase):

    def setUp(self):
        from companion.conversation_engine import _strip_thinking_tags
        self._strip = _strip_thinking_tags

    def test_strips_single_think_block(self):
        text = "<think>reasoning here</think>Hello patient"
        self.assertEqual(self._strip(text), "Hello patient")

    def test_strips_multiple_think_blocks(self):
        text = "<think>a</think>Hello<think>b</think> world"
        self.assertEqual(self._strip(text), "Hello world")

    def test_strips_multiline_think_block(self):
        text = "<think>\nline1\nline2\n</think>Result"
        self.assertEqual(self._strip(text), "Result")

    def test_no_think_block_unchanged(self):
        text = "No thinking tags here"
        self.assertEqual(self._strip(text), "No thinking tags here")

    def test_empty_string(self):
        self.assertEqual(self._strip(""), "")


class ConversationEngineAsyncPostProcessingTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            email="patient_pp@test.com", password="pass123", role="patient"
        )

    @patch("companion.conversation_engine._generate_session_summary")
    @patch("companion.conversation_engine.faq_detector")
    def test_stores_faq_for_patient_mode_new_question(self, mock_faq, mock_summary):
        from companion.conversation_engine import _run_async_post_processing
        from companion.models import ConversationSession

        session = ConversationSession.objects.create(
            patient=self.user, mode="patient", message_count=3
        )
        client = MagicMock()

        _run_async_post_processing(
            self.user, session, "Where is my daughter?", "She visits Sunday",
            "patient", None, client, "llama-3.3-70b"
        )
        time.sleep(0.3)
        mock_faq.store_faq.assert_called_once_with(
            self.user, "Where is my daughter?", "She visits Sunday"
        )

    @patch("companion.conversation_engine._generate_session_summary")
    @patch("companion.conversation_engine.faq_detector")
    def test_skips_faq_storage_when_faq_result_exists(self, mock_faq, mock_summary):
        from companion.conversation_engine import _run_async_post_processing
        from companion.models import ConversationSession

        session = ConversationSession.objects.create(
            patient=self.user, mode="patient", message_count=3
        )
        faq_result = {"match_type": "exact", "answer": "cached"}

        _run_async_post_processing(
            self.user, session, "question", "reply",
            "patient", faq_result, MagicMock(), "llama"
        )
        time.sleep(0.3)
        mock_faq.store_faq.assert_not_called()

    @patch("companion.conversation_engine._generate_session_summary")
    @patch("companion.conversation_engine.faq_detector")
    def test_skips_faq_storage_for_caregiver_mode(self, mock_faq, mock_summary):
        from companion.conversation_engine import _run_async_post_processing
        from companion.models import ConversationSession

        session = ConversationSession.objects.create(
            patient=self.user, mode="caregiver", message_count=3
        )

        _run_async_post_processing(
            self.user, session, "question", "reply",
            "caregiver", None, MagicMock(), "llama"
        )
        time.sleep(0.3)
        mock_faq.store_faq.assert_not_called()

    @patch("companion.conversation_engine._generate_session_summary")
    @patch("companion.conversation_engine.faq_detector")
    def test_generates_summary_on_first_message(self, mock_faq, mock_summary):
        from companion.conversation_engine import _run_async_post_processing
        from companion.models import ConversationSession

        session = ConversationSession.objects.create(
            patient=self.user, mode="patient", message_count=1
        )

        _run_async_post_processing(
            self.user, session, "hi", "hello",
            "patient", None, MagicMock(), "llama"
        )
        time.sleep(0.3)
        mock_summary.assert_called_once()

    @patch("companion.conversation_engine._generate_session_summary")
    @patch("companion.conversation_engine.faq_detector")
    def test_generates_summary_every_10_messages(self, mock_faq, mock_summary):
        from companion.conversation_engine import _run_async_post_processing
        from companion.models import ConversationSession

        session = ConversationSession.objects.create(
            patient=self.user, mode="patient", message_count=10
        )

        _run_async_post_processing(
            self.user, session, "hi", "hello",
            "patient", None, MagicMock(), "llama"
        )
        time.sleep(0.3)
        mock_summary.assert_called_once()

    @patch("companion.conversation_engine._generate_session_summary")
    @patch("companion.conversation_engine.faq_detector")
    def test_no_summary_at_message_5(self, mock_faq, mock_summary):
        from companion.conversation_engine import _run_async_post_processing
        from companion.models import ConversationSession

        session = ConversationSession.objects.create(
            patient=self.user, mode="patient", message_count=5
        )

        _run_async_post_processing(
            self.user, session, "hi", "hello",
            "patient", None, MagicMock(), "llama"
        )
        time.sleep(0.3)
        mock_summary.assert_not_called()


class ConversationEngineChatTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            email="patient_chat@test.com", password="pass123", role="patient",
            first_name="Alice"
        )
        from companion.models import ConversationSession
        self.session = ConversationSession.objects.create(
            patient=self.user, mode="patient", message_count=0
        )

    @patch("companion.conversation_engine._run_async_post_processing")
    @patch("companion.conversation_engine._get_client")
    @patch("companion.conversation_engine.build_conversation_messages")
    @patch("companion.conversation_engine.build_system_prompt")
    @patch("companion.conversation_engine.rag_engine")
    @patch("companion.conversation_engine.faq_detector")
    @patch.dict(os.environ, {"GROQ_API_KEY": "test-key"})
    def test_chat_returns_reply_and_elapsed(
        self, mock_faq, mock_rag, mock_prompt, mock_msgs, mock_client, mock_post
    ):
        mock_faq.check_faq.return_value = None
        mock_faq.get_faq_context.return_value = ""
        mock_rag.retrieve.return_value = ""
        mock_prompt.return_value = "system prompt"
        mock_msgs.return_value = [{"role": "user", "content": "hello"}]

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Hi Alice!"
        mock_client.return_value.chat.completions.create.return_value = mock_response

        from companion.conversation_engine import chat
        reply, elapsed_ms = chat(self.user, self.session, "hello", "patient", "mild")

        self.assertEqual(reply, "Hi Alice!")
        self.assertIsInstance(elapsed_ms, int)
        self.assertGreaterEqual(elapsed_ms, 0)

    @patch("companion.conversation_engine._run_async_post_processing")
    @patch("companion.conversation_engine._get_client")
    @patch("companion.conversation_engine.build_conversation_messages")
    @patch("companion.conversation_engine.build_system_prompt")
    @patch("companion.conversation_engine.rag_engine")
    @patch("companion.conversation_engine.faq_detector")
    @patch.dict(os.environ, {"GROQ_API_KEY": "test-key"})
    def test_chat_exact_faq_match_skips_llm(
        self, mock_faq, mock_rag, mock_prompt, mock_msgs, mock_client, mock_post
    ):
        mock_faq.check_faq.return_value = {
            "match_type": "exact",
            "answer": "Your daughter Sarah visits on Sunday.",
            "similarity": 0.92,
            "faq_id": 1,
        }

        from companion.conversation_engine import chat
        reply, elapsed_ms = chat(
            self.user, self.session, "Where is my daughter?", "patient", "mild"
        )

        self.assertEqual(reply, "Your daughter Sarah visits on Sunday.")
        self.assertEqual(elapsed_ms, 0)
        mock_client.return_value.chat.completions.create.assert_not_called()

    @patch("companion.conversation_engine._run_async_post_processing")
    @patch("companion.conversation_engine._get_client")
    @patch("companion.conversation_engine.build_conversation_messages")
    @patch("companion.conversation_engine.build_system_prompt")
    @patch("companion.conversation_engine.rag_engine")
    @patch("companion.conversation_engine.faq_detector")
    @patch.dict(os.environ, {"GROQ_API_KEY": "test-key"})
    def test_chat_partial_faq_injects_into_prompt(
        self, mock_faq, mock_rag, mock_prompt, mock_msgs, mock_client, mock_post
    ):
        mock_faq.check_faq.return_value = {
            "match_type": "partial",
            "answer": "She visits Sunday",
            "similarity": 0.72,
            "faq_id": 2,
        }
        mock_faq.get_faq_context.return_value = "FAQ context"
        mock_rag.retrieve.return_value = ""
        mock_prompt.return_value = "base prompt"
        mock_msgs.return_value = []

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Your daughter visits Sunday."
        mock_client.return_value.chat.completions.create.return_value = mock_response

        from companion.conversation_engine import chat
        reply, _ = chat(
            self.user, self.session, "When does Sarah come?", "patient", "mild"
        )

        create_call = mock_client.return_value.chat.completions.create
        call_kwargs = create_call.call_args[1]
        system_msg = call_kwargs["messages"][0]["content"]
        self.assertIn("similar question before", system_msg)
        self.assertIn("She visits Sunday", system_msg)

    @patch("companion.conversation_engine._run_async_post_processing")
    @patch("companion.conversation_engine._get_client")
    @patch("companion.conversation_engine.build_conversation_messages")
    @patch("companion.conversation_engine.build_system_prompt")
    @patch("companion.conversation_engine.rag_engine")
    @patch("companion.conversation_engine.faq_detector")
    @patch.dict(os.environ, {"GROQ_API_KEY": "test-key"})
    def test_chat_caregiver_mode_skips_faq(
        self, mock_faq, mock_rag, mock_prompt, mock_msgs, mock_client, mock_post
    ):
        mock_rag.retrieve.return_value = ""
        mock_prompt.return_value = "system"
        mock_msgs.return_value = []

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Clinical answer"
        mock_client.return_value.chat.completions.create.return_value = mock_response

        self.session.mode = "caregiver"
        self.session.save()

        from companion.conversation_engine import chat
        chat(self.user, self.session, "What stage is the patient?", "caregiver", "mild")

        mock_faq.check_faq.assert_not_called()

    @patch("companion.conversation_engine._run_async_post_processing")
    @patch("companion.conversation_engine._get_client")
    @patch("companion.conversation_engine.build_conversation_messages")
    @patch("companion.conversation_engine.build_system_prompt")
    @patch("companion.conversation_engine.rag_engine")
    @patch("companion.conversation_engine.faq_detector")
    @patch.dict(os.environ, {"GROQ_API_KEY": "test-key", "COMPANION_LLM_MODEL": "deepseek-r1"})
    def test_chat_strips_thinking_tags_for_deepseek(
        self, mock_faq, mock_rag, mock_prompt, mock_msgs, mock_client, mock_post
    ):
        mock_faq.check_faq.return_value = None
        mock_faq.get_faq_context.return_value = ""
        mock_rag.retrieve.return_value = ""
        mock_prompt.return_value = "system"
        mock_msgs.return_value = []

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = (
            "<think>reasoning</think>Hello Alice, how are you?"
        )
        mock_client.return_value.chat.completions.create.return_value = mock_response

        from companion.conversation_engine import chat
        reply, _ = chat(self.user, self.session, "hi", "patient", "mild")
        self.assertEqual(reply, "Hello Alice, how are you?")

    @patch("companion.conversation_engine._run_async_post_processing")
    @patch("companion.conversation_engine._get_client")
    @patch("companion.conversation_engine.build_conversation_messages")
    @patch("companion.conversation_engine.build_system_prompt")
    @patch("companion.conversation_engine.rag_engine")
    @patch("companion.conversation_engine.faq_detector")
    @patch.dict(os.environ, {"GROQ_API_KEY": "test-key"})
    def test_chat_saves_messages_to_db(
        self, mock_faq, mock_rag, mock_prompt, mock_msgs, mock_client, mock_post
    ):
        from companion.models import ConversationMessage

        mock_faq.check_faq.return_value = None
        mock_faq.get_faq_context.return_value = ""
        mock_rag.retrieve.return_value = ""
        mock_prompt.return_value = "system"
        mock_msgs.return_value = []

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Reply"
        mock_client.return_value.chat.completions.create.return_value = mock_response

        from companion.conversation_engine import chat
        chat(self.user, self.session, "user msg", "patient", "mild")

        msgs = ConversationMessage.objects.filter(session=self.session)
        self.assertEqual(msgs.count(), 2)
        self.assertEqual(msgs.first().role, "user")
        self.assertEqual(msgs.last().role, "assistant")

    @patch("companion.conversation_engine._run_async_post_processing")
    @patch("companion.conversation_engine._get_client")
    @patch("companion.conversation_engine.build_conversation_messages")
    @patch("companion.conversation_engine.build_system_prompt")
    @patch("companion.conversation_engine.rag_engine")
    @patch("companion.conversation_engine.faq_detector")
    @patch.dict(os.environ, {"GROQ_API_KEY": "test-key"})
    def test_chat_appends_rag_context_to_prompt(
        self, mock_faq, mock_rag, mock_prompt, mock_msgs, mock_client, mock_post
    ):
        mock_faq.check_faq.return_value = None
        mock_faq.get_faq_context.return_value = ""
        mock_rag.retrieve.return_value = "RAG passage about sundowning"
        mock_prompt.return_value = "base"
        mock_msgs.return_value = []

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "answer"
        mock_client.return_value.chat.completions.create.return_value = mock_response

        from companion.conversation_engine import chat
        chat(self.user, self.session, "what is sundowning", "patient", "mild")

        call_kwargs = mock_client.return_value.chat.completions.create.call_args[1]
        system_content = call_kwargs["messages"][0]["content"]
        self.assertIn("RAG passage about sundowning", system_content)


class ConversationEngineChatStreamTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            email="patient_stream@test.com", password="pass123", role="patient",
            first_name="Bob"
        )
        from companion.models import ConversationSession
        self.session = ConversationSession.objects.create(
            patient=self.user, mode="patient", message_count=0
        )

    @patch("companion.conversation_engine._run_async_post_processing")
    @patch("companion.conversation_engine._get_client")
    @patch("companion.conversation_engine.build_conversation_messages")
    @patch("companion.conversation_engine.build_system_prompt")
    @patch("companion.conversation_engine.rag_engine")
    @patch("companion.conversation_engine.faq_detector")
    @patch.dict(os.environ, {"GROQ_API_KEY": "test-key"})
    def test_stream_yields_chunks_and_done(
        self, mock_faq, mock_rag, mock_prompt, mock_msgs, mock_client, mock_post
    ):
        mock_faq.check_faq.return_value = None
        mock_faq.get_faq_context.return_value = ""
        mock_rag.retrieve.return_value = ""
        mock_prompt.return_value = "system"
        mock_msgs.return_value = []

        chunk1 = MagicMock()
        chunk1.choices = [MagicMock()]
        chunk1.choices[0].delta.content = "Hello "
        chunk2 = MagicMock()
        chunk2.choices = [MagicMock()]
        chunk2.choices[0].delta.content = "Bob!"
        chunk3 = MagicMock()
        chunk3.choices = []

        mock_client.return_value.chat.completions.create.return_value = iter(
            [chunk1, chunk2, chunk3]
        )

        from companion.conversation_engine import chat_stream
        results = list(chat_stream(self.user, self.session, "hi", "patient", "mild"))

        chunk_results = [r for r in results if r["type"] == "chunk"]
        done_results = [r for r in results if r["type"] == "done"]

        self.assertEqual(len(chunk_results), 2)
        self.assertEqual(chunk_results[0]["content"], "Hello ")
        self.assertEqual(chunk_results[1]["content"], "Bob!")
        self.assertEqual(len(done_results), 1)
        self.assertEqual(done_results[0]["content"], "Hello Bob!")
        self.assertIn("response_time_ms", done_results[0])

    @patch("companion.conversation_engine._run_async_post_processing")
    @patch("companion.conversation_engine._get_client")
    @patch("companion.conversation_engine.build_conversation_messages")
    @patch("companion.conversation_engine.build_system_prompt")
    @patch("companion.conversation_engine.rag_engine")
    @patch("companion.conversation_engine.faq_detector")
    @patch.dict(os.environ, {"GROQ_API_KEY": "test-key"})
    def test_stream_faq_exact_match_yields_faq_hit(
        self, mock_faq, mock_rag, mock_prompt, mock_msgs, mock_client, mock_post
    ):
        mock_faq.check_faq.return_value = {
            "match_type": "exact",
            "answer": "Cached answer",
            "similarity": 0.90,
            "faq_id": 5,
        }

        from companion.conversation_engine import chat_stream
        results = list(
            chat_stream(self.user, self.session, "question", "patient", "mild")
        )

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["type"], "faq_hit")
        self.assertEqual(results[0]["content"], "Cached answer")
        self.assertTrue(results[0]["is_faq"])
        mock_client.return_value.chat.completions.create.assert_not_called()


class ConversationEngineSessionSummaryTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            email="patient_summ@test.com", password="pass123", role="patient"
        )
        from companion.models import ConversationSession, ConversationMessage
        self.session = ConversationSession.objects.create(
            patient=self.user, mode="patient", summary=""
        )
        ConversationMessage.objects.create(
            session=self.session, role="user", content_text="Hello"
        )
        ConversationMessage.objects.create(
            session=self.session, role="assistant", content_text="Hi there!"
        )

    def test_generates_first_summary_as_title(self):
        from companion.conversation_engine import _generate_session_summary

        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Greeting Conversation"
        mock_client.chat.completions.create.return_value = mock_response

        _generate_session_summary(self.session, mock_client, "llama-3.3-70b")

        self.session.refresh_from_db()
        self.assertEqual(self.session.summary, "Greeting Conversation")

    def test_appends_subsequent_summary(self):
        from companion.conversation_engine import _generate_session_summary

        self.session.summary = "Initial title"
        self.session.save()

        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Patient discussed family"
        mock_client.chat.completions.create.return_value = mock_response

        _generate_session_summary(self.session, mock_client, "llama-3.3-70b")

        self.session.refresh_from_db()
        self.assertIn("Initial title", self.session.summary)
        self.assertIn("Patient discussed family", self.session.summary)
        self.assertIn(" | ", self.session.summary)

    def test_no_messages_returns_early(self):
        from companion.conversation_engine import _generate_session_summary
        from companion.models import ConversationSession

        empty_session = ConversationSession.objects.create(
            patient=self.user, mode="patient", summary=""
        )
        mock_client = MagicMock()
        _generate_session_summary(empty_session, mock_client, "llama")
        mock_client.chat.completions.create.assert_not_called()

    def test_strips_thinking_for_deepseek_model(self):
        from companion.conversation_engine import _generate_session_summary

        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "<think>r</think>Summary text"
        mock_client.chat.completions.create.return_value = mock_response

        _generate_session_summary(self.session, mock_client, "deepseek-r1")

        self.session.refresh_from_db()
        self.assertEqual(self.session.summary, "Summary text")


class ConversationEngineTranscribeTests(TestCase):

    def setUp(self):
        import companion.conversation_engine as mod
        self._mod = mod
        self._orig_client = mod._client

    def tearDown(self):
        self._mod._client = self._orig_client

    @patch("companion.conversation_engine._get_client")
    def test_transcribe_file_path(self, mock_get_client):
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.audio.transcriptions.create.return_value = MagicMock(
            text="  Hello world  "
        )

        audio_content = b"fake audio bytes"
        with patch("builtins.open", MagicMock(
            return_value=io.BytesIO(audio_content)
        )):
            from companion.conversation_engine import transcribe_audio
            result = transcribe_audio("/path/to/audio.webm")

        self.assertEqual(result, "Hello world")
        mock_client.audio.transcriptions.create.assert_called_once()
        call_kwargs = mock_client.audio.transcriptions.create.call_args[1]
        self.assertEqual(call_kwargs["model"], "whisper-large-v3-turbo")
        self.assertEqual(call_kwargs["language"], "en")

    @patch("companion.conversation_engine._get_client")
    def test_transcribe_file_like_object(self, mock_get_client):
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.audio.transcriptions.create.return_value = MagicMock(
            text="transcribed text"
        )

        fake_file = io.BytesIO(b"audio data")
        fake_file.name = "recording.mp3"

        from companion.conversation_engine import transcribe_audio
        result = transcribe_audio(fake_file)

        self.assertEqual(result, "transcribed text")

    @patch("companion.conversation_engine._get_client")
    def test_transcribe_unsupported_type_raises(self, mock_get_client):
        from companion.conversation_engine import transcribe_audio
        with self.assertRaises(ValueError) as ctx:
            transcribe_audio(12345)
        self.assertIn("Unsupported audio_file type", str(ctx.exception))


# =============================================================================
# 2. context_builder.py tests
# =============================================================================

class ContextBuilderCalculateAgeTests(TestCase):

    def test_calculates_age_correctly(self):
        from companion.context_builder import _calculate_age
        dob = date(1950, 1, 15)
        age = _calculate_age(dob)
        expected = date.today().year - 1950 - (
            (date.today().month, date.today().day) < (1, 15)
        )
        self.assertEqual(age, expected)

    def test_birthday_today(self):
        from companion.context_builder import _calculate_age
        today = date.today()
        dob = date(today.year - 70, today.month, today.day)
        self.assertEqual(_calculate_age(dob), 70)

    def test_birthday_tomorrow(self):
        from companion.context_builder import _calculate_age
        tomorrow = date.today() + timedelta(days=1)
        dob = date(date.today().year - 70, tomorrow.month, tomorrow.day)
        self.assertEqual(_calculate_age(dob), 69)


class ContextBuilderMriSectionTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            email="patient_mri@test.com", password="pass123", role="patient"
        )

    def test_caregiver_mode_no_scans(self):
        from companion.context_builder import _build_mri_section
        result = _build_mri_section(self.user, "caregiver")
        self.assertIn("No scans on file", result)

    def test_patient_mode_no_scans(self):
        from companion.context_builder import _build_mri_section
        result = _build_mri_section(self.user, "patient")
        self.assertIn("No scans on file", result)

    def test_patient_mode_with_scan(self):
        from companion.context_builder import _build_mri_section
        from detection.models import DetectionResult
        from django.core.files.uploadedfile import SimpleUploadedFile
        DetectionResult.objects.create(
            patient=self.user, status="completed",
            predicted_class="dementia", confidence_score=0.87,
            uploaded_file=SimpleUploadedFile("t.jpg", b"x", "image/jpeg"),
            file_size=100,
        )
        result = _build_mri_section(self.user, "patient")
        self.assertIn("87%", result)


class ContextBuilderSessionSummaryTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            email="patient_ss@test.com", password="pass123", role="patient"
        )

    def test_no_sessions_returns_empty(self):
        from companion.context_builder import _build_session_summary_section
        result = _build_session_summary_section(self.user)
        self.assertEqual(result, "")

    def test_returns_session_summaries(self):
        from companion.context_builder import _build_session_summary_section
        from companion.models import ConversationSession

        ConversationSession.objects.create(
            patient=self.user, mode="patient", summary="Talked about family"
        )
        result = _build_session_summary_section(self.user)
        self.assertIn("SESSION CONTINUITY CONTEXT", result)
        self.assertIn("Talked about family", result)


class ContextBuilderLifeStoryTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            email="patient_ls@test.com", password="pass123", role="patient"
        )

    def test_no_entries_returns_empty(self):
        from companion.context_builder import _build_life_story_section
        result = _build_life_story_section(self.user)
        self.assertEqual(result, "")

    def test_builds_life_story_with_entries(self):
        from companion.context_builder import _build_life_story_section
        from companion.models import LifeStoryEntry

        LifeStoryEntry.objects.create(
            patient=self.user,
            category="family",
            title="Daughter Sarah",
            description="Sarah visits every Sunday at 2pm",
            people_involved=["Sarah"],
            time_period="Weekly",
            trigger_questions=["Where is my daughter?"],
            emotional_valence="positive",
            priority=2,
        )
        result = _build_life_story_section(self.user)
        self.assertIn("LIFE STORY", result)
        self.assertIn("Daughter Sarah", result)
        self.assertIn("Sarah visits every Sunday", result)
        self.assertIn("SPECIFIC ANSWERS", result)

    def test_sensitive_topics_warning(self):
        from companion.context_builder import _build_life_story_section
        from companion.models import LifeStoryEntry

        LifeStoryEntry.objects.create(
            patient=self.user,
            category="memories",
            title="Husband's passing",
            description="Husband passed away in 2020",
            emotional_valence="sensitive",
            priority=1,
        )
        result = _build_life_story_section(self.user)
        self.assertIn("AVOID", result)
        self.assertIn("Husband's passing", result)

    def test_voice_entries_show_indicator(self):
        from companion.context_builder import _build_life_story_section
        from companion.models import LifeStoryEntry

        LifeStoryEntry.objects.create(
            patient=self.user,
            category="daily_routine",
            title="Morning routine",
            entry_type="voice",
            audio_transcript="I wake up at 7am and take my pills",
            emotional_valence="neutral",
            priority=1,
        )
        result = _build_life_story_section(self.user)
        self.assertIn("🎤", result)

    def test_care_instructions_category(self):
        from companion.context_builder import _build_life_story_section
        from companion.models import LifeStoryEntry

        LifeStoryEntry.objects.create(
            patient=self.user,
            category="instructions",
            title="Bedtime routine",
            description="Always play soft music before sleep",
            emotional_valence="neutral",
            priority=3,
        )
        result = _build_life_story_section(self.user)
        self.assertIn("CARE INSTRUCTIONS", result)
        self.assertIn("Bedtime routine", result)


class ContextBuilderBuildSystemPromptTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            email="patient_sp@test.com", password="pass123", role="patient",
            first_name="Alice"
        )
        from authx.models import PatientProfile
        PatientProfile.objects.create(
            user=self.user,
            date_of_birth=date(1955, 6, 15),
            gender="F",
            current_medications="Donepezil 10mg",
            allergies="Penicillin",
            medical_history={"hypertension": "diagnosed 2010"},
        )

    @patch("companion.context_builder._build_mri_section")
    @patch("companion.context_builder._build_life_story_section")
    @patch("companion.context_builder._build_session_summary_section")
    def test_patient_mode_prompt_contains_patient_info(
        self, mock_ss, mock_ls, mock_mri
    ):
        from companion.context_builder import build_system_prompt
        mock_mri.return_value = "- Latest MRI: No scans"
        mock_ls.return_value = ""
        mock_ss.return_value = ""

        result = build_system_prompt(self.user, "patient", "mild")
        self.assertIn("Alice", result)
        self.assertIn("Female", result)
        self.assertIn("Donepezil", result)
        self.assertIn("Penicillin", result)
        self.assertIn("hypertension", result)

    @patch("companion.context_builder._build_mri_section")
    @patch("companion.context_builder._build_life_story_section")
    def test_caregiver_mode_prompt(self, mock_ls, mock_mri):
        from companion.context_builder import build_system_prompt
        mock_mri.return_value = "- MRI History: No scans"
        mock_ls.return_value = ""

        result = build_system_prompt(self.user, "caregiver", "moderate")
        self.assertIn("Alice", result)
        self.assertIn("moderate", result.lower())

    @patch("companion.context_builder._build_mri_section")
    @patch("companion.context_builder._build_life_story_section")
    @patch("companion.context_builder._build_session_summary_section")
    def test_prompt_uses_email_fallback_when_no_first_name(
        self, mock_ss, mock_ls, mock_mri
    ):
        from companion.context_builder import build_system_prompt
        mock_mri.return_value = ""
        mock_ls.return_value = ""
        mock_ss.return_value = ""

        user_no_name = User.objects.create_user(
            email="noname@test.com", password="pass123", role="patient"
        )
        result = build_system_prompt(user_no_name, "patient", "mild")
        self.assertIn("noname", result)


class ContextBuilderBuildConversationMessagesTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            email="patient_bm@test.com", password="pass123", role="patient"
        )
        from companion.models import ConversationSession, ConversationMessage
        self.session = ConversationSession.objects.create(
            patient=self.user, mode="patient"
        )
        ConversationMessage.objects.create(
            session=self.session, role="user", content_text="Hello"
        )
        ConversationMessage.objects.create(
            session=self.session, role="assistant", content_text="Hi there"
        )
        ConversationMessage.objects.create(
            session=self.session, role="user", content_text="How are you?"
        )

    def test_returns_messages_in_order(self):
        from companion.context_builder import build_conversation_messages
        msgs = build_conversation_messages(self.session)
        self.assertEqual(len(msgs), 3)
        self.assertEqual(msgs[0]["role"], "user")
        self.assertEqual(msgs[0]["content"], "Hello")
        self.assertEqual(msgs[1]["role"], "assistant")
        self.assertEqual(msgs[2]["content"], "How are you?")

    def test_respects_limit(self):
        from companion.context_builder import build_conversation_messages
        msgs = build_conversation_messages(self.session, limit=2)
        self.assertEqual(len(msgs), 2)
        self.assertEqual(msgs[0]["role"], "assistant")
        self.assertEqual(msgs[1]["content"], "How are you?")

    def test_empty_session_returns_empty_list(self):
        from companion.context_builder import build_conversation_messages
        from companion.models import ConversationSession

        empty_session = ConversationSession.objects.create(
            patient=self.user, mode="patient"
        )
        msgs = build_conversation_messages(empty_session)
        self.assertEqual(msgs, [])


# =============================================================================
# 3. faq_detector.py tests
# =============================================================================

class FaqDetectorGetModelTests(TestCase):

    def setUp(self):
        import companion.faq_detector as mod
        self._mod = mod
        self._orig_model = mod._model

    def tearDown(self):
        self._mod._model = self._orig_model

    @patch("companion.faq_detector.SentenceTransformer", create=True)
    def test_lazy_loads_model(self, mock_st_cls):
        self._mod._model = None
        with patch.dict("sys.modules", {"sentence_transformers": MagicMock()}):
            from sentence_transformers import SentenceTransformer
            with patch(
                "companion.faq_detector.SentenceTransformer",
                create=True
            ):
                mock_st = MagicMock()
                with patch.object(
                    self._mod, "_get_model",
                    wraps=self._mod._get_model
                ):
                    # Actually test the function
                    self._mod._model = None
                    # Patch the import inside the function
                    mock_module = MagicMock()
                    mock_module.SentenceTransformer.return_value = mock_st
                    with patch.dict(
                        "sys.modules",
                        {"sentence_transformers": mock_module}
                    ):
                        result = self._mod._get_model()
                        self.assertEqual(result, mock_st)

    def test_returns_cached_model(self):
        fake_model = MagicMock()
        self._mod._model = fake_model
        result = self._mod._get_model()
        self.assertEqual(result, fake_model)

    def test_returns_none_on_import_failure(self):
        import logging
        self._mod._model = None
        with self.assertLogs("companion.faq_detector", level="ERROR"):
            with patch.dict("sys.modules", {"sentence_transformers": None}):
                with patch("builtins.__import__", side_effect=ImportError("no module")):
                    result = self._mod._get_model()
                    self.assertIsNone(result)


class FaqDetectorSerializationTests(TestCase):

    def test_serialize_and_deserialize_roundtrip(self):
        from companion.faq_detector import _serialize_embedding, _deserialize_embedding

        original = np.random.randn(384).astype(np.float32)
        serialized = _serialize_embedding(original)
        self.assertIsInstance(serialized, bytes)

        deserialized = _deserialize_embedding(serialized)
        np.testing.assert_array_almost_equal(original, deserialized)

    def test_serialize_preserves_float32(self):
        from companion.faq_detector import _serialize_embedding, _deserialize_embedding

        original = np.array([1.0, 2.0, 3.0], dtype=np.float64)
        serialized = _serialize_embedding(original)
        deserialized = _deserialize_embedding(serialized)
        self.assertEqual(deserialized.dtype, np.float32)


class FaqDetectorCosineSimilarityTests(TestCase):

    def test_identical_vectors_similarity_one(self):
        from companion.faq_detector import _cosine_similarity_batch

        query = np.array([1.0, 0.0, 0.0])
        faqs = np.array([[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]])
        sims = _cosine_similarity_batch(query, faqs)
        self.assertAlmostEqual(float(sims[0]), 1.0, places=5)
        self.assertAlmostEqual(float(sims[1]), 0.0, places=5)

    def test_orthogonal_vectors_zero(self):
        from companion.faq_detector import _cosine_similarity_batch

        query = np.array([1.0, 0.0])
        faqs = np.array([[0.0, 1.0]])
        sims = _cosine_similarity_batch(query, faqs)
        self.assertAlmostEqual(float(sims[0]), 0.0, places=5)

    def test_batch_returns_correct_shape(self):
        from companion.faq_detector import _cosine_similarity_batch

        query = np.random.randn(384)
        faqs = np.random.randn(10, 384)
        sims = _cosine_similarity_batch(query, faqs)
        self.assertEqual(sims.shape, (10,))


class FaqDetectorCheckFaqTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            email="patient_faq_check@test.com", password="pass123", role="patient"
        )
        import companion.faq_detector as mod
        self._mod = mod
        self._orig_model = mod._model

    def tearDown(self):
        self._mod._model = self._orig_model

    def test_returns_none_when_model_unavailable(self):
        self._mod._model = None
        with patch.object(self._mod, "_get_model", return_value=None):
            result = self._mod.check_faq(self.user, "Where is my daughter?")
            self.assertIsNone(result)

    def test_returns_none_when_no_faqs_exist(self):
        mock_model = MagicMock()
        with patch.object(self._mod, "_get_model", return_value=mock_model):
            result = self._mod.check_faq(self.user, "Where is my daughter?")
            self.assertIsNone(result)

    def test_exact_match_returns_dict(self):
        from companion.models import PatientFAQ
        from companion.faq_detector import _serialize_embedding

        embedding = np.random.randn(384).astype(np.float32)
        embedding = embedding / np.linalg.norm(embedding)

        faq = PatientFAQ.objects.create(
            patient=self.user,
            question_text="Where is my daughter?",
            answer_text="Sarah visits on Sunday at 2pm",
            category="family",
            ask_count=3,
            question_embedding=_serialize_embedding(embedding),
        )

        mock_model = MagicMock()
        mock_model.encode.return_value = embedding  # Same embedding = similarity ~1.0

        with patch.object(self._mod, "_get_model", return_value=mock_model):
            result = self._mod.check_faq(self.user, "Where is my daughter?")

        self.assertIsNotNone(result)
        self.assertEqual(result["match_type"], "exact")
        self.assertEqual(result["answer"], "Sarah visits on Sunday at 2pm")
        self.assertGreaterEqual(result["similarity"], 0.85)

        faq.refresh_from_db()
        self.assertEqual(faq.ask_count, 4)

    def test_partial_match_returns_dict(self):
        from companion.models import PatientFAQ
        from companion.faq_detector import _serialize_embedding

        stored_emb = np.array([1.0, 0.0, 0.0] + [0.0] * 381, dtype=np.float32)
        stored_emb = stored_emb / np.linalg.norm(stored_emb)

        PatientFAQ.objects.create(
            patient=self.user,
            question_text="Where is my daughter?",
            answer_text="Sarah visits Sunday",
            category="family",
            ask_count=1,
            question_embedding=_serialize_embedding(stored_emb),
        )

        # Query embedding with angle giving cosine ~0.7
        query_emb = np.array([0.7, 0.7, 0.1] + [0.0] * 381, dtype=np.float32)
        query_emb = query_emb / np.linalg.norm(query_emb)

        mock_model = MagicMock()
        mock_model.encode.return_value = query_emb

        with patch.object(self._mod, "_get_model", return_value=mock_model):
            result = self._mod.check_faq(self.user, "When does Sarah come?")

        self.assertIsNotNone(result)
        self.assertEqual(result["match_type"], "partial")

    def test_low_similarity_returns_none(self):
        from companion.models import PatientFAQ
        from companion.faq_detector import _serialize_embedding

        stored_emb = np.array([1.0, 0.0, 0.0] + [0.0] * 381, dtype=np.float32)
        stored_emb = stored_emb / np.linalg.norm(stored_emb)

        PatientFAQ.objects.create(
            patient=self.user,
            question_text="Where is my daughter?",
            answer_text="She visits Sunday",
            category="family",
            ask_count=1,
            question_embedding=_serialize_embedding(stored_emb),
        )

        # Orthogonal query -> similarity ~0
        query_emb = np.array([0.0, 1.0, 0.0] + [0.0] * 381, dtype=np.float32)
        query_emb = query_emb / np.linalg.norm(query_emb)

        mock_model = MagicMock()
        mock_model.encode.return_value = query_emb

        with patch.object(self._mod, "_get_model", return_value=mock_model):
            result = self._mod.check_faq(self.user, "What is for lunch?")

        self.assertIsNone(result)

    def test_computes_missing_embeddings(self):
        from companion.models import PatientFAQ
        from companion.faq_detector import _serialize_embedding

        PatientFAQ.objects.create(
            patient=self.user,
            question_text="Where is my daughter?",
            answer_text="She visits Sunday",
            category="family",
            ask_count=1,
            question_embedding=None,  # No pre-computed embedding
        )

        embedding = np.random.randn(384).astype(np.float32)
        embedding = embedding / np.linalg.norm(embedding)

        mock_model = MagicMock()
        mock_model.encode.side_effect = [
            embedding,  # query encoding
            np.array([embedding]),  # batch encoding of missing FAQ
        ]

        with patch.object(self._mod, "_get_model", return_value=mock_model):
            self._mod.check_faq(self.user, "test question")

        # Verify the FAQ now has its embedding saved
        faq = PatientFAQ.objects.get(patient=self.user)
        self.assertIsNotNone(faq.question_embedding)


class FaqDetectorStoreFaqTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            email="patient_faq_store@test.com", password="pass123", role="patient"
        )
        import companion.faq_detector as mod
        self._mod = mod
        self._orig_model = mod._model

    def tearDown(self):
        self._mod._model = self._orig_model

    def test_creates_new_faq_entry(self):
        from companion.models import PatientFAQ

        embedding = np.random.randn(384).astype(np.float32)
        mock_model = MagicMock()
        mock_model.encode.return_value = embedding

        with patch.object(self._mod, "_get_model", return_value=mock_model):
            result = self._mod.store_faq(
                self.user, "Where is my daughter?", "She visits Sunday", "family"
            )

        self.assertIsNotNone(result)
        self.assertEqual(PatientFAQ.objects.filter(patient=self.user).count(), 1)
        faq = PatientFAQ.objects.get(patient=self.user)
        self.assertEqual(faq.question_text, "Where is my daughter?")
        self.assertEqual(faq.answer_text, "She visits Sunday")
        self.assertEqual(faq.category, "family")
        self.assertIsNotNone(faq.question_embedding)

    def test_updates_existing_faq_on_high_similarity(self):
        from companion.models import PatientFAQ
        from companion.faq_detector import _serialize_embedding

        embedding = np.random.randn(384).astype(np.float32)
        embedding = embedding / np.linalg.norm(embedding)

        PatientFAQ.objects.create(
            patient=self.user,
            question_text="Where is my daughter?",
            answer_text="Old answer",
            category="family",
            ask_count=2,
            question_embedding=_serialize_embedding(embedding),
        )

        mock_model = MagicMock()
        mock_model.encode.return_value = embedding  # Same embedding = high similarity

        with patch.object(self._mod, "_get_model", return_value=mock_model):
            self._mod.store_faq(
                self.user, "Where is my daughter?", "New answer", "family"
            )

        self.assertEqual(PatientFAQ.objects.filter(patient=self.user).count(), 1)
        faq = PatientFAQ.objects.get(patient=self.user)
        self.assertEqual(faq.answer_text, "New answer")
        self.assertEqual(faq.ask_count, 3)

    def test_creates_faq_without_model(self):
        from companion.models import PatientFAQ

        with patch.object(self._mod, "_get_model", return_value=None):
            result = self._mod.store_faq(
                self.user, "What day is it?", "It's Monday", "orientation"
            )

        self.assertIsNotNone(result)
        faq = PatientFAQ.objects.get(patient=self.user)
        self.assertIsNone(faq.question_embedding)


class FaqDetectorGetFaqContextTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            email="patient_faq_ctx@test.com", password="pass123", role="patient"
        )

    def test_returns_empty_when_no_faqs(self):
        from companion.faq_detector import get_faq_context
        result = get_faq_context(self.user)
        self.assertEqual(result, "")

    def test_returns_formatted_faq_context(self):
        from companion.faq_detector import get_faq_context
        from companion.models import PatientFAQ

        PatientFAQ.objects.create(
            patient=self.user,
            question_text="Where is my daughter?",
            answer_text="Sarah visits on Sunday",
            ask_count=5,
        )
        PatientFAQ.objects.create(
            patient=self.user,
            question_text="What day is it?",
            answer_text="It's Monday",
            ask_count=3,
        )

        result = get_faq_context(self.user, limit=5)
        self.assertIn("FREQUENTLY ASKED QUESTIONS", result)
        self.assertIn("Where is my daughter?", result)
        self.assertIn("Sarah visits on Sunday", result)
        self.assertIn("asked 5 times", result)
        self.assertIn("What day is it?", result)

    def test_respects_limit(self):
        from companion.faq_detector import get_faq_context
        from companion.models import PatientFAQ

        for i in range(10):
            PatientFAQ.objects.create(
                patient=self.user,
                question_text=f"Question {i}?",
                answer_text=f"Answer {i}",
                ask_count=10 - i,
            )

        result = get_faq_context(self.user, limit=3)
        self.assertIn("Question 0", result)
        self.assertIn("Question 2", result)
        self.assertNotIn("Question 5", result)


# =============================================================================
# 4. tts_service.py tests
# =============================================================================

class TtsServiceEnsureEdgeTtsTests(TestCase):

    def setUp(self):
        import companion.tts_service as mod
        self._mod = mod
        self._orig = mod._edge_tts

    def tearDown(self):
        self._mod._edge_tts = self._orig

    def test_lazy_imports_edge_tts(self):
        self._mod._edge_tts = None
        mock_edge = MagicMock()
        with patch.dict("sys.modules", {"edge_tts": mock_edge}):
            result = self._mod._ensure_edge_tts()
            self.assertEqual(result, mock_edge)

    def test_returns_cached_module(self):
        fake_module = MagicMock()
        self._mod._edge_tts = fake_module
        result = self._mod._ensure_edge_tts()
        self.assertEqual(result, fake_module)


class TtsServiceSynthesizeTests(TestCase):

    def setUp(self):
        import companion.tts_service as mod
        self._mod = mod
        self._orig = mod._edge_tts

    def tearDown(self):
        self._mod._edge_tts = self._orig

    @patch("companion.tts_service.os.makedirs")
    @patch("companion.tts_service.uuid.uuid4")
    def test_synthesize_returns_filepath(self, mock_uuid, mock_makedirs):
        mock_uuid.return_value = MagicMock(hex="abc123")

        mock_communicate_instance = MagicMock()
        mock_edge = MagicMock()
        mock_edge.Communicate.return_value = mock_communicate_instance

        import asyncio
        future = asyncio.Future()
        future.set_result(None)
        mock_communicate_instance.save.return_value = future

        self._mod._edge_tts = mock_edge

        result = self._mod.synthesize("Hello world", "en-US-AriaNeural")

        self.assertIn("/media/companion_audio/abc123.mp3", result)

    def test_synthesize_returns_none_on_exception(self):
        self._mod._edge_tts = None
        with patch.dict("sys.modules", {"edge_tts": None}):
            with patch("builtins.__import__", side_effect=ImportError("no edge_tts")):
                result = self._mod.synthesize("text")
                self.assertIsNone(result)


class TtsServiceAsyncGenerateTests(TestCase):

    def setUp(self):
        import companion.tts_service as mod
        self._mod = mod
        self._orig_tasks = mod._tts_tasks.copy()

    def tearDown(self):
        self._mod._tts_tasks.clear()
        self._mod._tts_tasks.update(self._orig_tasks)

    @patch("companion.tts_service.synthesize")
    def test_generate_tts_async_returns_task_id(self, mock_synth):
        mock_synth.return_value = "/media/companion_audio/test.mp3"
        task_id = self._mod.generate_tts_async("Hello", task_id="test-task-1")
        self.assertEqual(task_id, "test-task-1")
        time.sleep(0.3)

        status = self._mod.get_tts_status("test-task-1")
        self.assertEqual(status["status"], "completed")
        self.assertEqual(status["audio_url"], "/media/companion_audio/test.mp3")

    @patch("companion.tts_service.synthesize")
    def test_generate_tts_async_auto_generates_id(self, mock_synth):
        mock_synth.return_value = "/media/file.mp3"
        task_id = self._mod.generate_tts_async("text")
        self.assertIsNotNone(task_id)
        self.assertTrue(len(task_id) > 0)

    @patch("companion.tts_service.synthesize")
    def test_generate_tts_async_calls_on_complete(self, mock_synth):
        mock_synth.return_value = "/media/done.mp3"
        callback = MagicMock()

        self._mod.generate_tts_async(
            "Hello", task_id="cb-task", on_complete=callback
        )
        time.sleep(0.3)

        callback.assert_called_once_with("cb-task", "/media/done.mp3")

    @patch("companion.tts_service.synthesize")
    def test_generate_tts_async_handles_failure(self, mock_synth):
        mock_synth.side_effect = RuntimeError("TTS crash")
        self._mod.generate_tts_async("text", task_id="fail-task")
        time.sleep(0.3)

        status = self._mod.get_tts_status("fail-task")
        self.assertEqual(status["status"], "failed")
        self.assertIn("TTS crash", status["error"])


class TtsServiceStatusTests(TestCase):

    def setUp(self):
        import companion.tts_service as mod
        self._mod = mod
        self._orig_tasks = mod._tts_tasks.copy()

    def tearDown(self):
        self._mod._tts_tasks.clear()
        self._mod._tts_tasks.update(self._orig_tasks)

    def test_get_status_returns_none_for_unknown_task(self):
        result = self._mod.get_tts_status("nonexistent-id")
        self.assertIsNone(result)

    def test_get_status_returns_copy(self):
        self._mod._tts_tasks["test-id"] = {
            "status": "pending", "audio_url": None, "error": None
        }
        status = self._mod.get_tts_status("test-id")
        self.assertEqual(status["status"], "pending")
        status["status"] = "modified"
        original = self._mod._tts_tasks["test-id"]
        self.assertEqual(original["status"], "pending")


class TtsServiceCleanupTests(TestCase):

    def setUp(self):
        import companion.tts_service as mod
        self._mod = mod
        self._orig_tasks = mod._tts_tasks.copy()

    def tearDown(self):
        self._mod._tts_tasks.clear()
        self._mod._tts_tasks.update(self._orig_tasks)

    def test_cleanup_removes_task(self):
        self._mod._tts_tasks["to-remove"] = {
            "status": "completed", "audio_url": "/x.mp3", "error": None
        }
        self._mod.cleanup_tts_task("to-remove")
        self.assertIsNone(self._mod.get_tts_status("to-remove"))

    def test_cleanup_nonexistent_does_not_raise(self):
        self._mod.cleanup_tts_task("does-not-exist")


# =============================================================================
# 5. rag_engine.py tests
# =============================================================================

class RagEngineChunkTextTests(TestCase):

    def test_basic_chunking(self):
        from companion.rag_engine import _chunk_text

        text = "Para one.\n\nPara two.\n\nPara three."
        chunks = _chunk_text(text, chunk_size=50, overlap=10)
        self.assertGreater(len(chunks), 0)
        for chunk in chunks:
            self.assertTrue(len(chunk) > 0)

    def test_single_paragraph(self):
        from companion.rag_engine import _chunk_text

        text = "Just one paragraph with some text."
        chunks = _chunk_text(text, chunk_size=1000, overlap=50)
        self.assertEqual(len(chunks), 1)
        self.assertEqual(chunks[0], "Just one paragraph with some text.")

    def test_empty_text(self):
        from companion.rag_engine import _chunk_text

        chunks = _chunk_text("", chunk_size=500, overlap=50)
        self.assertEqual(chunks, [])

    def test_large_chunk_size_single_chunk(self):
        from companion.rag_engine import _chunk_text

        text = "A.\n\nB.\n\nC."
        chunks = _chunk_text(text, chunk_size=10000, overlap=100)
        self.assertEqual(len(chunks), 1)

    def test_small_chunk_size_multiple_chunks(self):
        from companion.rag_engine import _chunk_text

        text = "First paragraph here.\n\nSecond paragraph here.\n\nThird paragraph."
        chunks = _chunk_text(text, chunk_size=30, overlap=5)
        self.assertGreater(len(chunks), 1)

    def test_overlap_creates_overlapping_content(self):
        from companion.rag_engine import _chunk_text

        text = (
            "Word " * 50 + "\n\n"
            + "Another " * 50 + "\n\n"
            + "Final " * 50
        )
        chunks = _chunk_text(text, chunk_size=100, overlap=40)
        if len(chunks) > 1:
            # Overlap should mean some words repeat between chunks
            words_chunk0 = set(chunks[0].split())
            words_chunk1 = set(chunks[1].split())
            self.assertTrue(len(words_chunk0 & words_chunk1) > 0)


class RagEngineFileContentHashTests(TestCase):

    def test_hashes_all_files_when_include_none(self):
        import tempfile
        from companion.rag_engine import _file_content_hash
        from pathlib import Path

        with tempfile.TemporaryDirectory() as tmpdir:
            p = Path(tmpdir)
            (p / "01_stages.txt").write_text("content1")
            (p / "02_care.txt").write_text("content2")
            result = _file_content_hash(p, None)
        self.assertIsInstance(result, str)
        self.assertEqual(len(result), 64)

    def test_filters_by_include_files(self):
        import tempfile
        from companion.rag_engine import _file_content_hash
        from pathlib import Path

        with tempfile.TemporaryDirectory() as tmpdir:
            p = Path(tmpdir)
            (p / "01_stages.txt").write_text("content1")
            (p / "02_care.txt").write_text("content2")
            hash_all = _file_content_hash(p, None)
            hash_one = _file_content_hash(p, {"01_stages.txt"})
        self.assertNotEqual(hash_all, hash_one)


class RagEngineRetrieveTests(TestCase):

    @patch("companion.rag_engine._get_collection")
    def test_retrieve_returns_formatted_passages_caregiver(self, mock_get_col):
        mock_col = MagicMock()
        mock_col.query.return_value = {
            "documents": [["Passage about sundowning.", "Passage about medication."]],
            "metadatas": [[
                {"source": "01_dementia_stages"},
                {"source": "03_medications"},
            ]],
        }
        mock_get_col.return_value = mock_col

        from companion.rag_engine import retrieve
        result = retrieve("What is sundowning?", mode="caregiver")

        self.assertIn("REFERENCE KNOWLEDGE", result)
        self.assertIn("Passage about sundowning", result)
        self.assertIn("Passage about medication", result)
        self.assertIn("clinical", result.lower())

    @patch("companion.rag_engine._get_collection")
    def test_retrieve_returns_formatted_passages_patient(self, mock_get_col):
        mock_col = MagicMock()
        mock_col.query.return_value = {
            "documents": [["Emotional guidance text."]],
            "metadatas": [[{"source": "06_patient_scenarios"}]],
        }
        mock_get_col.return_value = mock_col

        from companion.rag_engine import retrieve
        result = retrieve("I'm scared", mode="patient")

        self.assertIn("INTERNAL BEHAVIORAL GUIDANCE", result)
        self.assertIn("Emotional guidance text", result)

    @patch("companion.rag_engine._get_collection")
    def test_retrieve_returns_empty_on_no_results(self, mock_get_col):
        mock_col = MagicMock()
        mock_col.query.return_value = {"documents": [[]], "metadatas": [[]]}
        mock_get_col.return_value = mock_col

        from companion.rag_engine import retrieve
        result = retrieve("random query", mode="caregiver")
        self.assertEqual(result, "")

    @patch("companion.rag_engine._get_collection")
    def test_retrieve_handles_collection_error(self, mock_get_col):
        mock_get_col.side_effect = RuntimeError("ChromaDB connection failed")

        from companion.rag_engine import retrieve
        result = retrieve("query", mode="caregiver")
        self.assertEqual(result, "")

    @patch("companion.rag_engine._get_collection")
    def test_retrieve_handles_query_error(self, mock_get_col):
        mock_col = MagicMock()
        mock_col.query.side_effect = RuntimeError("Query failed")
        mock_get_col.return_value = mock_col

        from companion.rag_engine import retrieve
        result = retrieve("query", mode="patient")
        self.assertEqual(result, "")

    @patch("companion.rag_engine._get_collection")
    def test_retrieve_uses_default_n_results(self, mock_get_col):
        mock_col = MagicMock()
        mock_col.query.return_value = {"documents": [[]], "metadatas": [[]]}
        mock_get_col.return_value = mock_col

        from companion.rag_engine import retrieve
        retrieve("query", mode="caregiver")

        call_kwargs = mock_col.query.call_args[1]
        self.assertEqual(call_kwargs["n_results"], 8)

    @patch("companion.rag_engine._get_collection")
    def test_retrieve_respects_custom_n_results(self, mock_get_col):
        mock_col = MagicMock()
        mock_col.query.return_value = {"documents": [[]], "metadatas": [[]]}
        mock_get_col.return_value = mock_col

        from companion.rag_engine import retrieve
        retrieve("query", mode="patient", n_results=5)

        call_kwargs = mock_col.query.call_args[1]
        self.assertEqual(call_kwargs["n_results"], 5)


class RagEngineWarmUpTests(TestCase):

    @patch("companion.rag_engine._get_collection")
    def test_warm_up_loads_both_collections(self, mock_get_col):
        mock_col = MagicMock()
        mock_col.count.return_value = 42
        mock_get_col.return_value = mock_col

        from companion.rag_engine import warm_up
        warm_up()

        calls = mock_get_col.call_args_list
        modes_called = [c[0][0] for c in calls]
        self.assertIn("caregiver", modes_called)
        self.assertIn("patient", modes_called)

    @patch("companion.rag_engine._get_collection")
    def test_warm_up_handles_failure_gracefully(self, mock_get_col):
        mock_get_col.side_effect = RuntimeError("ChromaDB init failed")

        from companion.rag_engine import warm_up
        # Should not raise
        warm_up()
