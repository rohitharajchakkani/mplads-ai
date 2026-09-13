# Data audit

## Intake result

Audit generated: `2026-09-06T13:11:34.133455+00:00`.

All 12 expected `.xlsx` files were found. Every workbook contains one observed `Sheet1` worksheet with a complete, unique header in source row 2. The files are assigned using the user-declared House directories and required order, then corroborated by their observed field semantics. No source contains a dedicated House field.

The Excel style layer is malformed for the installed `openpyxl` reader. The audit read the underlying OOXML worksheet values directly, without editing source files. This is a format-compatibility finding, not a data-value change.

## Dataset inventory

| # | House | Domain | Source file | Data rows | Columns | Exact duplicate rows | Work-ID evidence | Validation |
|---:|---|---|---|---:|---:|---:|---|---|
| 1 | LOK_SABHA | ALLOCATED_LIMIT | `Allocated Limit for Honble MPs.xlsx` | 544 | 5 | 0 | Not applicable | PASSED_SOURCE_AUDIT |
| 2 | LOK_SABHA | CALAMITY | `Amount consented for Calamity.xlsx` | 13 | 6 | 0 | Not applicable | PASSED_SOURCE_AUDIT |
| 3 | LOK_SABHA | WORKS_RECOMMENDED | `Works Recommended (2).xlsx` | 103,424 | 11 | 0 | 77982 parsed / 77982 distinct | PASSED_SOURCE_AUDIT |
| 4 | LOK_SABHA | WORKS_SANCTIONED | `Works Sanctioned.xlsx` | 32,001 | 12 | 0 | 32000 parsed / 32000 distinct | PASSED_SOURCE_AUDIT |
| 5 | LOK_SABHA | EXPENDITURE | `Expenditure on Completed and On-going Works as on Date.xlsx` | 10,001 | 11 | 0 | 10000 parsed / 7542 distinct | PASSED_SOURCE_AUDIT |
| 6 | LOK_SABHA | WORKS_COMPLETED | `Works Completed.xlsx` | 33,983 | 11 | 0 | 33982 parsed / 33982 distinct | PASSED_SOURCE_AUDIT |
| 7 | RAJYA_SABHA | ALLOCATED_LIMIT | `Allocated Limit for Honble MPs (1).xlsx` | 232 | 5 | 0 | Not applicable | PASSED_SOURCE_AUDIT |
| 8 | RAJYA_SABHA | CALAMITY | `Amount consented for Calamity (1).xlsx` | 21 | 6 | 0 | Not applicable | PASSED_SOURCE_AUDIT |
| 9 | RAJYA_SABHA | WORKS_RECOMMENDED | `Works Recommended (3).xlsx` | 22,001 | 11 | 0 | 18668 parsed / 18668 distinct | PASSED_SOURCE_AUDIT |
| 10 | RAJYA_SABHA | WORKS_SANCTIONED | `Works Sanctioned (1).xlsx` | 19,331 | 12 | 0 | 19330 parsed / 19330 distinct | PASSED_SOURCE_AUDIT |
| 11 | RAJYA_SABHA | EXPENDITURE | `Expenditure on Completed and On-going Works as on Date (1).xlsx` | 24,980 | 11 | 0 | 24979 parsed / 15210 distinct | PASSED_SOURCE_AUDIT |
| 12 | RAJYA_SABHA | WORKS_COMPLETED | `Works Completed (1).xlsx` | 9,914 | 11 | 0 | 9913 parsed / 9913 distinct | PASSED_SOURCE_AUDIT |

## Observed schema and completeness

### 1. LOK_SABHA — ALLOCATED_LIMIT

SHA-256: `7956fd7470b27bc6aaba6dde170e9048beee9105db13522cb9c46c6fe4be0173`. Source sequence (`Sr. No.`) unique: `True`.

| Observed source column | Inferred storage type | Nulls |
|---|---|---:|
| Sr. No. | numeric | 0 (0.0%) |
| State | text | 1 (0.18%) |
| Hon'ble Members of Parliaments | text | 1 (0.18%) |
| Constituency | text | 1 (0.18%) |
| Allocated AMOUNT ( ₹ ) | numeric | 1 (0.18%) |

