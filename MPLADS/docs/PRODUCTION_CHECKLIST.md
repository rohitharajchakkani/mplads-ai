# Production checklist

## Environment and secrets

- [ ] `backend/.env` is ignored locally and no secret is committed.
- [ ] Production supplies backend variables through a secret/configuration manager.
- [ ] `APP_ENV` is set to `production`.
- [ ] `ALLOW_DEV_HEADERS` is set to `false` in production.
- [ ] `GATEWAY_SHARED_SECRET` is set in the backend and trusted reverse proxy only.
- [ ] `GEMINI_API_KEY` is available only to the backend process.
- [ ] The frontend has only public-safe `VITE_API_BASE_URL` configuration.
- [ ] `CORS_ORIGINS` names only approved frontend origins.

## Application and database

- [ ] `python -m alembic upgrade head` completes against the deployment database.
- [ ] `GET /api/v1/health` reports database and migration health.
- [ ] Exactly one active dataset release is available.
- [ ] Database backup and restore procedures have been exercised.
- [ ] The deployment uses a TLS-terminating gateway or reverse proxy.

## Access and operations

- [ ] An authenticating reverse proxy or API gateway provides authenticated principal, role, actor, and scope claims.
- [ ] Untrusted browser requests attempting direct `X-MPLADS-*` identity injection are rejected with `HTTP 401`.
- [ ] Gateway forwards requests with `X-Gateway-Secret` matching `GATEWAY_SHARED_SECRET`.
- [ ] Direct Render backend URL is not published to bypass the authentication gateway.
- [ ] Platform-administrator access to `/api/v1/admin/*` is verified server-side.
- [ ] Access, role/scope, release, and review/recommendation events appear in append-only audit surfaces.
- [ ] Gemini status is reported safely; its credential is never rendered or logged.

## Build and verification

- [ ] `npx tsc -b` passes.
- [ ] `npm run build` passes.
- [ ] Backend tests (including production authentication hardening) pass.
- [ ] Frontend tests and Playwright smoke checks pass.
- [ ] Static scans find no committed credential or production mock data.

## Operational gate status

Backend authentication hardening is fully implemented and verified via automated test suites. Direct client spoofing of `X-MPLADS-*` headers is rejected in production mode (`ALLOW_DEV_HEADERS=false`). Deployment readiness requires populating `GATEWAY_SHARED_SECRET` in the Render environment and configuring the reverse proxy / gateway before directing user traffic to protected monitoring features.
