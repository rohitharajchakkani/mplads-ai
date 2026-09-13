# Human review workflow

Review cases are protected, persisted records created from an existing active-release alert or monitoring signal. A signal supports review; it is not a finding of wrongdoing.

Case statuses are exactly `OPEN`, `ASSIGNED`, `UNDER_REVIEW`, `FOLLOW_UP_REQUIRED`, `RESOLVED`, `CLOSED`, and `REOPENED`.

Allowed workflow transitions are `OPEN → ASSIGNED`, `ASSIGNED/REOPENED/FOLLOW_UP_REQUIRED → UNDER_REVIEW`, `UNDER_REVIEW → FOLLOW_UP_REQUIRED`, `UNDER_REVIEW → RESOLVED`, `RESOLVED → CLOSED`, and `CLOSED → REOPENED`. Reassignment changes the assignee and records `REASSIGNED`; it does not introduce a status.

Every creation and action appends an immutable event containing actor, timestamp, action, metadata, and optional comment. Writes require the current case version. A stale version receives HTTP 409 and cannot overwrite a more recent action.

Resolution types are administrative outcomes only: `INFORMATION_VERIFIED`, `NO_FURTHER_ACTION`, `CORRECTION_REQUIRED`, `FOLLOW_UP_COMPLETED`, and `REFERRED`.
