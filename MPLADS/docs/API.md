# API

All endpoints are versioned under `/api/v1`. Interactive OpenAPI documentation is served by FastAPI at `/docs` when the backend is running.

## System and dashboard

- `GET /health` reports live application, database, migration and active-release state.
- `GET /dashboard/summary`, `/dashboard/work-status`, `/dashboard/house-comparison`, `/dashboard/state-summary`, `/dashboard/expenditure-trend`, and `/dashboard/completion-summary` return database-derived, chart-ready aggregates.
- `GET /dashboard/sector-summary` truthfully reports that verified sector/subsector analysis is unavailable from the supplied source.

## Public data endpoints

- `GET /mps`, `/states`, `/districts`, `/works` use database filtering and pagination.
- `GET /mps/{mp_id}`, `/states/{state_id}`, `/districts/{district_id}`, `/works/{canonical_work_key}` return source-backed entity detail.
- `GET /financial/summary`, `/financial/by-house`, `/financial/by-state`, `/financial/by-mp`, `/financial/by-district` operate at expenditure-transaction grain.
- `GET /trends/lifecycle`, `/trends/works`, `/trends/expenditure`, `/trends/completion` use only available source dates.
- `GET /search` searches active canonical work, MP, State, district/IDA and constituency records.
- `GET /data-quality/summary`, `/datasets/active`, and `/datasets/versions` expose controlled quality and version provenance.

## Common contracts

Analytical responses return `data` and `provenance`. Provenance includes active release version, ingestion batch, service name, generated timestamp, and applied filters. List responses use `page` and `page_size` (1–100), returning `total`, `page`, `page_size`, and `total_pages`.

The shared supported filter names are `house`, `state`, `district_or_ida`, `mp`, `constituency`, `financial_year`, and `work_status`. `sector` and `subsector` are rejected as unsupported because the source has no verified fields for them. Individual allocation/calamity domains may expose fewer filters according to their source grain.

## Errors

- `404`: entity does not exist in the active release.
- `422`: invalid identifier, filter, sort, pagination input, or unsupported analysis.
- `503`: database unavailable or no active data release.

Responses contain structured error codes; no unavailable query returns invented data.