### 2. LOK_SABHA — CALAMITY

SHA-256: `f049f625f95b0927f53179932320e59bf3793cbf45c7b86a010c9cf4dbb9a355`. Source sequence (`Sr. No.`) unique: `True`.

| Observed source column | Inferred storage type | Nulls |
|---|---|---:|
| Sr. No. | text | 0 (0.0%) |
| Calamity Type | text | 1 (7.69%) |
| Calamity Name | text | 1 (7.69%) |
| Hon'ble Members of Parliament | text | 1 (7.69%) |
| Date of Consent | date_text_dd_mmm_yyyy | 1 (7.69%) |
| Consent Amount ( ₹ ) | numeric | 0 (0.0%) |

### 3. LOK_SABHA — WORKS_RECOMMENDED

SHA-256: `a664c45068db2b2882c9e8e40969718757df01adcef442107a270aadba730f9f`. Source sequence (`Sr. No.`) unique: `True`.

| Observed source column | Inferred storage type | Nulls |
|---|---|---:|
| Sr. No. | numeric | 0 (0.0%) |
| Work category | text | 1 (0.0%) |
| WORK | text | 1 (0.0%) |
| State | text | 1 (0.0%) |
| IDA | text | 1 (0.0%) |
| Hon'ble Members of Parliament | text | 1 (0.0%) |
| Constituency | text | 1 (0.0%) |
| Work description | text | 3 (0.0%) |
| Recommended date | date_text_dd_mmm_yyyy | 1 (0.0%) |
| RECOMMENDED AMOUNT   ( ₹ ) | numeric | 1 (0.0%) |
| Sanction Date | text | 0 (0.0%) |

### 4. LOK_SABHA — WORKS_SANCTIONED

SHA-256: `522f3c10e607bd9bedfd4007ad6c2c60b0e4eb33b1f4d46b3b0d6bf274f8452e`. Source sequence (`Sr. No.`) unique: `True`.

| Observed source column | Inferred storage type | Nulls |
|---|---|---:|
| Sr. No. | numeric | 0 (0.0%) |
| Work category | text | 1 (0.0%) |
| Work | text | 1 (0.0%) |
| State | text | 1 (0.0%) |
| IDA | text | 1 (0.0%) |
| Hon'ble Members of Parliament | text | 1 (0.0%) |
| Constituency | text | 1 (0.0%) |
| Work description | text | 1 (0.0%) |
| Recommended date | date_text_dd_mmm_yyyy | 1 (0.0%) |
| Sanction Date | date_text_dd_mmm_yyyy | 1 (0.0%) |
| Sanction Amount ( ₹ ) | numeric | 1 (0.0%) |
| Work Status | text | 0 (0.0%) |

### 5. LOK_SABHA — EXPENDITURE

SHA-256: `195c569f2e9e2f9980c964b150f746eb1e9531b7e380c714334acda18618b11d`. Source sequence (`Sr. No.`) unique: `True`.

| Observed source column | Inferred storage type | Nulls |
|---|---|---:|
| Sr. No. | numeric | 0 (0.0%) |
| State | text | 1 (0.01%) |
| Work | text | 1 (0.01%) |
| Work ID | text | 1 (0.01%) |
| IDA | text | 1 (0.01%) |
| Hon'ble Members of Parliament | text | 1 (0.01%) |
| Constituency | text | 1 (0.01%) |
| Expenditure Date | date_text_dd_mmm_yyyy | 1 (0.01%) |
| Vendor Name | text | 1 (0.01%) |
| Payment Status | text | 1 (0.01%) |
| Fund Disbursed Amount ( ₹ ) | numeric | 0 (0.0%) |

### 6. LOK_SABHA — WORKS_COMPLETED

SHA-256: `4545f8f74dcc87438ba1fdd57307f2eacaef048bcf40f312dad04b941f88fb0b`. Source sequence (`Sr. No.`) unique: `True`.

