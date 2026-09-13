# Data dictionary

## Provenance and versioning

- `ingestion_batches`: immutable processing attempt, source-set fingerprint, application/ingestion version, operator, timestamps, status and summary.
- `dataset_versions`: one source file within a batch; records House assignment, filename, checksum, sheet, row counts and validation status.
- `validation_findings`: source-row-level `ERROR` or `WARNING`, code, field and explanation.
- Every staging table records `batch_id`, `dataset_version_id`, `source_row_number`, `source_sequence`, `source_values`, normalized candidates, validation status and work-reference status.

## Staging domains

`staging_allocated_limits`, `staging_calamity`, `staging_recommended_works`, `staging_sanctioned_works`, `staging_expenditure`, and `staging_completed_works` preserve the six observed source domains separately. Raw source values are never overwritten.

## Canonical domains

- `works`: only reliably resolved works, keyed by `canonical_work_key = house:normalized_work_id`.
- `recommended_work_records`, `sanctioned_work_records`, `completed_work_records`: lifecycle source records, each linked to a canonical work only when a resolved Work ID exists.
- `expenditure_transactions`: transaction-level payments. Multiple records may link to one work; no row is counted as a work.
- `allocated_limit_records` and `calamity_records`: separate MP-level analytical domains. They are not assigned to individual works.

`district_or_ida` preserves the audited `IDA` source value and does not assert that it is a conventional district. `completed_reported_disbursed_amount` stays distinct from transaction expenditure pending evidence-based reconciliation.
