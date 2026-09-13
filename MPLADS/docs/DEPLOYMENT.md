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

- `APP_ENV`
- `DATABASE_URL`
- `API_PREFIX`
- `CORS_ORIGINS`
- `MAX_UPLOAD_BYTES`
- `GEMINI_API_KEY`
- `GEMINI_MODEL`

Only `GEMINI_API_KEY` is a provider credential. Keep it backend-only. The frontend must never receive it.

## Frontend

Build the Vite frontend from `C:\Projects\MPLADS\frontend`:

```powershell
npm run build
```

The output is `frontend/dist`. Its only API configuration is the public-safe `VITE_API_BASE_URL`; it must point to the backend API prefix. Do not place backend credentials, database connection strings, or Gemini configuration in a `VITE_` variable.

## Database and releases

Back up the production database before migrations. Confirm the migration revision and active dataset using the health endpoint after startup. Dataset lifecycle operations must remain in the API: an administrator may only approve, promote, or roll back through the existing validation and atomic-release safeguards. Never make a second release active directly in the database.

## CORS, TLS, and rollback

Set `CORS_ORIGINS` to the exact deployed frontend origin or origins; do not use a wildcard for an authenticated administrative deployment. Terminate TLS at the approved gateway or reverse proxy and forward only the intended API routes.

For an application rollback, deploy the previous compatible application version. For a database rollback, use a verified backup or an Alembic downgrade only after validating that the target revision is compatible with retained release and audit history. Do not delete audit records or source data as a rollback shortcut.

## Required pre-deployment checks

Run the production checklist and security review in this directory. Deployment remains blocked until a real production identity provider or trusted authentication gateway replaces development request-header identity handling.
