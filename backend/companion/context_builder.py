from datetime import date
from typing import Optional

from django.conf import settings
from django.utils import timezone

from .prompts import (
    PATIENT_MODE_SYSTEM_PROMPT,
    CAREGIVER_MODE_SYSTEM_PROMPT,
    STAGE_RULES,
    WORD_LIMITS,
)


def _calculate_age(dob: date) -> int:
    today = date.today()
    return today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))


def _build_mri_section(patient, mode: str) -> str:
    from detection.models import DetectionResult

    if mode == "caregiver":
        scans = DetectionResult.objects.filter(patient=patient, status="completed").order_by("-created_at")[:5]
        if not scans:
            return "- MRI History: No scans on file."
        lines = ["- MRI History:"]
        for scan in scans:
            label = scan.get_predicted_class_display() if scan.predicted_class else "Unknown"
            conf = f"{scan.confidence_score:.0%}" if scan.confidence_score else "N/A"
            dt = scan.created_at.strftime("%B %d, %Y")
            lines.append(f"  * {dt}: {label} (confidence {conf})")
        return "\n".join(lines)
    else:
        latest = (
            DetectionResult.objects.filter(patient=patient, status="completed")
            .order_by("-created_at")
            .first()
        )
        if not latest:
            return "- Latest MRI: No scans on file."
        label = latest.get_predicted_class_display() if latest.predicted_class else "Unknown"
        confidence = (
            f"{latest.confidence_score:.0%}" if latest.confidence_score else "N/A"
        )
        scan_date = latest.created_at.strftime("%B %d, %Y")
        return f"- Latest MRI scan ({scan_date}): {label} (confidence {confidence})"


def _build_session_summary_section(patient) -> str:
    from .models import ConversationSession
    recent = ConversationSession.objects.filter(
        patient=patient, mode="patient"
    ).exclude(summary="").order_by("-started_at")[:3]
    
    if not recent:
        return ""
        
    lines = ["SESSION CONTINUITY CONTEXT:"]
    lines.append("Here is what you discussed with the patient in recent sessions:")
    for session in reversed(list(recent)):
        lines.append(f"- {session.started_at.strftime('%A')}: {session.summary}")
    return "\n".join(lines)


def _build_life_story_section(patient) -> str:
    """
    Build a comprehensive life story context section for the LLM.
    Includes text entries, voice message transcripts, and specific Q&A pairs.
    """
    from .models import LifeStoryEntry

    entries = LifeStoryEntry.objects.filter(patient=patient).order_by("-priority", "category")
    if not entries.exists():
        return ""

    lines = ["PATIENT'S LIFE STORY & CARE INFORMATION:"]
    lines.append("(Use this information to answer questions accurately - DO NOT make up information)")
    lines.append("")
    
    by_category: dict[str, list] = {}
    sensitive_topics: list[str] = []
    qa_pairs: list[str] = []  # Specific question-answer pairs
    care_instructions: list[str] = []  # Important care notes

    for entry in entries:
        cat = entry.get_category_display()
        content = entry.get_content()  # Gets transcript for voice, description for text
        
        # Build the detail string
        detail = f"**{entry.title}**"
        if content:
            # Truncate very long content for context efficiency
            content_preview = content[:500] + "..." if len(content) > 500 else content
            detail += f": {content_preview}"
        
        if entry.people_involved:
            people = ", ".join(entry.people_involved)
            detail += f" (People: {people})"
        if entry.time_period:
            detail += f" [Time: {entry.time_period}]"
        
        # Add voice indicator
        if entry.entry_type == "voice":
            detail += " 🎤"
        
        by_category.setdefault(cat, [])
        by_category[cat].append(detail)

        # Handle sensitive topics
        if entry.emotional_valence == "sensitive":
            sensitive_topics.append(entry.title)
        
        # Extract Q&A pairs for direct answering
        if entry.trigger_questions:
            for q in entry.trigger_questions:
                if q and content:
                    qa_pairs.append(f'Q: "{q}"\nA: {content[:300]}')
        
        # Collect care instructions separately for emphasis
        if entry.category == "instructions":
            care_instructions.append(f"• {entry.title}: {content[:200] if content else 'No details'}")

    # Output categorized information
    for cat, items in by_category.items():
        lines.append(f"## {cat}")
        for item in items:
            lines.append(f"  {item}")
        lines.append("")

    # Add specific Q&A pairs for direct use
    if qa_pairs:
        lines.append("## SPECIFIC ANSWERS TO COMMON QUESTIONS:")
        lines.append("(When the patient asks these questions, use these EXACT answers)")
        for qa in qa_pairs[:10]:  # Limit to 10 most important
            lines.append(qa)
        lines.append("")

    # Emphasize care instructions
    if care_instructions:
        lines.append("## CARE INSTRUCTIONS (from caregiver):")
        for inst in care_instructions:
            lines.append(inst)
        lines.append("")

    # Warn about sensitive topics
    if sensitive_topics:
        lines.append(f"⚠️ AVOID these topics (may cause distress): {', '.join(sensitive_topics)}")

    return "\n".join(lines)


