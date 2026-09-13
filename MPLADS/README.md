# MPLADS AI

An independent public-data transparency, monitoring, analytics, and decision-support platform for MPLADS datasets. This project is not an official Government of India portal.

## Current phase

The core implementation is complete across all phases: audited source datasets have been staged, validated, canonicalized, promoted to an active release, and exposed through database-backed FastAPI endpoints and a full-featured React/Vite frontend. The application intentionally contains no mock records, placeholder statistics, or fallback data.

For the comprehensive project overview, SIH problem statement, and architectural diagrams, see the [Root README](../README.md).

## Dataset intake

Place the supplied source files, unchanged, in `data/raw/inbox/`. Do not rename or reorder files after delivery. Then run:

```powershell
cd backend
python -m app.ingestion.inspect --source-dir ..\data\raw\inbox --output-dir ..\docs\generated
```

The inspector inventories files and workbook sheets, profiles observed columns, checks nulls and duplicates, and creates a draft audit. It does **not** assign a House or dataset type automatically. Assignment happens only after the source evidence is reviewed against `docs/DATASET_MANIFEST.md`.

## Local development

### Backend (FastAPI)
```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```
- Interactive API documentation: `http://localhost:8000/docs`
- Health check: `http://localhost:8000/api/v1/health`

### Frontend (React / Vite)
```powershell
cd frontend
npm install
npm run dev
```
- Web application: `http://localhost:5173`

See [API documentation](docs/API.md), [System Architecture](docs/ARCHITECTURE.md), and [Validation Report](docs/generated/validation_report.md).

## Repository layout

- `data/raw/` — immutable supplied files (git-ignored except directory markers)
- `data/processed/` — SQLite database store (git-ignored)
- `backend/` — FastAPI service, ingestion pipeline, database models, analytics, and Ask AI layer
- `frontend/` — React 19 / Vite client with interactive dashboards, monitoring views, review workflow, and print-safe reporting
- `docs/` — audit, schema, architecture, analytics, and operational documentation
