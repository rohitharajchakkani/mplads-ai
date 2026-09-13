# Recommendation workflow

Recommendation statuses are `NOTED`, `UNDER_REVIEW`, `ACTION_INITIATED`, and `RESOLVED`. A resolved recommendation may return to `UNDER_REVIEW`; recommendations cannot return to `NOTED` after action has begun.

Status changes require the current optimistic-lock version, produce an append-only recommendation event, and return HTTP 409 on a stale version. An authorized actor can create a human review case only when the recommendation has a linked active-release signal or alert; it never creates a case automatically.

Recommendation reads, status updates, and review-case creation use the same server-side role/scope checks as protected monitoring and review APIs.
