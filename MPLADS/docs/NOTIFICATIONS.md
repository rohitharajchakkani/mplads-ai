# In-app notifications

Notifications are internal records, not email or SMS. Assignment, reassignment, follow-up, resolution, and reopening actions may create recipient notifications from their immutable case event. The `(event_id, recipient)` unique constraint makes generation idempotent.

States are `UNREAD`, `READ`, `ACKNOWLEDGED`, and `EXPIRED`. The current API exposes the authorized actor's notifications and permits only that recipient to mark a notification read or acknowledged. Notification history is retained.
