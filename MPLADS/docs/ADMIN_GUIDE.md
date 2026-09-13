# Administration guide

The Administration section is separate from Public and Monitoring. Every administration API is checked by the server for the Platform Administrator role. The browser’s selected development profile is not an authorization grant.

## Access requests

`/admin/access-requests` lists persisted requests only. Filter by status, applicant text, state, district/IDA, and created date. When approving, choose a role and the exact matching scope; the request itself never supplies a privileged role. Approval and rejection require explicit confirmation and write an audit event.

## Users and roles

`/admin/users` shows only authorized-user records created after approval. Use Manage to change a role/scope after checking the confirmation box, or disable/revoke an active account after supplying a reason. House is not a role. National and platform roles have no narrower monitoring scope.

## Dataset versions

`/admin/datasets` displays actual release metadata, source filenames, checksums, counts, validation status, and lifecycle events. Promote and rollback are confirmation-gated and use the existing lifecycle service. Do not manually alter release status or activate a second release.

## Data quality

`/admin/data-quality` provides active-release completeness and validation metrics plus paginated, safe finding metadata. These are data-quality signals, not fraud determinations. Raw source rows are not available in the browser.

## Audit and system state

`/admin/audit-logs` is an append-only, paginated view of safe operational events. It cannot be edited through the Admin API. `/admin/system` exposes health, active release, migration revision, environment mode, and safe configuration state. It never exposes API keys, database URLs, `.env` contents, or provider credentials.

## Empty pages are valid

The administration UI does not create sample users, requests, versions, audit events, quality metrics, or health data. An empty result accurately means there are no matching persisted records.
