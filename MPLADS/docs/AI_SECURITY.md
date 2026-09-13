# Ask AI security controls

- The endpoint requires an intelligence role and applies that role's server-side scope to every tool query.
- Tools are an explicit, read-only allowlist. There are no mutation tools for reviews, alerts, recommendations, datasets, users, or notifications.
- Request models, query plans, page context, and tool arguments reject unknown fields and invalid values.
- Page context is decoded only from known public identifiers and is verified against the caller's authorized data.
- Natural-language text cannot broaden page context or authorization.
- Tool outputs are bounded, and Gemini receives a minimal verified result rather than files, tables, SQL, database credentials, or raw datasets.
- Prompt-injection keyword screening is supplementary. The real boundary is plan validation, authorization, the tool allowlist, argument validation, and bounded execution.
- Audit records retain a question hash and length, not the raw question or answer. They contain no credentials.

The Gemini key remains backend-only in the ignored `backend/.env` configuration path; it is never returned by this API or delivered to the frontend.

Tests use a disposable SQLite backup, so test audit events cannot pollute durable development audit records.
