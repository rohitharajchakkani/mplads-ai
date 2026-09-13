# Validation

## Severity policy

- `ERROR`: a required value is absent or invalid. The source row remains staged, but it is excluded from canonical promotion.
- `WARNING`: a non-fatal parsing, missing-value, or unresolved-reference issue. The source row remains staged and may retain a null canonical relationship.
- `INFO`: reserved for source-state observations that do not indicate an error.

## Implemented checks

- Required source fields by audited domain
- Monetary parsing without zero substitution
- `dd-MMM-yyyy` date parsing while retaining raw source text
- Work-ID extraction and House-safe canonical key construction
- Unresolved `NA-…` and blank work-reference retention
- Source row provenance, checksums, dataset assignment and validation finding traceability
- Transaction-level expenditure and separated allocation/calamity domains

The measured result of the current validated batch is in [generated/validation_report.md](generated/validation_report.md). Source-audit duplicate checks remain in [DATA_AUDIT.md](DATA_AUDIT.md); no duplicate records are introduced during idempotent reruns.
