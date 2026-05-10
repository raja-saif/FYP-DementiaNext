from django.db import models
from django.conf import settings


class LifeStoryEntry(models.Model):
    """
    Life story entries for dementia patients - used for reminiscence therapy
    and providing accurate, personalized responses in conversations.
    """
    
    # Improved categories that make more clinical sense for dementia care
    CATEGORY_CHOICES = [
        ("family", "Family & Relationships"),      # Spouse, children, siblings, parents
        ("daily_routine", "Daily Routine & Care"), # Meals, medications, sleep schedule
        ("favorites", "Favorites & Preferences"),  # Food, music, TV shows, colors
        ("memories", "Important Memories"),        # Wedding, births, achievements
        ("places", "Places & Home"),               # Current home, hometown, visited places
        ("health", "Health Information"),          # Allergies, conditions, what calms them
        ("people", "Important People"),            # Who visits, caregivers, friends
        ("instructions", "Care Instructions"),     # How to handle situations, preferences
    ]

    # Entry type - text description or voice message
    ENTRY_TYPE_CHOICES = [
        ("text", "Text Entry"),
        ("voice", "Voice Message"),
    ]

    VALENCE_CHOICES = [
        ("positive", "Positive"),    # Safe to bring up, brings joy
        ("neutral", "Neutral"),      # Factual information
        ("sensitive", "Sensitive"),  # Avoid bringing up, may cause distress
    ]

    patient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="life_story_entries",
    )
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    entry_type = models.CharField(
        max_length=10, 
        choices=ENTRY_TYPE_CHOICES, 
        default="text"
    )
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    
    # Voice message fields
    audio_file = models.CharField(max_length=500, blank=True)  # Path to audio file
    audio_transcript = models.TextField(blank=True)  # Transcribed text from voice
    
    # Additional context
    people_involved = models.JSONField(default=list, blank=True)
    time_period = models.CharField(max_length=100, blank=True)
    
    # Question-Answer pairs - specific Q&A the chatbot should use
    # E.g., Q: "Where is my daughter?" A: "Sarah visits every Sunday at 2pm"
    trigger_questions = models.JSONField(
        default=list, 
        blank=True,
        help_text="Questions that should trigger this entry's answer"
    )
    
    emotional_valence = models.CharField(
        max_length=20, choices=VALENCE_CHOICES, default="positive"
    )
    
    # Priority for conflicting information (higher = more authoritative)
    priority = models.PositiveIntegerField(default=1)
    
    usage_count = models.PositiveIntegerField(default=0)
    last_positive_response = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="created_life_stories",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-priority", "-created_at"]
        indexes = [
            models.Index(fields=["patient", "category"]),
            models.Index(fields=["patient", "emotional_valence"]),
            models.Index(fields=["patient", "entry_type"]),
        ]

    def __str__(self):
        entry_type_icon = "🎤" if self.entry_type == "voice" else "📝"
        return f"{entry_type_icon} {self.title} ({self.get_category_display()}) - {self.patient.get_full_name()}"
    
    def get_content(self):
        """Get the content to use - transcript for voice, description for text."""
        if self.entry_type == "voice" and self.audio_transcript:
            return self.audio_transcript
        return self.description


class ConversationSession(models.Model):
    MODE_CHOICES = [
        ("patient", "Patient"),
        ("caregiver", "Caregiver"),
    ]

    STAGE_CHOICES = [
        ("mild", "Mild"),
        ("moderate", "Moderate"),
        ("severe", "Severe"),
    ]

    patient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="companion_sessions",
    )
    mode = models.CharField(max_length=20, choices=MODE_CHOICES)
    started_at = models.DateTimeField(auto_now_add=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    message_count = models.PositiveIntegerField(default=0)
    cognitive_stage_at_time = models.CharField(
        max_length=20, choices=STAGE_CHOICES, blank=True
    )
    summary = models.TextField(blank=True)

    class Meta:
        ordering = ["-started_at"]
        indexes = [
            models.Index(fields=["patient", "-started_at"]),
        ]

    def __str__(self):
        return f"Session {self.pk} - {self.patient.get_full_name()} ({self.mode})"


class ConversationMessage(models.Model):
    ROLE_CHOICES = [
        ("user", "User"),
        ("assistant", "Assistant"),
        ("system", "System"),
    ]

    session = models.ForeignKey(
        ConversationSession,
        on_delete=models.CASCADE,
        related_name="messages",
    )
    role = models.CharField(max_length=10, choices=ROLE_CHOICES)
    content_text = models.TextField()
    audio_url = models.CharField(max_length=500, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    response_time_ms = models.PositiveIntegerField(null=True, blank=True)

    class Meta:
        ordering = ["timestamp"]
        indexes = [
            models.Index(fields=["session", "timestamp"]),
        ]

    def __str__(self):
        preview = self.content_text[:60]
        return f"[{self.role}] {preview}"


class PatientCompanionConfig(models.Model):
    STAGE_CHOICES = [
        ("mild", "Mild"),
        ("moderate", "Moderate"),
        ("severe", "Severe"),
    ]

    patient = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="companion_config",
    )
    cognitive_stage = models.CharField(
        max_length=20, choices=STAGE_CHOICES, default="mild"
    )
    stage_last_updated = models.DateTimeField(auto_now=True)
    preferred_voice = models.CharField(max_length=100, default="en-US-AriaNeural")
    life_story_enabled = models.BooleanField(default=True)
    language = models.CharField(max_length=10, default="en")
    consent_given = models.BooleanField(default=False)
    consent_date = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Config for {self.patient.get_full_name()} - Stage: {self.cognitive_stage}"


class PatientFAQ(models.Model):
    """
    Tracks questions a dementia patient asks repeatedly so the chatbot
    can return the *exact same wording* each time — clinical best practice
    for providing comfort through familiar phrasing.
    """

    CATEGORY_CHOICES = [
        ("orientation", "Orientation"),       # where am I, what day
        ("family", "Family"),                 # where is [person]
        ("routine", "Routine"),               # when is lunch, what's next
        ("identity", "Identity"),             # who are you, who am I
        ("safety", "Safety"),                 # I want to go home
        ("general", "General"),
    ]

    patient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="patient_faqs",
    )
    question_text = models.TextField(
        help_text="Canonical form of the patient's question.",
    )
    answer_text = models.TextField(
        help_text="The consistent answer to give every time.",
    )
    category = models.CharField(
        max_length=20, choices=CATEGORY_CHOICES, default="general",
    )
    ask_count = models.PositiveIntegerField(default=1)
    last_asked = models.DateTimeField(null=True, blank=True)
    # Pre-computed embedding for fast similarity matching (avoids recomputing on every request)
    question_embedding = models.BinaryField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-ask_count", "-last_asked"]
        indexes = [
            models.Index(fields=["patient", "-ask_count"]),
        ]

    def __str__(self):
        return f"FAQ({self.patient.first_name}): {self.question_text[:50]} (×{self.ask_count})"
