"""
Background detection jobs (django-q on Hugging Face and similar).

Set on the server: ASYNC_DETECTION=1 to return 202 from upload_and_detect and
finish work in this task.

Set MODAL_PREPROCESSING=0 (recommended) to run the MRI pipeline inside the Space.
This repo does not ship Modal.com wiring; a disabled Modal workspace causes:

    modal.exception.ConflictError: workspace … is disabled
"""

from __future__ import annotations

import logging
import os
import time

logger = logging.getLogger(__name__)


def _modal_enabled() -> bool:
    return os.environ.get("MODAL_PREPROCESSING", "0").lower() in ("1", "true", "yes")


def run_detection_task(detection_id: int) -> None:
    """django-q hook: load row, run pipeline + inference in-process."""
    if _modal_enabled():
        raise RuntimeError(
            "MODAL_PREPROCESSING is enabled but this repository build runs preprocessing "
            "only inside the container. On Hugging Face → Space → Settings → Variables, "
            "set MODAL_PREPROCESSING=0 (or remove it). Re-enable a paid Modal workspace "
            "only if you vendor Modal app code compatible with your deployment."
        )

    from .models import DetectionResult
    from .views import DetectionViewSet, _finalize_detection_from_inference

    dr = DetectionResult.objects.get(pk=detection_id)
    view = DetectionViewSet()
    start = time.time()
    try:
        result = view._process_image(dr)
        elapsed = time.time() - start
        _finalize_detection_from_inference(dr, result, elapsed)
        logger.info("Detection %s completed", detection_id)
    except Exception as exc:
        logger.exception("Detection %s failed", detection_id)
        try:
            dr.refresh_from_db()
            dr.status = "failed"
            dr.error_message = str(exc)
            dr.save(update_fields=["status", "error_message", "updated_at"])
        except Exception:
            logger.exception("Could not persist failure for detection %s", detection_id)
        raise
