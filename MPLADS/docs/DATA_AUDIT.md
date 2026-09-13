# Data audit

## Result

Audit completed on 2026-09-06 against the twelve supplied `.xlsx` workbooks. All expected files are present, each has one observed `Sheet1`, and each has a complete unique header in source row 2. The complete, machine-readable evidence is in [generated/source_audit.json](generated/source_audit.json); the human-readable column/null profile is [generated/source_audit.md](generated/source_audit.md).

The workbooks do not contain a dedicated House column. House is assigned from the user-declared `lok_sabha` / `rajya_sabha` intake folders and required 1–12 ordering, then corroborated by the observed schemas: Lok Sabha workbooks carry `Constituency`, while Rajya Sabha workbooks carry `Elected/Nominated`.

| # | House | Domain | Data rows | Columns | Exact duplicate source rows | Audit status |
|---:|---|---|---:|---:|---:|---|
| 1 | LOK_SABHA | ALLOCATED_LIMIT | 544 | 5 | 0 | PASSED_SOURCE_AUDIT |
| 2 | LOK_SABHA | CALAMITY | 13 | 6 | 0 | PASSED_SOURCE_AUDIT |
| 3 | LOK_SABHA | WORKS_RECOMMENDED | 103,424 | 11 | 0 | PASSED_SOURCE_AUDIT |
| 4 | LOK_SABHA | WORKS_SANCTIONED | 32,001 | 12 | 0 | PASSED_SOURCE_AUDIT |
| 5 | LOK_SABHA | EXPENDITURE | 10,001 | 11 | 0 | PASSED_SOURCE_AUDIT |
| 6 | LOK_SABHA | WORKS_COMPLETED | 33,983 | 11 | 0 | PASSED_SOURCE_AUDIT |
| 7 | RAJYA_SABHA | ALLOCATED_LIMIT | 232 | 5 | 0 | PASSED_SOURCE_AUDIT |
| 8 | RAJYA_SABHA | CALAMITY | 21 | 6 | 0 | PASSED_SOURCE_AUDIT |
| 9 | RAJYA_SABHA | WORKS_RECOMMENDED | 22,001 | 11 | 0 | PASSED_SOURCE_AUDIT |
| 10 | RAJYA_SABHA | WORKS_SANCTIONED | 19,331 | 12 | 0 | PASSED_SOURCE_AUDIT |
| 11 | RAJYA_SABHA | EXPENDITURE | 24,980 | 11 | 0 | PASSED_SOURCE_AUDIT |
| 12 | RAJYA_SABHA | WORKS_COMPLETED | 9,914 | 11 | 0 | PASSED_SOURCE_AUDIT |

## Observed quality findings

- `Sr. No.` is unique within every dataset. It is a source sequence, not a cross-dataset key.
- No exact duplicate data rows were found in any dataset.
- Work IDs are explicit in both expenditure files. In sanctioned and completed files they are embedded in `Work`; they are parsed only when matching the observed `WS/MP<number>/<financial-year>/<number>` pattern after incidental spaces are removed.
- The two recommended-work files contain unresolved source labels: 25,441 Lok Sabha and 3,332 Rajya Sabha values begin with `NA-`; one row in each is blank. These must stay out of canonical Work-ID joins unless a future supplied source resolves them.
- One blank Work-ID/work-label value appears in each sanctioned, expenditure, and completed dataset. It is a visible data-quality issue, not a zero or synthetic ID.
- No normalized Work ID occurs in both Houses in this intake. The canonical key remains `house:work_id` regardless, so future collisions cannot merge records across Houses.
- `Sanction Date` in the recommended-work sources is mixed text rather than universally date-formatted. Preserve the raw value and validate parsing per row.
- The XML workbook style layer is incompatible with the installed `openpyxl` reader. The audit reads the underlying `.xlsx` worksheet values directly and never changes the supplied files.

## Audit decision

The source-audit gate is passed. The next permitted work is raw/staging ingestion with row-level validation, preserving the original files and unresolved records. No dataset version is approved, promoted, or active yet.
| Pending | Pending | Pending | Pending | Pending |
