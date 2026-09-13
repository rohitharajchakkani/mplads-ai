# Security review

## Reviewed controls

- Admin routes are protected server-side by `require_platform_administrator`; a browser route or URL parameter does not grant access.
- Consequential administration actions additionally require an actor, a confirmation value, and create an append-only `AdminAuditEvent`.
- Role/scope assignment is validated server-side: MP, district, and state roles require exactly their matching scope; Ministry and Platform Administrator cannot carry a narrower scope.
- Dataset promotion and rollback call the existing versioning service, preserving its lifecycle gate and one-active-release invariant.
- Administrative list endpoints use bounded page sizes and typed filter values.
- Administrative dashboard values are loaded from the database/services; raw source files and rows are not returned.
- Administrative audit aggregation minimizes review, recommendation, and AI metadata. Ask AI question text and provider credentials are not returned.
- SQLAlchemy ORM queries bind user values rather than constructing raw SQL from filters.
- The backend has configured CORS origins, safe error messages, and `nosniff`, frame-denial, and referrer-policy response headers.
- Gemini is backend-only; verified tool results are used by the grounded Ask AI flow rather than forwarding the database or source files.

## Hardened control: production authentication boundary

**Status: Hardened and verified.** The backend enforces an explicit fail-closed authentication boundary:
- When `ALLOW_DEV_HEADERS=true` (default in `development`), direct `X-MPLADS-*` identity headers are accepted for local pair-programming, API testing, and UI verification.
- When `ALLOW_DEV_HEADERS=false` (default in `production`), direct `X-MPLADS-*` headers from untrusted clients or browsers are strictly rejected with `HTTP 401 Unauthorized` (`AUTHENTICATION_GATEWAY_REQUIRED`).
- Protected endpoints require an authenticating reverse proxy or API gateway to forward requests accompanied by `X-Gateway-Secret` matching `GATEWAY_SHARED_SECRET`.
- Verification uses constant-time string comparison (`hmac.compare_digest`) to prevent timing attacks, and secrets are never returned in error responses.
- Public transparency endpoints (`/health`, `/dashboard/*`, `/works/*`, `/analytics/*`) remain publicly accessible without requiring credentials.

## Operational guidance

Keep `.env` files untracked, redact credentials from logs, restrict database network access to the backend, keep CORS to explicit origins, and do not enable `ALLOW_DEV_HEADERS` in production. Audit records must be retained through upgrade and rollback operations. The direct Render backend URL must not be published to end-users to prevent bypassing the authenticating gateway.