| Observed source column | Inferred storage type | Nulls |
|---|---|---:|
| Sr. No. | numeric | 0 (0.0%) |
| Work Category | text | 1 (0.0%) |
| Work | text | 1 (0.0%) |
| State | text | 1 (0.0%) |
| IDA | text | 1 (0.0%) |
| Work Description | text | 1 (0.0%) |
| Hon'ble Members of Parliament | text | 1 (0.0%) |
| Constituency | text | 1 (0.0%) |
| Image | text | 1 (0.0%) |
| Completion Date | date_text_dd_mmm_yyyy | 1 (0.0%) |
| Amount Disbursed ( ₹ ) | numeric | 77 (0.23%) |

### 7. RAJYA_SABHA — ALLOCATED_LIMIT

SHA-256: `dabc86530660f949c2472cb1e014a03017953f19b36a4e1f23d3172bc7db3656`. Source sequence (`Sr. No.`) unique: `True`.

| Observed source column | Inferred storage type | Nulls |
|---|---|---:|
| Sr. No. | numeric | 0 (0.0%) |
| State | text | 1 (0.43%) |
| Hon'ble Members of Parliament | text | 1 (0.43%) |
| Elected/Nominated | text | 1 (0.43%) |
| Allocated AMOUNT ( ₹ ) | numeric | 0 (0.0%) |

### 8. RAJYA_SABHA — CALAMITY

SHA-256: `55e299ee4b2fda9188ef218f850062379962c71e58a23ac4e8bb3d0a5e37e5eb`. Source sequence (`Sr. No.`) unique: `True`.

| Observed source column | Inferred storage type | Nulls |
|---|---|---:|
| Sr. No. | text | 0 (0.0%) |
| Calamity Type | text | 1 (4.76%) |
| Calamity Name | text | 1 (4.76%) |
| Hon'ble Members of Parliament | text | 1 (4.76%) |
| Date of Consent | date_text_dd_mmm_yyyy | 1 (4.76%) |
| Consent Amount ( ₹ ) | numeric | 0 (0.0%) |

### 9. RAJYA_SABHA — WORKS_RECOMMENDED

SHA-256: `c0bb6cb17e882dc2ee04bedd62430515bf91a59bdac4185c941235dfddd71694`. Source sequence (`Sr. No.`) unique: `True`.

| Observed source column | Inferred storage type | Nulls |
|---|---|---:|
| Sr. No. | numeric | 0 (0.0%) |
| Work category | text | 1 (0.0%) |
| WORK | text | 1 (0.0%) |
| State | text | 1 (0.0%) |
| IDA | text | 1 (0.0%) |
| Hon'ble Members of Parliament | text | 1 (0.0%) |
| Elected/Nominated | text | 1 (0.0%) |
| Work description | text | 2 (0.01%) |
| Recommended date | date_text_dd_mmm_yyyy | 1 (0.0%) |
| RECOMMENDED AMOUNT   ( ₹ ) | numeric | 1 (0.0%) |
| Sanction Date | text | 0 (0.0%) |

### 10. RAJYA_SABHA — WORKS_SANCTIONED

SHA-256: `33b1b40be162f088fa20713e92950e4bdfbb047de79ba8d35a3b9ad2322376ef`. Source sequence (`Sr. No.`) unique: `True`.

| Observed source column | Inferred storage type | Nulls |
|---|---|---:|
| Sr. No. | numeric | 0 (0.0%) |
| Work category | text | 1 (0.01%) |
| Work | text | 1 (0.01%) |
| State | text | 1 (0.01%) |
| IDA | text | 1 (0.01%) |
| Hon'ble Members of Parliament | text | 1 (0.01%) |
| Elected/Nominated | text | 1 (0.01%) |
| Work description | text | 1 (0.01%) |
| Recommended date | date_text_dd_mmm_yyyy | 1 (0.01%) |
| Sanction Date | date_text_dd_mmm_yyyy | 1 (0.01%) |
| Sanction Amount ( ₹ ) | numeric | 1 (0.01%) |
| Work Status | text | 0 (0.0%) |

### 11. RAJYA_SABHA — EXPENDITURE

SHA-256: `9ca6f5d84a0171e70cd3e3634eb0c123b1a070a7cdfbc0e97d36bfff186601e0`. Source sequence (`Sr. No.`) unique: `True`.

