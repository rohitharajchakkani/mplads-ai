"""Gemini configuration tests do not require or reveal a real credential."""
from dataclasses import replace
from unittest.mock import MagicMock, patch

import pytest

from app.ai.gemini_provider import GeminiConfigurationError, generate_text, get_gemini_client, provider_status
from app.core.config import Settings


def settings(key: str | None = None, model: str = "gemini-2.5-flash") -> Settings:
    return Settings("test", "sqlite://", "/api/v1", "http://localhost", 1, key, model)


def test_missing_key_is_not_configured_and_does_not_leak_secret():
    status = provider_status(settings())
    assert not status.configured and "key" not in status.message.lower()
    with pytest.raises(GeminiConfigurationError, match="not configured"):
        generate_text("unused", settings=settings())


def test_configured_status_exposes_model_but_never_key():
    status = provider_status(settings("test-secret-value"))
    assert status.configured and status.model == "gemini-2.5-flash"
    assert "test-secret-value" not in repr(status)


def test_blank_model_is_treated_as_malformed_configuration():
    status = provider_status(settings("test-secret-value", " "))
    assert not status.configured and status.model is None


def test_initialization_and_invocation_use_official_client_without_logging_secret():
    fake_response = MagicMock(text="safe response")
    fake_client = MagicMock(); fake_client.models.generate_content.return_value = fake_response
    with patch("google.genai.Client", return_value=fake_client) as client:
        assert generate_text("minimal provider test", settings=settings("test-secret-value")) == "safe response"
    client.assert_called_once_with(api_key="test-secret-value")
    fake_client.models.generate_content.assert_called_once_with(model="gemini-2.5-flash", contents="minimal provider test")
