import os
import time
import logging
import threading
from typing import Generator, Optional

from groq import Groq

from .context_builder import build_system_prompt, build_conversation_messages
from . import rag_engine
from . import faq_detector

logger = logging.getLogger(__name__)

_client: Groq | None = None

# --- Model configuration per mode ------------------------------------------

_MODEL_CONFIG = {
    "patient": {
        "model_env": "COMPANION_LLM_MODEL",
        "model_default": "llama-3.3-70b-versatile",
        "temperature": 0.7,
        "max_tokens": 400,
    },
    "caregiver": {
        "model_env": "CAREGIVER_LLM_MODEL",
        "model_default": "llama-3.3-70b-versatile",
        "temperature": 0.4,
        "max_tokens": 500,
    },
}


def _get_client() -> Groq:
    global _client
    if _client is None:
        api_key = (os.getenv("GROQ_API_KEY") or "").strip()
        if not api_key:
            raise ValueError(
                "GROQ_API_KEY is not set. "
                "Get a free key at https://console.groq.com and add it to backend/.env"
            )
        _client = Groq(api_key=api_key)
    return _client


def _strip_thinking_tags(text: str) -> str:
    """Strip <think>...</think> blocks from deepseek-r1 reasoning output."""
    import re
    cleaned = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)
    return cleaned.strip()


def _run_async_post_processing(
    patient, 
    session, 
    user_text: str, 
    reply: str, 
    mode: str, 
    faq_result: Optional[dict],
    client: Groq,
    model_name: str
):
    """Run post-processing tasks in a background thread (FAQ storage, session summary)."""
    def _worker():
        from .models import ConversationMessage
        
        # Store FAQ for patient mode (new questions only)
        if mode == "patient" and faq_result is None:
            try:
                faq_detector.store_faq(patient, user_text, reply)
            except Exception:
                logger.exception("Failed to store FAQ for patient %s", patient.pk)
        
        # Generate session summary - after first message and then every 10 messages
        if session.message_count == 1 or (session.message_count > 0 and session.message_count % 10 == 0):
            try:
                _generate_session_summary(session, client, model_name)
            except Exception:
                logger.exception("Failed to generate session summary")
    
    thread = threading.Thread(target=_worker, daemon=True)
    thread.start()


def chat(
    patient,
    session,
    user_text: str,
    mode: str,
    cognitive_stage: str,
) -> tuple[str, int]:
    """Send a message and return (assistant_reply, response_time_ms)."""
    from .models import ConversationMessage

    # ----- FAQ check (patient mode only) ------------------------------------
    faq_result = None
    if mode == "patient":
        faq_result = faq_detector.check_faq(patient, user_text)

        if faq_result and faq_result["match_type"] == "exact":
            # Return the exact stored answer — no LLM call needed
            reply = faq_result["answer"]

            ConversationMessage.objects.create(
                session=session, role="user", content_text=user_text
            )
            ConversationMessage.objects.create(
                session=session,
                role="assistant",
                content_text=reply,
                response_time_ms=0,
            )
            session.message_count = session.messages.count()
            session.save(update_fields=["message_count"])

            logger.info(
                "FAQ exact match returned for patient %s (sim=%.2f)",
                patient.pk, faq_result["similarity"],
            )
            return reply, 0

    # ----- Build system prompt + RAG ----------------------------------------
    system_prompt = build_system_prompt(patient, mode, cognitive_stage)

    # Mode-aware RAG retrieval
    rag_context = rag_engine.retrieve(user_text, mode=mode)
    if rag_context:
        system_prompt += "\n\n" + rag_context

    # For patient mode: inject FAQ context for partial matches or general FAQ awareness
    if mode == "patient":
        faq_context = faq_detector.get_faq_context(patient, limit=5)
        if faq_context:
            system_prompt += "\n\n" + faq_context

        # If there's a partial FAQ match, add specific guidance
        if faq_result and faq_result["match_type"] == "partial":
            system_prompt += (
                f'\n\nIMPORTANT: The patient has asked a similar question before. '
                f'Their previous answer was: "{faq_result["answer"]}". '
                f'Use very similar wording in your response for consistency and comfort.'
            )

    # ----- Save user message ------------------------------------------------
    ConversationMessage.objects.create(
        session=session, role="user", content_text=user_text
    )
    session.message_count = session.messages.count()
    session.save(update_fields=["message_count"])

    # ----- Build messages list ----------------------------------------------
    history = build_conversation_messages(session)
    messages = [{"role": "system", "content": system_prompt}] + history

    # ----- Call LLM with mode-specific config -------------------------------
    cfg = _MODEL_CONFIG.get(mode, _MODEL_CONFIG["patient"])
    model_name = os.getenv(cfg["model_env"], cfg["model_default"])

    start = time.time()
    client = _get_client()
    response = client.chat.completions.create(
        model=model_name,
        messages=messages,
        temperature=cfg["temperature"],
        max_tokens=cfg["max_tokens"],
    )
    elapsed_ms = int((time.time() - start) * 1000)

    reply = response.choices[0].message.content.strip()

    # Strip <think> tags if using deepseek-r1
    if "deepseek" in model_name.lower():
        reply = _strip_thinking_tags(reply)

    # ----- Save assistant message -------------------------------------------
    ConversationMessage.objects.create(
        session=session,
        role="assistant",
        content_text=reply,
        response_time_ms=elapsed_ms,
    )
    session.message_count = session.messages.count()
    session.save(update_fields=["message_count"])

    # ----- Async post-processing (FAQ storage, session summary) -------------
    _run_async_post_processing(
        patient, session, user_text, reply, mode, faq_result, client, model_name
    )

    return reply, elapsed_ms


