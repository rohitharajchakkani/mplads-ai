# Data provenance

Every staging row retains the immutable source dataset identity, intake-derived House, source filename and sheet, original worksheet row number, dataset checksum, ingestion batch, dataset version, raw source values, normalized candidates, validation status, and findings.

Every active analytical result provides its release version, batch ID, service name, timestamp, and filters. Canonical work identity is `house:normalized_work_id`; same-looking Work IDs in different Houses can never merge. Lifecycle and payment records retain their source dataset-version link. Allocation and calamity remain separate analytical domains.

Unresolved `NA-…` references and blank work references are retained in staging with their source provenance. They are not assigned generated IDs, linked by text similarity, or discarded.
