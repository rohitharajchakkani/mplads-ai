"""Minimal, secret-safe Gemini provider boundary for future backend features."""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

from app.core.config import Settings, get_settings


class GeminiConfigurationError(RuntimeError):
    """Raised without credential details when Gemini cannot be initialized."""


@dataclass(frozen=True)
class GeminiProviderStatus:
    configured: bool
    provider: str
    model: str | None
    message: str


def provider_status(settings: Settings | None = None) -> GeminiProviderStatus:
    settings = settings or get_settings()
    if not settings.gemini_api_key:
        return GeminiProviderStatus(False, "Gemini", settings.gemini_model, "Gemini provider is not configured.")
    if not settings.gemini_model.strip():
        return GeminiProviderStatus(False, "Gemini", None, "Gemini provider model is not configured.")
    return GeminiProviderStatus(True, "Gemini", settings.gemini_model, "Gemini provider is configured.")


@lru_cache
def get_gemini_client():
    settings = get_settings()
    status = provider_status(settings)
    if not status.configured:
        raise GeminiConfigurationError(status.message)
    try:
        from google import genai
        return genai.Client(api_key=settings.gemini_api_key)
    except ImportError as exc:
        raise GeminiConfigurationError("Gemini provider SDK is unavailable.") from exc
    except Exception as exc:
        raise GeminiConfigurationError("Gemini provider could not be initialized.") from exc


def generate_text(contents: str, *, settings: Settings | None = None) -> str:
    """Future backend-only invocation abstraction; no API route uses this yet."""
    resolved = settings or get_settings()
    status = provider_status(resolved)
    if not status.configured:
        raise GeminiConfigurationError(status.message)
    client = get_gemini_client() if settings is None else _client_for_settings(resolved)
    response = client.models.generate_content(model=resolved.gemini_model, contents=contents)
    return response.text or ""


def _client_for_settings(settings: Settings):
    try:
        from google import genai
        return genai.Client(api_key=settings.gemini_api_key)
    except ImportError as exc:
        raise GeminiConfigurationError("Gemini provider SDK is unavailable.") from exc
