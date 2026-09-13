# MPLADS AI deployment preparation

This repository is prepared for deployment; this document does not deploy it. Run each command from the stated directory and supply environment values through the deployment platform, never through committed files.

## Backend

The backend is a FastAPI application. Its local development entry point is:

```powershell
python -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000
```

Apply migrations before starting an updated backend:

```powershell
Set-Location C:\Projects\MPLADS\backend
$env:PYTHONPATH = "."
python -m alembic upgrade head
```

The health check is `GET /api/v1/health`. It reports application, database, active-release, and migration state without returning credentials.

The backend configuration loader reads `C:\Projects\MPLADS\backend\.env` in local development. Process environment variables take precedence. Deployment must configure the following names through its secret/configuration manager:

- `APP_ENV`: Application environment (`production` in deployment; `development` locally).
- `ALLOW_DEV_HEADERS`: Explicit gateway gate (`false` in production; `true` in local development).
- `GATEWAY_SHARED_SECRET`: Cryptographic shared secret known only to the trusted reverse proxy / authenticating gateway and the backend.
- `DATABASE_URL`: SQLAlchemy connection string.
- `API_PREFIX`: Route prefix (`/api/v1`).
- `CORS_ORIGINS`: Approved frontend origins.
- `MAX_UPLOAD_BYTES`: Maximum upload size in bytes.
- `GEMINI_API_KEY`: Google Gemini API key (server-side only).
- `GEMINI_MODEL`: Model identifier (`gemini-2.5-flash`).

Only `GEMINI_API_KEY` and `GATEWAY_SHARED_SECRET` are sensitive credentials. Keep them strictly backend/gateway-only. The frontend must never receive them.

## Frontend

Build the Vite frontend from `C:\Projects\MPLADS\frontend`:

```powershell
npm run build
```

The output is `frontend/dist`. Its only API configuration is the public-safe `VITE_API_BASE_URL`; it must point to the gateway or backend API prefix. Do not place backend credentials, database connection strings, gateway secrets, or Gemini configuration in a `VITE_` variable.

## Database and releases

Back up the production database before migrations. Confirm the migration revision and active dataset using the health endpoint after startup. Dataset lifecycle operations must remain in the API: an administrator may only approve, promote, or roll back through the existing validation and atomic-release safeguards. Never make a second release active directly in the database.

## CORS, TLS, and rollback

Set `CORS_ORIGINS` to the exact deployed frontend origin or origins; do not use a wildcard for an authenticated administrative deployment. Terminate TLS at the approved gateway or reverse proxy and forward only the intended API routes.

For an application rollback, deploy the previous compatible application version. For a database rollback, use a verified backup or an Alembic downgrade only after validating that the target revision is compatible with retained release and audit history. Do not delete audit records or source data as a rollback shortcut.

## Production authentication boundary and gateway routing

The backend enforces a fail-closed production authentication boundary:
- **Local development:** When `ALLOW_DEV_HEADERS=true` (the default in `development`), direct client `X-MPLADS-*` identity headers are accepted for local verification.
- **Production deployment:** When `ALLOW_DEV_HEADERS=false` (the default in `production`), all direct `X-MPLADS-*` headers from browsers or clients are rejected with `HTTP 401 Unauthorized`.
- **Gateway protection:** In production, protected endpoints require an authenticating reverse proxy or API gateway that validates user identity, strips untrusted client headers, injects verified role/scope claims, and supplies `X-Gateway-Secret` matching `GATEWAY_SHARED_SECRET`.
- **No direct bypass:** The direct Render backend URL must not be published to end-users to prevent bypassing the authenticating gateway. Public transparency endpoints (`/health`, `/dashboard/*`, `/works/*`, `/analytics/*`) remain publicly accessible without gateway credentials.
