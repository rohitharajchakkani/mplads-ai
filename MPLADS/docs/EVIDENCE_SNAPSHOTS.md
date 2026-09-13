# Evidence snapshots

Creating a case performs one database transaction: validate the protected alert or signal, collect the release-specific analytical context, store a snapshot, create the case, and append `CREATED`.

The snapshot includes the source alert or signal, active-release risk assessment, related signals, relevant duplicate candidates, analytical run metadata, source dataset version, and capture timestamp. Its deterministic SHA-256 content hash is returned on case detail.

Snapshots are never updated by review actions or intelligence reruns. Historical cases therefore retain the exact analytical evidence available when the case was created, even after the active dataset changes.