def build_system_prompt(patient, mode: str, cognitive_stage: str) -> str:
    profile = getattr(patient, "patient_profile", None)

    patient_name = patient.first_name or patient.email.split("@")[0]
    age = _calculate_age(profile.date_of_birth) if profile and profile.date_of_birth else "Unknown"
    gender_map = {"M": "Male", "F": "Female", "O": "Other"}
    gender = gender_map.get(profile.gender, "Unknown") if profile else "Unknown"

    medications = profile.current_medications if profile and profile.current_medications else None
    medications_section = f"- Current medications: {medications}" if medications else "- Current medications: None on file"

    allergies = profile.allergies if profile and profile.allergies else None
    allergies_section = f"- Allergies: {allergies}" if allergies else "- Allergies: None on file"

    medical_history = profile.medical_history if profile and profile.medical_history else None
    if medical_history and isinstance(medical_history, dict) and medical_history:
        history_str = ", ".join(f"{k}: {v}" for k, v in medical_history.items())
        medical_history_section = f"- Medical history: {history_str}"
    else:
        medical_history_section = "- Medical history: None on file"

    mri_section = _build_mri_section(patient, mode)
    life_story_section = _build_life_story_section(patient)
    stage_rules_template = STAGE_RULES.get(cognitive_stage, STAGE_RULES["mild"])
    stage_rules = stage_rules_template.replace("{patient_name}", patient_name)
    word_limit = WORD_LIMITS.get(cognitive_stage, 80)
    
    session_summary_section = _build_session_summary_section(patient) if mode == "patient" else ""

    template = (
        PATIENT_MODE_SYSTEM_PROMPT if mode == "patient"
        else CAREGIVER_MODE_SYSTEM_PROMPT
    )

    if mode == "patient":
        return template.format(
            current_time=timezone.localtime().strftime("%A, %B %d, %Y, %I:%M %p"),
            patient_name=patient_name,
            age=age,
            gender=gender,
            medications_section=medications_section,
            allergies_section=allergies_section,
            medical_history_section=medical_history_section,
            mri_section=mri_section,
            cognitive_stage=cognitive_stage,
            cognitive_stage_upper=cognitive_stage.upper(),
            life_story_section=life_story_section,
            session_summary_section=session_summary_section,
            faq_context_section="",  # injected dynamically in conversation_engine.py
            stage_rules=stage_rules,
            word_limit=word_limit,
        )
    else:
        return template.format(
            patient_name=patient_name,
            age=age,
            gender=gender,
            medications_section=medications_section,
            allergies_section=allergies_section,
            medical_history_section=medical_history_section,
            mri_section=mri_section,
            cognitive_stage=cognitive_stage,
            cognitive_stage_upper=cognitive_stage.upper(),
            life_story_section=life_story_section,
            stage_rules=stage_rules,
            word_limit=word_limit,
        )


def build_conversation_messages(session, limit: int = 20) -> list[dict]:
    """Return the last `limit` messages formatted for the LLM API."""
    from .models import ConversationMessage

    recent = (
        ConversationMessage.objects.filter(session=session)
        .order_by("-timestamp")[:limit]
    )
    messages = []
    for msg in reversed(list(recent)):
        messages.append({"role": msg.role, "content": msg.content_text})
    return messages
