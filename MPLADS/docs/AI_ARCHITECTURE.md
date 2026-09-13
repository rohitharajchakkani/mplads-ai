# Ask AI architecture

Ask AI is a protected, read-only monitoring feature. Its flow is:

```text
Question → controlled intent → validated AiQueryPlan → server authorization
→ allowlisted tool → persisted MPLADS evidence → normalized ToolResult
→ Gemini explanation
```

`backend/app/ai/planner.py` creates a strict Pydantic `AiQueryPlan`; it does not generate SQL and cannot name a database table. `backend/app/ai/registry.py` is the formal allowlist, and `backend/app/ai/tools.py` contains the corresponding registered handlers. `backend/app/ai/assistant.py` orchestrates those components and calls Gemini only after a successful normalized result exists.

The frontend calls only `POST /api/v1/ai/ask` through `api.askAi`. It displays structured backend data separately from the non-authoritative explanation.

The pytest suite makes a temporary SQLite backup before application modules create database sessions. Test writes, including Ask AI audit rows and review-workflow checks, occur only in that disposable database. The configured development database is not a test target; its real audit rows are preserved.
