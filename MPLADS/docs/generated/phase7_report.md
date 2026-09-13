# Phase 7 API report

Versioned API paths in the live OpenAPI contract: **29**.
Application status: `ok`. Database status: `ok`. Migration: `20260906_02`.
Active release: `phase5-v2:cc8d5102`.
Active dataset versions: **12**.

## Database-derived summary response

- `total_canonical_works`: 97516
- `recommended_works`: 96648
- `sanctioned_works`: 51330
- `completed_works`: 43895
- `total_sanction_amount`: 33566721242.42
- `total_expenditure`: 15826725992.69
- `mp_count`: 712
- `state_count`: 35
- `district_or_ida_count`: 769
- `sector`: {'available': False, 'message': 'Not available from the current source data; the source contains work categories, not a verified sector field.'}
- `physical_progress`: {'available': False, 'message': 'Physical progress percentage is not available in the supplied source data.'}
- `allocation`: 116819035627.53
- `calamity_amount`: 290134800.00

Every value above was obtained through the live FastAPI endpoint at report generation time. It is not embedded in the API implementation.
