"""
FAQ detector for the DementiaNext Patient Companion.

Detects when a dementia patient asks a semantically similar question to one
they have asked before, and returns the previously given consistent answer.
This is clinically important — dementia patients are comforted by hearing
the exact same answer phrased in the exact same way each time.

Uses sentence-transformers for lightweight, local semantic similarity.
OPTIMIZED: Pre-computed embeddings are stored in the database to avoid
recomputing on every request (saves ~150-250ms per query).
"""

import logging
import pickle
from datetime import timedelta

from django.utils import timezone

logger = logging.getLogger(__name__)

# Lazy-loaded model to avoid importing at module level
_model = None


def _get_model():
    """Lazy-load the sentence-transformers model."""
    global _model
    if _model is None:
        try:
            from sentence_transformers import SentenceTransformer
            _model = SentenceTransformer("all-MiniLM-L6-v2")
            logger.info("FAQ detector: sentence-transformers model loaded.")
        except Exception:
            logger.exception("Failed to load sentence-transformers model for FAQ")
            return None
    return _model


def _serialize_embedding(emb: "np.ndarray") -> bytes:
    """Serialize numpy embedding to bytes for DB storage."""
    import numpy as np

    return pickle.dumps(emb.astype(np.float32))


def _deserialize_embedding(data: bytes) -> "np.ndarray":
    """Deserialize embedding from bytes."""
    return pickle.loads(data)


def _cosine_similarity_batch(
    query_emb: "np.ndarray", faq_embeddings: "np.ndarray"
) -> "np.ndarray":
    """Compute cosine similarity between query and all FAQ embeddings efficiently."""
    import numpy as np

    query_norm = query_emb / (np.linalg.norm(query_emb) + 1e-9)
    faq_norms = faq_embeddings / (
        np.linalg.norm(faq_embeddings, axis=1, keepdims=True) + 1e-9
    )
    return np.dot(faq_norms, query_norm)


def check_faq(patient, question_text: str) -> dict | None:
    """
    Check if *question_text* matches a previously asked FAQ for this patient.
    Uses pre-computed embeddings for fast matching (only embeds the query).

    Returns a dict with keys:
      - "answer": the consistent answer to return
      - "similarity": how closely it matched
      - "faq_id": the PatientFAQ pk
    Or None if no match above the threshold.
    """
    from .models import PatientFAQ

    model = _get_model()
    if model is None:
        return None

    # Get all FAQs for this patient with their pre-computed embeddings
    faqs = list(
        PatientFAQ.objects.filter(patient=patient)
        .order_by("-ask_count")[:50]
    )
    if not faqs:
        return None

    try:
        # Only embed the query (not all FAQs - they're pre-computed!)
        query_embedding = model.encode(question_text, normalize_embeddings=True)
        
        # Collect pre-computed embeddings (or compute missing ones)
        faq_embeddings = []
        faqs_needing_embedding = []
        
        for faq in faqs:
            if faq.question_embedding:
                try:
                    emb = _deserialize_embedding(faq.question_embedding)
                    faq_embeddings.append(emb)
                except Exception:
                    faqs_needing_embedding.append(faq)
                    faq_embeddings.append(None)
            else:
                faqs_needing_embedding.append(faq)
                faq_embeddings.append(None)
        
        # Batch compute any missing embeddings
        if faqs_needing_embedding:
            texts_to_embed = [f.question_text for f in faqs_needing_embedding]
            new_embeddings = model.encode(texts_to_embed, normalize_embeddings=True)
            
            # Fill in missing and save to DB
            new_emb_idx = 0
            for i, emb in enumerate(faq_embeddings):
                if emb is None:
                    faq_embeddings[i] = new_embeddings[new_emb_idx]
                    # Save embedding to DB for future use (async-friendly)
                    faqs[i].question_embedding = _serialize_embedding(new_embeddings[new_emb_idx])
                    faqs[i].save(update_fields=["question_embedding"])
                    new_emb_idx += 1
        
        import numpy as np

        # Convert to numpy array for batch similarity
        faq_embeddings_array = np.array(faq_embeddings)
        similarities = _cosine_similarity_batch(query_embedding, faq_embeddings_array)
        
        best_idx = np.argmax(similarities)
        best_sim = float(similarities[best_idx])
        best_faq = faqs[best_idx]

    except Exception:
        logger.exception("FAQ embedding failed")
        return None

    # High confidence match → return exact stored answer
    if best_sim >= 0.85:
        best_faq.ask_count += 1
        best_faq.last_asked = timezone.now()
        best_faq.save(update_fields=["ask_count", "last_asked"])

        logger.info(
            "FAQ exact match (sim=%.2f) for patient %s: '%s'",
            best_sim, patient.pk, question_text[:60],
        )
        return {
            "answer": best_faq.answer_text,
            "similarity": best_sim,
            "faq_id": best_faq.pk,
            "match_type": "exact",
        }

    # Moderate match → return FAQ context for prompt injection
    if best_sim >= 0.60:
        best_faq.ask_count += 1
        best_faq.last_asked = timezone.now()
        best_faq.save(update_fields=["ask_count", "last_asked"])

        logger.info(
            "FAQ partial match (sim=%.2f) for patient %s: '%s'",
            best_sim, patient.pk, question_text[:60],
        )
        return {
            "answer": best_faq.answer_text,
            "similarity": best_sim,
            "faq_id": best_faq.pk,
            "match_type": "partial",
        }

    return None


