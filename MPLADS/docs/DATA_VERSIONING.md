# Dataset versioning

## Lifecycle

`DISCOVERED -> STAGED -> VALIDATED -> APPROVED -> PROMOTED -> ACTIVE`

Terminal or historical states are `FAILED`, `ROLLED_BACK`, and `HISTORICAL`. Validation does not activate data. An approval service verifies the twelve-dataset manifest, House/domain assignment, source-to-staging reconciliation, checksums, canonicalization, and database integrity before creating an `APPROVED` release.

## Active pointer

`dataset_releases` is the authoritative release registry. A database partial unique index permits only one row with `status = ACTIVE`. All analytics call the centralized `resolve_active_scope` service, which resolves the active release and its twelve dataset versions. No analytical query reads unscoped canonical data.

## Promotion and rollback

Promotion runs in one transaction: the prior active release becomes `HISTORICAL`; the approved candidate becomes `ACTIVE`; version and batch statuses change together; lifecycle events record both changes. If the transaction fails, it rolls back before changing the active pointer.

Rollback never deletes a source, release, or audit event. It moves the current active release to `ROLLED_BACK` and atomically restores the most recent eligible `HISTORICAL` release. If no historical release exists, rollback fails safely and leaves the active release unchanged.

## Current release

The local development database has one active release created from the validated batch. See [generated/phase6_report.md](generated/phase6_report.md) for the database-derived current status.
