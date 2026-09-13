# Architecture

## Governing principle

All MPLADS values flow from an approved source dataset through raw preservation, staging, validation, normalization, canonical storage, analytical queries, versioned API responses, and the frontend. The system has no demo data path.

## Planned flow

```text
supplied source file
  -> immutable raw intake + checksum
  -> inspection / preview
  -> validation decision
  -> approved staging transformation
  -> normalized canonical entities
  -> active dataset version / analytical services
  -> /api/v1 responses
  -> public or authorized UI
```

## Version lifecycle

`DISCOVERED -> STAGED -> VALIDATED -> APPROVED -> PROMOTED`

Rejected or inconsistent source rows are retained in staging with a validation result and cannot be promoted into canonical records. Only one version of a logical dataset may become active at a time. The current intake is `VALIDATED`; it is not yet approved or promoted.

## Security boundary

Public routes expose only public aggregates and records. Monitoring, review, administration, and AI query tools require server-side authorization. AI receives only validated, authorized tool results and never database credentials, direct SQL, filesystem access, or unrestricted data.
