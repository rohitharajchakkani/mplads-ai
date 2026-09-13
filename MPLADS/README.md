# MPLADS AI

An independent public-data transparency, monitoring, analytics, and decision-support platform for MPLADS datasets. This project is not an official Government of India portal.

## Current phase

Phase 7 is complete in the local SQLite development database: the audited source datasets have been staged, validated, canonicalized, explicitly promoted to an active release, and exposed through database-backed FastAPI endpoints. The application intentionally contains no sample records, statistics, or fallback data.

## Dataset intake

Place the twelve supplied source files, unchanged, in `data/raw/inbox/`. Do not rename or reorder files after delivery. Then run:

```powershell
cd backend
python -m app.ingestion.inspect --source-dir ..\data\raw\inbox --output-dir ..\docs\generated
```

The inspector inventories files and workbook sheets, profiles observed columns, checks nulls and duplicates, and creates a draft audit. It does **not** assign a House or dataset type automatically. Assignment happens only after the source evidence is reviewed against `docs/DATASET_MANIFEST.md`.

## Local development (after dependency installation)

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
uvicorn app.main:app --reload
```

The API health endpoint is at `/api/v1/health`, and interactive documentation is at `/docs`. See [API documentation](docs/API.md), [ingestion documentation](docs/INGESTION.md), and the generated [validation report](docs/generated/validation_report.md).

## Repository layout

- `data/raw/` — immutable supplied files (git-ignored except directory markers)
- `backend/` — FastAPI service, ingestion pipeline, database and analytics layers
- `frontend/` — React/Vite public client (intentionally not yet implemented)
- `docs/` — audit, schema, architecture and methodology documentation
