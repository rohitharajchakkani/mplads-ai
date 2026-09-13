# Validation report

Validated batch: `cc8d5102-096c-5836-8957-cadd323d2965`.

Ingestion version: `phase5-v2`. Application version: `0.1.0`. Database status: `VALIDATED`.

## Row outcomes

| Dataset | House | Source | Staged | Valid | Warning | Rejected |
|---|---|---:|---:|---:|---:|---:|
| ALLOCATED_LIMIT | LOK_SABHA | 544 | 544 | 542 | 0 | 2 |
| CALAMITY | LOK_SABHA | 13 | 13 | 12 | 1 | 0 |
| EXPENDITURE | LOK_SABHA | 10,001 | 10,001 | 10,000 | 0 | 1 |
| WORKS_COMPLETED | LOK_SABHA | 33,983 | 33,983 | 33,905 | 77 | 1 |
| WORKS_RECOMMENDED | LOK_SABHA | 103,424 | 103,424 | 77,980 | 25,441 | 3 |
| WORKS_SANCTIONED | LOK_SABHA | 32,001 | 32,001 | 32,000 | 0 | 1 |
| ALLOCATED_LIMIT | RAJYA_SABHA | 232 | 232 | 231 | 0 | 1 |
| CALAMITY | RAJYA_SABHA | 21 | 21 | 20 | 1 | 0 |
| EXPENDITURE | RAJYA_SABHA | 24,980 | 24,980 | 24,979 | 0 | 1 |
| WORKS_COMPLETED | RAJYA_SABHA | 9,914 | 9,914 | 9,895 | 18 | 1 |
| WORKS_RECOMMENDED | RAJYA_SABHA | 22,001 | 22,001 | 18,668 | 3,331 | 2 |
| WORKS_SANCTIONED | RAJYA_SABHA | 19,331 | 19,331 | 19,330 | 0 | 1 |

## Findings

- Errors: 38
- Warnings: 57,667

| Code | Count | Interpretation |
|---|---:|---|
| BLANK_SOURCE_WORK_REFERENCE | 8 | Retained source row has no usable Work ID/label. |
| MALFORMED_DATE | 28,775 | Preserved source text cannot be parsed as the observed date format. |
| MISSING_CRITICAL_FIELD | 37 | Required source field is blank; the staging record is retained and rejected from canonical promotion. |
| MISSING_DATE | 12 | Date source value is blank. |
| MISSING_MONEY | 100 | Monetary source value is blank; it is not converted to zero. |
| UNRESOLVED_SOURCE_WORK_REFERENCE | 28,773 | Retained source work label cannot safely link to a canonical work. |

Most `MALFORMED_DATE` findings are the source value `NA` in recommended-work `Sanction Date`; it indicates no parseable sanction date and remains raw source text. Two other values in that field are non-date numeric strings. The validation layer does not repair either condition.

## Canonical output

- `canonical_works`: 97,516
- `recommended_records`: 125,420
- `sanctioned_records`: 51,330
- `completed_records`: 43,895
- `expenditure_transactions`: 34,979
- `allocated_limit_records`: 773
- `calamity_records`: 34

No source files were changed. House assignment is intake-derived because the workbooks do not have a House field. Rejected records remain traceable in staging and validation findings; unresolved records are retained without speculative linkage.