def store_faq(patient, question_text: str, answer_text: str, category: str = "general"):
    """
    Store a new FAQ entry for a patient with pre-computed embedding,
    or update an existing one if a close match already exists.
    """
    from .models import PatientFAQ

    model = _get_model()
    question_embedding_bytes = None

    # Compute embedding for new question
    if model is not None:
        try:
            query_emb = model.encode(question_text, normalize_embeddings=True)
            question_embedding_bytes = _serialize_embedding(query_emb)
        except Exception:
            logger.exception("FAQ embedding computation failed")
            query_emb = None

        # Check for duplicates using cached embeddings
        existing = list(PatientFAQ.objects.filter(patient=patient)[:50])
        if existing and query_emb is not None:
            try:
                # Collect existing embeddings
                existing_embs = []
                for faq in existing:
                    if faq.question_embedding:
                        try:
                            existing_embs.append(_deserialize_embedding(faq.question_embedding))
                        except Exception:
                            # Fallback: compute embedding
                            emb = model.encode(faq.question_text, normalize_embeddings=True)
                            existing_embs.append(emb)
                    else:
                        emb = model.encode(faq.question_text, normalize_embeddings=True)
                        existing_embs.append(emb)

                import numpy as np

                existing_array = np.array(existing_embs)
                similarities = _cosine_similarity_batch(query_emb, existing_array)
                
                best_idx = np.argmax(similarities)
                if similarities[best_idx] >= 0.85:
                    # Update the existing FAQ's answer to the latest one
                    faq = existing[best_idx]
                    faq.answer_text = answer_text
                    faq.ask_count += 1
                    faq.last_asked = timezone.now()
                    if not faq.question_embedding:
                        faq.question_embedding = _serialize_embedding(existing_embs[best_idx])
                    faq.save(update_fields=["answer_text", "ask_count", "last_asked", "question_embedding"])
                    return faq
            except Exception:
                logger.exception("FAQ duplicate check failed")

    faq = PatientFAQ.objects.create(
        patient=patient,
        question_text=question_text,
        answer_text=answer_text,
        category=category,
        ask_count=1,
        last_asked=timezone.now(),
        question_embedding=question_embedding_bytes,
    )
    logger.info("Stored new FAQ for patient %s: '%s'", patient.pk, question_text[:60])
    return faq


def get_faq_context(patient, limit: int = 5) -> str:
    """
    Build a context string of the patient's most frequently asked questions
    for injection into the system prompt.
    """
    from .models import PatientFAQ

    faqs = (
        PatientFAQ.objects.filter(patient=patient)
        .order_by("-ask_count")[:limit]
    )
    if not faqs:
        return ""

    lines = [
        "PATIENT'S FREQUENTLY ASKED QUESTIONS (answer with the EXACT same "
        "wording each time — consistency comforts dementia patients):"
    ]
    for faq in faqs:
        lines.append(
            f'Q: "{faq.question_text}"\n'
            f'A: "{faq.answer_text}" (asked {faq.ask_count} times)'
        )
    return "\n\n".join(lines)
