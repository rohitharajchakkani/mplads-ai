# Dataset manifest

## Intake `intake-2026-09-06`

The manifest is explicitly recorded in [data/dataset_assignments.json](../data/dataset_assignments.json). Assignment uses the supplied House folders, required ordering, and observed field semantics. It is not derived from a filename alone. All files were audited with a one-sheet (`Sheet1`) layout and header in source row 2.

| # | House | Domain | Source file | SHA-256 | Data rows | Schema | Validation | Batch | Version |
|---:|---|---|---|---|---:|---|---|---|---|
| 1 | LOK_SABHA | ALLOCATED_LIMIT | `Allocated Limit for Honble MPs.xlsx` | `7956fd…e0173` | 544 | VERIFIED_OBSERVED | PASSED_SOURCE_AUDIT | INTAKE-20260906-01 | intake-2026-09-06 |
| 2 | LOK_SABHA | CALAMITY | `Amount consented for Calamity.xlsx` | `f049f6…9a355` | 13 | VERIFIED_OBSERVED | PASSED_SOURCE_AUDIT | INTAKE-20260906-01 | intake-2026-09-06 |
| 3 | LOK_SABHA | WORKS_RECOMMENDED | `Works Recommended (2).xlsx` | `a664c4…30f9f` | 103,424 | VERIFIED_OBSERVED | PASSED_SOURCE_AUDIT | INTAKE-20260906-01 | intake-2026-09-06 |
| 4 | LOK_SABHA | WORKS_SANCTIONED | `Works Sanctioned.xlsx` | `522f3c…8452` | 32,001 | VERIFIED_OBSERVED | PASSED_SOURCE_AUDIT | INTAKE-20260906-01 | intake-2026-09-06 |
| 5 | LOK_SABHA | EXPENDITURE | `Expenditure on Completed and On-going Works as on Date.xlsx` | `195c56…8b11d` | 10,001 | VERIFIED_OBSERVED | PASSED_SOURCE_AUDIT | INTAKE-20260906-01 | intake-2026-09-06 |
| 6 | LOK_SABHA | WORKS_COMPLETED | `Works Completed.xlsx` | `4545f8…fb0b` | 33,983 | VERIFIED_OBSERVED | PASSED_SOURCE_AUDIT | INTAKE-20260906-01 | intake-2026-09-06 |
| 7 | RAJYA_SABHA | ALLOCATED_LIMIT | `Allocated Limit for Honble MPs (1).xlsx` | `dabc86…b3656` | 232 | VERIFIED_OBSERVED | PASSED_SOURCE_AUDIT | INTAKE-20260906-01 | intake-2026-09-06 |
| 8 | RAJYA_SABHA | CALAMITY | `Amount consented for Calamity (1).xlsx` | `55e299…7e5eb` | 21 | VERIFIED_OBSERVED | PASSED_SOURCE_AUDIT | INTAKE-20260906-01 | intake-2026-09-06 |
| 9 | RAJYA_SABHA | WORKS_RECOMMENDED | `Works Recommended (3).xlsx` | `c0bb6c…71694` | 22,001 | VERIFIED_OBSERVED | PASSED_SOURCE_AUDIT | INTAKE-20260906-01 | intake-2026-09-06 |
| 10 | RAJYA_SABHA | WORKS_SANCTIONED | `Works Sanctioned (1).xlsx` | `33b1b4…76ef` | 19,331 | VERIFIED_OBSERVED | PASSED_SOURCE_AUDIT | INTAKE-20260906-01 | intake-2026-09-06 |
| 11 | RAJYA_SABHA | EXPENDITURE | `Expenditure on Completed and On-going Works as on Date (1).xlsx` | `9ca6f5…601e0` | 24,980 | VERIFIED_OBSERVED | PASSED_SOURCE_AUDIT | INTAKE-20260906-01 | intake-2026-09-06 |
| 12 | RAJYA_SABHA | WORKS_COMPLETED | `Works Completed (1).xlsx` | `33a291…dadd0` | 9,914 | VERIFIED_OBSERVED | PASSED_SOURCE_AUDIT | INTAKE-20260906-01 | intake-2026-09-06 |

Full checksums and source-column profiles are retained in [generated/source_audit.json](generated/source_audit.json). Promotion is prohibited until raw/staging validation has completed.
