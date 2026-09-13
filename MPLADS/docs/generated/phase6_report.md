# Phase 6 report

Active release: `phase5-v2:cc8d5102`.
Batch: `cc8d5102-096c-5836-8957-cadd323d2965`.
Release status: `ACTIVE`.

## Integrity

- `expected_dataset_versions_present`: True
- `source_to_staging_row_loss`: 0
- `canonical_key_mismatch_count`: 0
- `cross_house_work_id_collision_count`: 0
- `unmatched_valid_expenditure_transaction_count`: 0
- `foreign_key_violation_count`: 0
- `passed`: True

## Core metrics

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

## Lifecycle

- `terminology`: Observed lifecycle duration
- `recommendation_to_sanction`: {'count_with_both_dates': 51330, 'median_days': 83.0, 'mean_days': 116.98400545489967, 'p25_days': 42.0, 'p50_days': 83.0, 'p75_days': 152.0, 'p90_days': 264.0, 'min_days': 0.0, 'max_days': 1100.0}
- `sanction_to_completion`: {'count_with_both_dates': 30656, 'median_days': 183.0, 'mean_days': 205.16727557411272, 'p25_days': 86.0, 'p50_days': 183.0, 'p75_days': 302.0, 'p90_days': 416.5, 'min_days': 0.0, 'max_days': 948.0}
- `right_censored_sanctioned_work_count`: 20674
- `completion_ratio`: 0.5972335865965323

The values above are calculated from the active database release at report generation time. No frontend or static analytical data was created.
