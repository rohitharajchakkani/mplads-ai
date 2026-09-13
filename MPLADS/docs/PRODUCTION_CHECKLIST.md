# Production checklist

## Environment and secrets

- [ ] `backend/.env` is ignored locally and no secret is committed.
- [ ] Production supplies backend variables through a secret/configuration manager.
- [ ] `GEMINI_API_KEY` is available only to the backend process.
- [ ] The frontend has only public-safe `VITE_API_BASE_URL` configuration.
- [ ] `APP_ENV` is set to the intended deployment mode.
- [ ] `CORS_ORIGINS` names only approved frontend origins.

## Application and database

- [ ] `python -m alembic upgrade head` completes against the deployment database.
- [ ] `GET /api/v1/health` reports database and migration health.
- [ ] Exactly one active dataset release is available.
- [ ] Database backup and restore procedures have been exercised.
- [ ] The deployment uses a TLS-terminating gateway or reverse proxy.

## Access and operations

- [ ] A production identity provider or trusted gateway provides authenticated principal, role, actor, and scope claims.
- [ ] Header values from untrusted browsers cannot establish an administrator identity.
- [ ] Platform-administrator access to `/api/v1/admin/*` is verified server-side.
- [ ] Access, role/scope, release, and review/recommendation events appear in append-only audit surfaces.
- [ ] Gemini status is reported safely; its credential is never rendered or logged.

## Build and verification

- [ ] `npx tsc -b` passes.
- [ ] `npm run build` passes.
- [ ] Backend tests pass on an isolated test database.
- [ ] Frontend tests and Playwright smoke checks pass.
- [ ] Static scans find no committed credential or production mock data.

## Current release blocker

The current development identity mechanism accepts MPLADS role/scope request headers. It is adequate for local verification but is not a production authentication boundary. Production deployment is blocked until those headers are populated and integrity-protected by a real IdP or trusted gateway, with direct browser spoofing prevented.