| Observed source column | Inferred storage type | Nulls |
|---|---|---:|
| Sr. No. | numeric | 0 (0.0%) |
| State | text | 1 (0.0%) |
| Work | text | 1 (0.0%) |
| Work ID | text | 1 (0.0%) |
| IDA | text | 1 (0.0%) |
| Hon'ble Members of Parliament | text | 1 (0.0%) |
| Elected/Nominated | text | 1 (0.0%) |
| Expenditure Date | date_text_dd_mmm_yyyy | 1 (0.0%) |
| Vendor Name | text | 1 (0.0%) |
| Payment Status | text | 1 (0.0%) |
| Fund Disbursed Amount ( ₹ ) | numeric | 0 (0.0%) |

### 12. RAJYA_SABHA — WORKS_COMPLETED

SHA-256: `33a291e23b1c0fe469757177d06265750f4759fe861d0f0b81ae289093bdadd0`. Source sequence (`Sr. No.`) unique: `True`.

| Observed source column | Inferred storage type | Nulls |
|---|---|---:|
| Sr. No. | numeric | 0 (0.0%) |
| Work Category | text | 1 (0.01%) |
| Work | text | 1 (0.01%) |
| State | text | 1 (0.01%) |
| IDA | text | 1 (0.01%) |
| Work Description | text | 1 (0.01%) |
| Hon'ble Members of Parliament | text | 1 (0.01%) |
| Elected/Nominated | text | 1 (0.01%) |
| Image | text | 1 (0.01%) |
| Completion Date | date_text_dd_mmm_yyyy | 1 (0.01%) |
| Amount Disbursed ( ₹ ) | numeric | 18 (0.18%) |

## Work identity and House separation

Work IDs were parsed from the source `Work ID` column where present, otherwise from the observed `Work` label. The normalized source pattern is `WS/MP<number>/<financial-year>/<number>`, with incidental spaces removed before parsing. Across all work-bearing sources, the same normalized work ID appears in both Houses **0** times. Canonical identity must therefore remain `normalized_house + ':' + normalized_work_id`; no cross-House merge is permitted.

### Work-ID quality findings

- LOK_SABHA WORKS_RECOMMENDED: 25,442 source values do not yield a canonical work ID; 25,441 are `NA-` placeholders and 1 are blank. These rows remain source-auditable but cannot be joined to a canonical work without a separate resolved identity.
- LOK_SABHA WORKS_SANCTIONED: 1 source values do not yield a canonical work ID; 0 are `NA-` placeholders and 1 are blank. These rows remain source-auditable but cannot be joined to a canonical work without a separate resolved identity.
- LOK_SABHA EXPENDITURE: 1 source values do not yield a canonical work ID; 0 are `NA-` placeholders and 1 are blank. These rows remain source-auditable but cannot be joined to a canonical work without a separate resolved identity.
- LOK_SABHA WORKS_COMPLETED: 1 source values do not yield a canonical work ID; 0 are `NA-` placeholders and 1 are blank. These rows remain source-auditable but cannot be joined to a canonical work without a separate resolved identity.
- RAJYA_SABHA WORKS_RECOMMENDED: 3,333 source values do not yield a canonical work ID; 3,332 are `NA-` placeholders and 1 are blank. These rows remain source-auditable but cannot be joined to a canonical work without a separate resolved identity.
- RAJYA_SABHA WORKS_SANCTIONED: 1 source values do not yield a canonical work ID; 0 are `NA-` placeholders and 1 are blank. These rows remain source-auditable but cannot be joined to a canonical work without a separate resolved identity.
- RAJYA_SABHA EXPENDITURE: 1 source values do not yield a canonical work ID; 0 are `NA-` placeholders and 1 are blank. These rows remain source-auditable but cannot be joined to a canonical work without a separate resolved identity.
- RAJYA_SABHA WORKS_COMPLETED: 1 source values do not yield a canonical work ID; 0 are `NA-` placeholders and 1 are blank. These rows remain source-auditable but cannot be joined to a canonical work without a separate resolved identity.

## Audit decision

All twelve sources passed the source-audit gate. This permits schema mapping and a raw/staging ingestion implementation. It does not yet mean that a version is approved or active; promotion must wait for row-level validation and ingestion results.
