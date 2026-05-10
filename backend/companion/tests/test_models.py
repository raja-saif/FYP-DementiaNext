"""
Unit tests for companion models
"""
from django.test import TestCase
from django.contrib.auth import get_user_model
from companion.models import (
    LifeStoryEntry, ConversationSession, ConversationMessage,
    PatientCompanionConfig, PatientFAQ,
)

User = get_user_model()


class LifeStoryEntryTests(TestCase):

    def setUp(self):
        self.patient = User.objects.create_user(
            email='ls_patient@t.com', password='p',
            first_name='Life', last_name='Story', role='patient'
        )
        self.caregiver = User.objects.create_user(
            email='ls_care@t.com', password='p', role='doctor'
        )

    def test_create_text_entry(self):
        entry = LifeStoryEntry.objects.create(
            patient=self.patient,
            category='family',
            entry_type='text',
            title='My Daughter',
            description='Sarah visits every Sunday.',
            created_by=self.caregiver,
        )
        self.assertEqual(entry.entry_type, 'text')
        self.assertEqual(entry.get_content(), 'Sarah visits every Sunday.')

    def test_create_voice_entry(self):
        entry = LifeStoryEntry.objects.create(
            patient=self.patient,
            category='memories',
            entry_type='voice',
            title='Wedding Day',
            audio_file='/media/audio/test.webm',
            audio_transcript='We got married in 1965.',
            created_by=self.caregiver,
        )
        self.assertEqual(entry.get_content(), 'We got married in 1965.')

    def test_get_content_voice_without_transcript(self):
        entry = LifeStoryEntry.objects.create(
            patient=self.patient, category='family',
            entry_type='voice', title='Test',
            description='fallback text',
        )
        self.assertEqual(entry.get_content(), 'fallback text')

    def test_str_representation(self):
        entry = LifeStoryEntry.objects.create(
            patient=self.patient, category='daily_routine',
            title='Morning Routine', description='...',
        )
        s = str(entry)
        self.assertIn('Morning Routine', s)

    def test_emotional_valence_default(self):
        entry = LifeStoryEntry.objects.create(
            patient=self.patient, category='favorites', title='Color',
        )
        self.assertEqual(entry.emotional_valence, 'positive')

    def test_priority_default(self):
        entry = LifeStoryEntry.objects.create(
            patient=self.patient, category='health', title='Allergy',
        )
        self.assertEqual(entry.priority, 1)

    def test_trigger_questions_json(self):
        entry = LifeStoryEntry.objects.create(
            patient=self.patient, category='people', title='Nurse',
            trigger_questions=['Where is the nurse?', 'Who helps me?'],
        )
        self.assertEqual(len(entry.trigger_questions), 2)

    def test_cascade_delete_patient(self):
        LifeStoryEntry.objects.create(
            patient=self.patient, category='family', title='Del',
        )
        self.patient.delete()
        self.assertEqual(LifeStoryEntry.objects.count(), 0)

    def test_ordering(self):
        e1 = LifeStoryEntry.objects.create(
            patient=self.patient, category='family', title='Low', priority=1
        )
        e2 = LifeStoryEntry.objects.create(
            patient=self.patient, category='family', title='High', priority=5
        )
        entries = list(LifeStoryEntry.objects.all())
        self.assertEqual(entries[0], e2)


class ConversationSessionTests(TestCase):

    def setUp(self):
        self.patient = User.objects.create_user(
            email='cs_pat@t.com', password='p', first_name='Chat', last_name='Patient'
        )

    def test_create_session(self):
        session = ConversationSession.objects.create(
            patient=self.patient, mode='patient',
            cognitive_stage_at_time='mild',
        )
        self.assertIsNotNone(session.started_at)
        self.assertIsNone(session.ended_at)
        self.assertEqual(session.message_count, 0)

    def test_str_representation(self):
        session = ConversationSession.objects.create(
            patient=self.patient, mode='caregiver',
        )
        s = str(session)
        self.assertIn('Chat Patient', s)
        self.assertIn('caregiver', s)


class ConversationMessageTests(TestCase):

    def setUp(self):
        self.patient = User.objects.create_user(
            email='cm_pat@t.com', password='p'
        )
        self.session = ConversationSession.objects.create(
            patient=self.patient, mode='patient'
        )

    def test_create_message(self):
        msg = ConversationMessage.objects.create(
            session=self.session, role='user',
            content_text='Hello, who am I?',
        )
        self.assertIsNotNone(msg.timestamp)
        self.assertEqual(msg.role, 'user')

    def test_str_representation(self):
        msg = ConversationMessage.objects.create(
            session=self.session, role='assistant',
            content_text='You are doing great today!',
        )
        s = str(msg)
        self.assertIn('[assistant]', s)
        self.assertIn('You are doing great', s)

    def test_ordering_by_timestamp(self):
        m1 = ConversationMessage.objects.create(
            session=self.session, role='user', content_text='First'
        )
        m2 = ConversationMessage.objects.create(
            session=self.session, role='assistant', content_text='Second'
        )
        msgs = list(self.session.messages.all())
        self.assertEqual(msgs[0], m1)
        self.assertEqual(msgs[1], m2)

    def test_cascade_delete_session(self):
        ConversationMessage.objects.create(
            session=self.session, role='user', content_text='Del'
        )
        self.session.delete()
        self.assertEqual(ConversationMessage.objects.count(), 0)


class PatientCompanionConfigTests(TestCase):

    def setUp(self):
        self.patient = User.objects.create_user(
            email='cfg@t.com', password='p', first_name='Config', last_name='Pat'
        )

    def test_create_config(self):
        config = PatientCompanionConfig.objects.create(patient=self.patient)
        self.assertEqual(config.cognitive_stage, 'mild')
        self.assertEqual(config.preferred_voice, 'en-US-AriaNeural')
        self.assertTrue(config.life_story_enabled)
        self.assertFalse(config.consent_given)

    def test_str_representation(self):
        config = PatientCompanionConfig.objects.create(
            patient=self.patient, cognitive_stage='moderate'
        )
        s = str(config)
        self.assertIn('Config Pat', s)
        self.assertIn('moderate', s)

    def test_one_to_one(self):
        PatientCompanionConfig.objects.create(patient=self.patient)
        from django.db.utils import IntegrityError
        with self.assertRaises(IntegrityError):
            PatientCompanionConfig.objects.create(patient=self.patient)


class PatientFAQTests(TestCase):

    def setUp(self):
        self.patient = User.objects.create_user(
            email='faq@t.com', password='p', first_name='FAQ', last_name='Pat'
        )

    def test_create_faq(self):
        faq = PatientFAQ.objects.create(
            patient=self.patient,
            question_text='Where is my daughter?',
            answer_text='Sarah visits every Sunday at 2pm.',
            category='family',
        )
        self.assertEqual(faq.ask_count, 1)
        self.assertEqual(faq.category, 'family')

    def test_str_representation(self):
        faq = PatientFAQ.objects.create(
            patient=self.patient,
            question_text='What day is it?',
            answer_text='Today is Monday.',
        )
        s = str(faq)
        self.assertIn('FAQ(FAQ)', s)
        self.assertIn('What day is it?', s)

    def test_ordering_by_ask_count(self):
        f1 = PatientFAQ.objects.create(
            patient=self.patient,
            question_text='Q1', answer_text='A1', ask_count=3
        )
        f2 = PatientFAQ.objects.create(
            patient=self.patient,
            question_text='Q2', answer_text='A2', ask_count=10
        )
        faqs = list(PatientFAQ.objects.all())
        self.assertEqual(faqs[0], f2)
