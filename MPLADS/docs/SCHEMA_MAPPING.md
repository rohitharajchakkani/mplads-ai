# Schema mapping

## Basis and rules

This mapping is based only on the observed header row 2 schemas in the twelve supplied files. Raw source values and original headers are retained alongside normalized values. `LOK_SABHA` and `RAJYA_SABHA` are injected from the verified intake manifest because no source workbook carries a dedicated House field.

All money fields are parsed to `decimal(18,2)` only when their raw value is a valid number. Dates are retained as raw text and parsed to `date` only when the observed `dd-MMM-yyyy` value is valid. Missing or invalid values remain null with a validation result; they never become zero.

| Dataset(s) | Source column | Canonical field | Type | Transformation | Validation |
|---|---|---|---|---|---|
| All 12 | Manifest assignment | `house` | enum | Inject verified `LOK_SABHA` or `RAJYA_SABHA` | Must match approved manifest record |
| All 12 | `Sr. No.` | `source_sequence` | text | Trim and preserve | Required and unique within source version |
| ALLOCATED_LIMIT | `State` | `state_name` | text | Trim; later reference-normalize | Required when source row is populated |
| ALLOCATED_LIMIT | `Hon'ble Members of Parliaments` (Lok) / `Hon'ble Members of Parliament` (Rajya) | `mp_source_name` | text | Preserve raw plus normalized comparison key | Required when source row is populated |
| LOK ALLOCATED_LIMIT | `Constituency` | `constituency_name` | text | Trim | Preserve null when missing |
| RAJYA ALLOCATED_LIMIT | `Elected/Nominated` | `membership_type` | text | Trim | Preserve null when missing |
| ALLOCATED_LIMIT | `Allocated AMOUNT ( ₹ )` | `allocated_amount` | decimal(18,2) | Parse numeric string | Reject malformed monetary value; do not coerce null to zero |
| CALAMITY | `Calamity Type` | `calamity_type` | text | Trim | Preserve null when missing |
| CALAMITY | `Calamity Name` | `calamity_name` | text | Trim | Preserve null when missing |
| CALAMITY | `Hon'ble Members of Parliament` | `mp_source_name` | text | Preserve raw plus normalized comparison key | Preserve null when missing |
| CALAMITY | `Date of Consent` | `consent_date` | date | Parse valid observed date text | Invalid/unparseable value becomes null with validation issue |
| CALAMITY | `Consent Amount ( ₹ )` | `consent_amount` | decimal(18,2) | Parse numeric string | Reject malformed monetary value |
| WORKS_RECOMMENDED / WORKS_SANCTIONED / WORKS_COMPLETED | `Work category` / `Work Category` | `work_category_source` | text | Trim | Preserve raw value |
| WORKS_RECOMMENDED | `WORK` | `work_source_label` | text | Trim and preserve | `NA-` labels are unresolved, not Work IDs |
| WORKS_SANCTIONED / WORKS_COMPLETED | `Work` | `work_source_label` | text | Trim and preserve | Extract Work ID only when observed pattern matches |
| EXPENDITURE | `Work` | `work_source_label` | text | Trim and preserve | Do not treat as a transaction identifier |
| EXPENDITURE | `Work ID` | `normalized_work_id` | text | Remove incidental spaces; extract `WS/MP<number>/<FY>/<number>` | Required to join a transaction; invalid/missing values are orphan candidates |
| WORKS_RECOMMENDED / WORKS_SANCTIONED / WORKS_COMPLETED | `WORK` / `Work` | `normalized_work_id` | text | Extract the same observed Work-ID pattern from the label | `NA-` or blank values are not canonicalized |
| Work-bearing sources | derived `house` + `normalized_work_id` | `canonical_work_key` | text | Concatenate as `HOUSE:WORK_ID` | Never merge same Work ID across Houses |
| Work-bearing sources | `State` | `state_name` | text | Trim; later reference-normalize | Preserve null when missing |
| Work-bearing sources | `IDA` | `district_or_ida` | text | Preserve full source value | Do not assert it is a conventional district |
| Work-bearing sources | `Hon'ble Members of Parliament` | `mp_source_name` | text | Preserve raw plus normalized comparison key | Preserve null when missing |
| Lok work-bearing sources | `Constituency` | `constituency_name` | text | Trim | Preserve null when missing |
| Rajya work-bearing sources | `Elected/Nominated` | `membership_type` | text | Trim | Preserve null when missing |
| WORKS_RECOMMENDED / WORKS_SANCTIONED / WORKS_COMPLETED | `Work description` / `Work Description` | `work_description` | text | Preserve text; create normalized text only for matching | Preserve null; never manufacture a description |
| WORKS_RECOMMENDED / WORKS_SANCTIONED | `Recommended date` | `recommended_date` | date | Parse valid observed date text | Invalid/unparseable value is a validation issue |
| WORKS_RECOMMENDED | `RECOMMENDED AMOUNT   ( ₹ )` | `recommended_amount` | decimal(18,2) | Parse numeric string | Reject malformed monetary value |
| WORKS_RECOMMENDED / WORKS_SANCTIONED | `Sanction Date` | `sanction_date` | date | Preserve raw, then parse only valid date text | Recommended-source values require row-level parsing due mixed text |
| WORKS_SANCTIONED | `Sanction Amount ( ₹ )` | `sanction_amount` | decimal(18,2) | Parse numeric string | Reject malformed monetary value |
| WORKS_SANCTIONED | `Work Status` | `work_status_source` | text | Trim and preserve | Preserve source vocabulary; no invented status mapping |
| EXPENDITURE | `Expenditure Date` | `expenditure_date` | date | Parse valid observed date text | Invalid/unparseable value is a validation issue |
| EXPENDITURE | `Vendor Name` | `vendor_name` | text | Trim and preserve | Preserve null when missing |
| EXPENDITURE | `Payment Status` | `payment_status_source` | text | Trim and preserve | Preserve source vocabulary |
| EXPENDITURE | `Fund Disbursed Amount ( ₹ )` | `disbursed_amount` | decimal(18,2) | Parse numeric string | Required for a valid expenditure transaction; never treat row count as work count |
| WORKS_COMPLETED | `Image` | `image_availability_source` | text | Preserve source marker | Do not infer a URL or geographic coordinate |
| WORKS_COMPLETED | `Completion Date` | `completion_date` | date | Parse valid observed date text | Invalid/unparseable value is a validation issue |
| WORKS_COMPLETED | `Amount Disbursed ( ₹ )` | `completed_reported_disbursed_amount` | decimal(18,2) | Parse numeric string | Keep distinct from transaction expenditure until reconciliation proves equivalence |

## Mapping decision

The mapping is approved for raw/staging implementation, not for silent data promotion. Row-level validation must report unresolved Work IDs, malformed amounts and dates, and reference integrity before a version can become active.
