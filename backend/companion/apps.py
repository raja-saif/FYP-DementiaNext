import threading

from django.apps import AppConfig


class CompanionConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "companion"
    verbose_name = "DementiaNext Companion"

    def ready(self):
        threading.Thread(target=self._warmup_rag, daemon=True).start()
        threading.Thread(target=self._warmup_faq_model, daemon=True).start()

    @staticmethod
    def _warmup_rag():
        try:
            from . import rag_engine
            rag_engine.warm_up()
        except Exception:
            pass

    @staticmethod
    def _warmup_faq_model():
        try:
            from .faq_detector import _get_model
            _get_model()
        except Exception:
            pass
