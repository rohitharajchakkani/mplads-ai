# Metrics

| Metric | Database formula | Grain / limitation |
|---|---|---|
| Total canonical works | `COUNT(DISTINCT works.canonical_work_key)` | Resolved canonical works only; House is part of identity. |
| Recommended / sanctioned / completed works | `COUNT(DISTINCT lifecycle_record.canonical_work_key)` | Requires a resolved canonical relationship; unresolved source rows remain visible through data quality. |
| Total sanction amount | `SUM(sanctioned_work_records.sanction_amount)` | Only active, filter-matching records. |
| Total expenditure | `SUM(expenditure_transactions.disbursed_amount)` | Valid linked transactions, never expenditure-row-as-work counts. |
| Allocation | `SUM(allocated_limit_records.allocated_amount)` | Allocation domain; never assigned to a work. |
| Calamity amount | `SUM(calamity_records.consent_amount)` | Calamity domain; never assigned to a work. |
| Lifecycle duration | Date difference only where both dates parse | Called “Observed lifecycle duration”; no policy deadline or delay verdict. |

The source provides `Work category`, but not a verified sector/subsector data field. Analytics expose the source category distribution and report sector/subsector as unavailable. Status analytics preserve `source_status`; there is no invented semantic status mapping. Physical progress is unavailable from the supplied source.
