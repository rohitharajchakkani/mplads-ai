# API architecture

```text
HTTP request
  -> FastAPI route and request validation
  -> centralized active-release resolver
  -> analytical/entity service
  -> parameterized SQLAlchemy query over active dataset versions
  -> Pydantic response with provenance
```

Routes are intentionally thin. SQL and metric semantics remain in database, ingestion, entity, analytical, and versioning services. Each analytical endpoint resolves the active release through `resolve_active_scope`; no endpoint hardcodes a release identifier.

Database access is dependency-injected per request. Pagination, filtering, ordering, and aggregations execute in SQL. Work detail limits returned expenditure transactions to 100 and includes a truncation indicator while separately calculating full transaction count and total.

Development CORS is configured from `CORS_ORIGINS`; it defaults only to the local Vite origin. The API emits `X-Content-Type-Options`, `X-Frame-Options`, and `Referrer-Policy` headers. Protected monitoring endpoints and authentication are intentionally outside Phase 7.
