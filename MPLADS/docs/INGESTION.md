# Ingestion

## Controlled flow

`immutable .xlsx source -> staging domain record -> row validation -> canonical record when linkage is reliable`

The original workbooks are read without modification. The XML worksheet values are read directly because the supplied style metadata is incompatible with the installed `openpyxl` reader. This affects presentation metadata only; no source cell values are changed.

House assignment is derived from controlled dataset intake grouping because the source files do not contain a House field.

## Running the intake

```powershell
cd backend
python -m alembic -c alembic.ini upgrade head
python -m app.ingestion.run --manifest ..\data\dataset_assignments.json --data-root ..\data --database-url sqlite:///../data/processed/mplads_ai.sqlite --output-dir ..\docs\generated
```

The batch identity is deterministically derived from source checksums and ingestion-transformation version. Re-running the same source and code returns the completed batch; it does not create duplicate records. A failed batch remains recorded and cannot be overwritten.

## Linkage

Only `house + normalized_work_id` links lifecycle stages. `NA-…` and blank source references stay in staging and lifecycle records with a null canonical-work link. They are never guessed, deleted, or matched by descriptive similarity.
