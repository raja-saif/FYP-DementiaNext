"""
Background detection jobs (django-q on Hugging Face, etc.).

This module does NOT use Modal.com. Preprocessing + inference run inside the same
container as Django. If logs still show ``modal.exception.ConflictError``, the
Space is running an old image or a forked file that calls Modal — rebuild the
Space from this repo's ``main`` (Factory reboot), not a cached layer.

Environment:
  ASYNC_DETECTION=1 — set on the server so ``upload_and_detect`` enqueues this
  task and returns HTTP 202 (see ``DetectionViewSet.upload_and_detect``).
"""

from __future__ import annotations

import logging
import time

logger = logging.getLogger(__name__)

_TASKS_BUILD_ID = "in-process-2026-05-10"
_tasks_boot_logged = False


def run_detection_task(detection_id: int) -> None:
    """django-q hook: load row, run pipeline + inference in-process."""
    global _tasks_boot_logged
    if not _tasks_boot_logged:
        _tasks_boot_logged = True
        logger.info(
            "detection.tasks run_detection_task build=%s (no third-party GPU sandbox)",
            _TASKS_BUILD_ID,
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
