# Ingestion report

Batch: `cc8d5102-096c-5836-8957-cadd323d2965`.

Source rows: **256,445**. Staged rows: **256,445**.

| # | House | Dataset | Source | Staged | Valid | Warning | Rejected | Unresolved | Blank ID |
|---:|---|---|---:|---:|---:|---:|---:|---:|---:|
| 1 | LOK_SABHA | ALLOCATED_LIMIT | 544 | 544 | 542 | 0 | 2 | 0 | 0 |
| 2 | LOK_SABHA | CALAMITY | 13 | 13 | 12 | 1 | 0 | 0 | 0 |
| 3 | LOK_SABHA | WORKS_RECOMMENDED | 103,424 | 103,424 | 77,980 | 25,441 | 3 | 25,441 | 1 |
| 4 | LOK_SABHA | WORKS_SANCTIONED | 32,001 | 32,001 | 32,000 | 0 | 1 | 0 | 1 |
| 5 | LOK_SABHA | EXPENDITURE | 10,001 | 10,001 | 10,000 | 0 | 1 | 0 | 1 |
| 6 | LOK_SABHA | WORKS_COMPLETED | 33,983 | 33,983 | 33,905 | 77 | 1 | 0 | 1 |
| 7 | RAJYA_SABHA | ALLOCATED_LIMIT | 232 | 232 | 231 | 0 | 1 | 0 | 0 |
| 8 | RAJYA_SABHA | CALAMITY | 21 | 21 | 20 | 1 | 0 | 0 | 0 |
| 9 | RAJYA_SABHA | WORKS_RECOMMENDED | 22,001 | 22,001 | 18,668 | 3,331 | 2 | 3,332 | 1 |
| 10 | RAJYA_SABHA | WORKS_SANCTIONED | 19,331 | 19,331 | 19,330 | 0 | 1 | 0 | 1 |
| 11 | RAJYA_SABHA | EXPENDITURE | 24,980 | 24,980 | 24,979 | 0 | 1 | 0 | 1 |
| 12 | RAJYA_SABHA | WORKS_COMPLETED | 9,914 | 9,914 | 9,895 | 18 | 1 | 0 | 1 |

## Canonical records

- `canonical_works`: 97,516
- `recommended_records`: 125,420
- `sanctioned_records`: 51,330
- `completed_records`: 43,895
- `expenditure_transactions`: 34,979
- `allocated_limit_records`: 773
- `calamity_records`: 34

House assignment is derived from controlled dataset intake grouping because the source files do not contain a House field. Source workbooks were not modified.
