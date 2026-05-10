"""
Unit tests for companion serializers
"""
from django.test import TestCase
from django.contrib.auth import get_user_model
from companion.models import (
    LifeStoryEntry, ConversationSession, ConversationMessage,
    PatientCompanionConfig,
)
from companion.serializers import (
    LifeStoryEntrySerializer, ConversationSessionSerializer,
    ConversationMessageSerializer, PatientCompanionConfigSerializer,
    ChatRequestSerializer, ChatResponseSerializer,
)

User = get_user_model()


class LifeStoryEntrySerializerTests(TestCase):

    def setUp(self):
        self.patient = User.objects.create_user(
            email='lse_ser@t.com', password='p',
            first_name='LS', last_name='Ser'
        )

    def test_serializes_text_entry(self):
        entry = LifeStoryEntry.objects.create(
            patient=self.patient, category='family',
            title='Daughter', description='Sarah visits Sundays.',
            created_by=self.patient,
        )
        data = LifeStoryEntrySerializer(entry).data
        self.assertEqual(data['title'], 'Daughter')
        self.assertEqual(data['content'], 'Sarah visits Sundays.')
        self.assertEqual(data['created_by_name'], 'LS Ser')

    def test_serializes_voice_entry(self):
        entry = LifeStoryEntry.objects.create(
            patient=self.patient, category='memories',
            entry_type='voice', title='Voice',
            audio_transcript='Transcribed text here',
        )
        data = LifeStoryEntrySerializer(entry).data
        self.assertEqual(data['content'], 'Transcribed text here')
        self.assertEqual(data['entry_type'], 'voice')

    def test_created_by_name_none(self):
        entry = LifeStoryEntry.objects.create(
            patient=self.patient, category='health', title='No Author',
        )
        data = LifeStoryEntrySerializer(entry).data
        self.assertIsNone(data['created_by_name'])


class ConversationSessionSerializerTests(TestCase):

    def setUp(self):
        self.patient = User.objects.create_user(
            email='css@t.com', password='p', first_name='CS', last_name='S'
        )

    def test_serializes_session(self):
        session = ConversationSession.objects.create(
            patient=self.patient, mode='patient',
            cognitive_stage_at_time='mild',
        )
        data = ConversationSessionSerializer(session).data
        self.assertEqual(data['mode'], 'patient')
        self.assertIsNone(data['last_message'])

    def test_last_message_populated(self):
        session = ConversationSession.objects.create(
            patient=self.patient, mode='patient',
        )
        ConversationMessage.objects.create(
            session=session, role='user', content_text='Hello!'
        )
        ConversationMessage.objects.create(
            session=session, role='assistant', content_text='Hi there, how are you?'
        )
        data = ConversationSessionSerializer(session).data
        self.assertIsNotNone(data['last_message'])
        self.assertEqual(data['last_message']['role'], 'assistant')


class ConversationMessageSerializerTests(TestCase):

    def test_serializes_message(self):
        patient = User.objects.create_user(email='cms@t.com', password='p')
        session = ConversationSession.objects.create(
            patient=patient, mode='patient'
        )
        msg = ConversationMessage.objects.create(
            session=session, role='user', content_text='Test msg',
            response_time_ms=150,
        )
        data = ConversationMessageSerializer(msg).data
        self.assertEqual(data['role'], 'user')
        self.assertEqual(data['content_text'], 'Test msg')
        self.assertEqual(data['response_time_ms'], 150)


class PatientCompanionConfigSerializerTests(TestCase):

    def test_serializes_config(self):
        patient = User.objects.create_user(email='pccs@t.com', password='p')
        config = PatientCompanionConfig.objects.create(
            patient=patient, cognitive_stage='moderate',
        )
        data = PatientCompanionConfigSerializer(config).data
        self.assertEqual(data['cognitive_stage'], 'moderate')
        self.assertFalse(data['consent_given'])

    def test_partial_update(self):
        patient = User.objects.create_user(email='pccs_up@t.com', password='p')
        config = PatientCompanionConfig.objects.create(patient=patient)
        ser = PatientCompanionConfigSerializer(
            config, data={'cognitive_stage': 'severe'}, partial=True
        )
        self.assertTrue(ser.is_valid(), ser.errors)
        updated = ser.save()
        self.assertEqual(updated.cognitive_stage, 'severe')


class ChatRequestSerializerTests(TestCase):

    def test_valid_patient_mode(self):
        ser = ChatRequestSerializer(data={'message': 'Hello', 'mode': 'patient'})
        self.assertTrue(ser.is_valid(), ser.errors)

    def test_valid_caregiver_mode(self):
        ser = ChatRequestSerializer(data={
            'message': 'How is mom?', 'mode': 'caregiver', 'patient_id': 1
        })
        self.assertTrue(ser.is_valid(), ser.errors)

    def test_message_optional(self):
        ser = ChatRequestSerializer(data={'mode': 'patient'})
        self.assertTrue(ser.is_valid(), ser.errors)

    def test_invalid_mode(self):
        ser = ChatRequestSerializer(data={'message': 'Hi', 'mode': 'admin'})
        self.assertFalse(ser.is_valid())


class ChatResponseSerializerTests(TestCase):

    def test_valid_response(self):
        data = {
            'reply': 'Hello!',
            'audio_url': None,
            'session_id': 1,
            'response_time_ms': 250,
        }
        ser = ChatResponseSerializer(data=data)
        self.assertTrue(ser.is_valid(), ser.errors)
