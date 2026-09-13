"""Tests for production authentication hardening and gateway secret verification."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings, get_settings
from app.main import app

client = TestClient(app)

PROD_SECRET = "production-test-gateway-secret-999"


def prod_settings(gateway_secret: str | None = PROD_SECRET) -> Settings:
    base = get_settings()
    return Settings(
        app_env="production",
        database_url=base.database_url,
        api_prefix=base.api_prefix,
        cors_origins=base.cors_origins,
        max_upload_bytes=base.max_upload_bytes,
        gemini_api_key=base.gemini_api_key,
        gemini_model=base.gemini_model,
        allow_dev_headers=False,
        gateway_shared_secret=gateway_secret,
    )


def dev_settings() -> Settings:
    base = get_settings()
    return Settings(
        app_env="development",
        database_url=base.database_url,
        api_prefix=base.api_prefix,
        cors_origins=base.cors_origins,
        max_upload_bytes=base.max_upload_bytes,
        gemini_api_key=base.gemini_api_key,
        gemini_model=base.gemini_model,
        allow_dev_headers=True,
        gateway_shared_secret=None,
    )


@pytest.fixture(autouse=True)
def cleanup_overrides():
    yield
    app.dependency_overrides.clear()


def test_production_rejects_spoofed_role_without_gateway_secret():
    """In production, sending X-MPLADS-Role without a gateway secret must return 401."""
    app.dependency_overrides[get_settings] = lambda: prod_settings()

    response = client.get(
        "/api/v1/risk/summary",
        headers={"X-MPLADS-Role": "MINISTRY"},
    )
    assert response.status_code == 401
    body = response.json()
    assert body["detail"]["code"] == "AUTHENTICATION_GATEWAY_REQUIRED"
    assert PROD_SECRET not in str(body)


def test_production_rejects_spoofed_headers_with_invalid_gateway_secret():
    """In production, sending an invalid gateway secret must return 401 without leaking secret."""
    app.dependency_overrides[get_settings] = lambda: prod_settings()

    response = client.get(
        "/api/v1/risk/summary",
        headers={
            "X-MPLADS-Role": "MINISTRY",
            "X-Gateway-Secret": "wrong-attacker-secret",
        },
    )
    assert response.status_code == 401
    body = response.json()
    assert body["detail"]["code"] == "AUTHENTICATION_GATEWAY_REQUIRED"
    assert PROD_SECRET not in str(body)


def test_production_accepts_valid_gateway_secret_with_valid_role():
    """In production, a valid gateway secret along with valid role proceeds to endpoint."""
    app.dependency_overrides[get_settings] = lambda: prod_settings()

    response = client.get(
        "/api/v1/risk/summary",
        headers={
            "X-MPLADS-Role": "MINISTRY",
            "X-Gateway-Secret": PROD_SECRET,
        },
    )
    assert response.status_code == 200
    assert "provenance" in response.json()


def test_production_fails_closed_when_gateway_secret_not_configured():
    """In production, if GATEWAY_SHARED_SECRET is not configured, protected endpoints fail closed."""
    app.dependency_overrides[get_settings] = lambda: prod_settings(gateway_secret=None)

    response = client.get(
        "/api/v1/risk/summary",
        headers={
            "X-MPLADS-Role": "MINISTRY",
            "X-Gateway-Secret": "some-secret",
        },
    )
    assert response.status_code == 401
    body = response.json()
    assert body["detail"]["code"] == "AUTHENTICATION_GATEWAY_REQUIRED"


def test_development_mode_allows_direct_dev_headers():
    """In development mode with allow_dev_headers=True, direct role headers succeed as before."""
    app.dependency_overrides[get_settings] = lambda: dev_settings()

    response = client.get(
        "/api/v1/risk/summary",
        headers={"X-MPLADS-Role": "MINISTRY"},
    )
    assert response.status_code == 200
    assert "provenance" in response.json()


def test_production_mode_preserves_public_endpoints():
    """Public transparency endpoints must remain accessible in production without auth headers."""
    app.dependency_overrides[get_settings] = lambda: prod_settings()

    # Health check
    health_res = client.get("/api/v1/health")
    assert health_res.status_code == 200
    assert health_res.json()["status"] == "ok"

    # Dashboard summary
    dash_res = client.get("/api/v1/dashboard/summary")
    assert dash_res.status_code == 200
    assert "provenance" in dash_res.json()

    # Public works listing
    works_res = client.get("/api/v1/works?limit=5")
    assert works_res.status_code == 200
    assert "items" in works_res.json()


def test_production_admin_routes_require_both_gateway_secret_and_admin_role():
    """Admin endpoints require valid gateway secret AND platform administrator role."""
    app.dependency_overrides[get_settings] = lambda: prod_settings()

    # Attempt admin system with spoofed header but no gateway secret => 401
    unauth_res = client.get(
        "/api/v1/admin/system",
        headers={"X-MPLADS-Role": "PLATFORM_ADMINISTRATOR", "X-MPLADS-Actor": "admin-test"},
    )
    assert unauth_res.status_code == 401

    # Attempt admin system with gateway secret but non-admin role => 403
    forbidden_res = client.get(
        "/api/v1/admin/system",
        headers={
            "X-MPLADS-Role": "MINISTRY",
            "X-Gateway-Secret": PROD_SECRET,
        },
    )
    assert forbidden_res.status_code == 403

    # Authorized admin request with both gateway secret and platform administrator role => 200
    admin_res = client.get(
        "/api/v1/admin/system",
        headers={
            "X-MPLADS-Role": "PLATFORM_ADMINISTRATOR",
            "X-MPLADS-Actor": "admin-test",
            "X-Gateway-Secret": PROD_SECRET,
        },
    )
    assert admin_res.status_code == 200