def chat_stream(
    patient,
    session,
    user_text: str,
    mode: str,
    cognitive_stage: str,
) -> Generator[dict, None, None]:
    """
    Streaming version of chat(). Yields chunks as they arrive from the LLM.
    
    Yields dicts with keys:
      - "type": "chunk" | "done" | "faq_hit"
      - "content": str (the text chunk for "chunk", full reply for "done")
      - "response_time_ms": int (only for "done")
      - "is_faq": bool (only for "faq_hit")
    """
    from .models import ConversationMessage

    # ----- FAQ check (patient mode only) ------------------------------------
    faq_result = None
    if mode == "patient":
        faq_result = faq_detector.check_faq(patient, user_text)

        if faq_result and faq_result["match_type"] == "exact":
            reply = faq_result["answer"]

            ConversationMessage.objects.create(
                session=session, role="user", content_text=user_text
            )
            ConversationMessage.objects.create(
                session=session,
                role="assistant",
                content_text=reply,
                response_time_ms=0,
            )
            session.message_count = session.messages.count()
            session.save(update_fields=["message_count"])

            logger.info(
                "FAQ exact match returned for patient %s (sim=%.2f)",
                patient.pk, faq_result["similarity"],
            )
            
            # For FAQ hits, yield the full response immediately
            yield {"type": "faq_hit", "content": reply, "is_faq": True, "response_time_ms": 0}
            return

    # ----- Build system prompt + RAG ----------------------------------------
    system_prompt = build_system_prompt(patient, mode, cognitive_stage)

    rag_context = rag_engine.retrieve(user_text, mode=mode)
    if rag_context:
        system_prompt += "\n\n" + rag_context

    if mode == "patient":
        faq_context = faq_detector.get_faq_context(patient, limit=5)
        if faq_context:
            system_prompt += "\n\n" + faq_context

        if faq_result and faq_result["match_type"] == "partial":
            system_prompt += (
                f'\n\nIMPORTANT: The patient has asked a similar question before. '
                f'Their previous answer was: "{faq_result["answer"]}". '
                f'Use very similar wording in your response for consistency and comfort.'
            )

    # ----- Save user message ------------------------------------------------
    ConversationMessage.objects.create(
        session=session, role="user", content_text=user_text
    )
    session.message_count = session.messages.count()
    session.save(update_fields=["message_count"])

    # ----- Build messages list ----------------------------------------------
    history = build_conversation_messages(session)
    messages = [{"role": "system", "content": system_prompt}] + history

    # ----- Call LLM with streaming ------------------------------------------
    cfg = _MODEL_CONFIG.get(mode, _MODEL_CONFIG["patient"])
    model_name = os.getenv(cfg["model_env"], cfg["model_default"])

    start = time.time()
    client = _get_client()
    
    # Use streaming API
    stream = client.chat.completions.create(
        model=model_name,
        messages=messages,
        temperature=cfg["temperature"],
        max_tokens=cfg["max_tokens"],
        stream=True,
    )
    
    full_reply = ""
    for chunk in stream:
        if chunk.choices and chunk.choices[0].delta.content:
            text_chunk = chunk.choices[0].delta.content
            full_reply += text_chunk
            yield {"type": "chunk", "content": text_chunk}
    
    elapsed_ms = int((time.time() - start) * 1000)

    # Strip <think> tags if using deepseek-r1
    if "deepseek" in model_name.lower():
        full_reply = _strip_thinking_tags(full_reply)

    # ----- Save assistant message -------------------------------------------
    ConversationMessage.objects.create(
        session=session,
        role="assistant",
        content_text=full_reply,
        response_time_ms=elapsed_ms,
    )
    session.message_count = session.messages.count()
    session.save(update_fields=["message_count"])

    # ----- Async post-processing --------------------------------------------
    _run_async_post_processing(
        patient, session, user_text, full_reply, mode, faq_result, client, model_name
    )

    yield {"type": "done", "content": full_reply, "response_time_ms": elapsed_ms}


