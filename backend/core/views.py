"""Tiny views for non-API routes (e.g. Hugging Face Space iframe loads `/`)."""

from django.http import HttpResponse, JsonResponse


def hf_space_root(request):
    """HF embeds the app origin in an iframe; without this, `/` 404 looks like a broken Space."""
    return HttpResponse(
        "<!DOCTYPE html><html><head><meta charset='utf-8'><title>DementiaNext API</title></head>"
        "<body style='font-family:system-ui;margin:2rem;'>"
        "<h1>DementiaNext backend</h1>"
        "<p>This Space exposes a REST API. The web UI is on Vercel.</p>"
        "<p><a href='/api/health'>/api/health</a> — liveness check</p>"
        "</body></html>",
        content_type="text/html; charset=utf-8",
    )


def health_check(_request):
    return JsonResponse({"status": "ok"})