def _generate_session_summary(session, client, model_name: str):
    """Generate a brief session summary for cross-session context continuity."""
    from .models import ConversationMessage

    recent = (
        ConversationMessage.objects.filter(session=session)
        .order_by("-timestamp")[:10]
    )
    if not recent:
        return

    conversation_text = "\n".join(
        f"{m.role}: {m.content_text}" for m in reversed(list(recent))
    )

    # For first message, generate a short title. For later, generate summary.
    is_first_summary = not session.summary
    
    if is_first_summary:
        prompt = (
            "Create a very short title (3-5 words max) for this conversation. "
            "Focus on the main topic or question. No quotes, no punctuation at the end."
        )
    else:
        prompt = (
            "Summarize this conversation between a dementia companion "
            "and a user in 2-3 sentences. Focus on the topics discussed, "
            "the patient's emotional state, and any important details "
            "mentioned. Be concise."
        )

    response = client.chat.completions.create(
        model=os.getenv("COMPANION_LLM_MODEL", "llama-3.3-70b-versatile"),
        messages=[
            {"role": "system", "content": prompt},
            {"role": "user", "content": conversation_text},
        ],
        temperature=0.2,
        max_tokens=50 if is_first_summary else 150,
    )

    summary_text = response.choices[0].message.content.strip()
    if "deepseek" in model_name.lower():
        summary_text = _strip_thinking_tags(summary_text)

    # For first message, replace. For later, append.
    if is_first_summary:
        session.summary = summary_text
    else:
        session.summary += f" | {summary_text}"
    session.save(update_fields=["summary"])

    logger.info("Session %s summary updated.", session.pk)


def transcribe_audio(audio_file) -> str:
    """Transcribe audio using Groq Whisper Large V3 Turbo (free, fast).
    
    Args:
        audio_file: Can be a file path (str), file-like object, or Django UploadedFile
    """
    import io
    
    client = _get_client()
    
    # Handle different input types for Groq API compatibility
    if isinstance(audio_file, str):
        # It's a file path - open and read
        with open(audio_file, "rb") as f:
            content = f.read()
        filename = audio_file.split("/")[-1]
    elif hasattr(audio_file, 'read'):
        # File-like object (including Django UploadedFile)
        content = audio_file.read()
        # Get filename if available
        filename = getattr(audio_file, 'name', 'audio.webm')
        if hasattr(filename, 'split'):
            filename = filename.split("/")[-1]
        # Reset file pointer if possible
        if hasattr(audio_file, 'seek'):
            audio_file.seek(0)
    else:
        raise ValueError(f"Unsupported audio_file type: {type(audio_file)}")
    
    # Determine mime type from filename
    if filename.endswith('.webm'):
        mime_type = 'audio/webm'
    elif filename.endswith('.mp3'):
        mime_type = 'audio/mpeg'
    elif filename.endswith('.wav'):
        mime_type = 'audio/wav'
    elif filename.endswith('.m4a'):
        mime_type = 'audio/mp4'
    else:
        mime_type = 'audio/webm'  # Default
    
    # Pass as tuple (filename, content, mime_type) for Groq API
    transcript = client.audio.transcriptions.create(
        model="whisper-large-v3-turbo",
        file=(filename, content, mime_type),
        language="en",
    )
    return transcript.text.strip()
