# Ask AI tool allowlist

Only handlers implemented in `backend/app/ai/tools.py` are registered:

- `get_dashboard_summary`
- `get_financial_by_state`
- `get_financial_by_house`
- `get_lifecycle_summary`
- `get_risk_summary`
- `get_monitoring_signal_detail`
- `get_alert_summary`
- `get_recommendations`
- `get_review_summary`
- `get_benchmark_result`
- `get_executive_summary`

Each registry entry declares its strict argument model, permitted roles, active-release and authorized-scope requirements, hard result maximum, supported entities and filters, and `read_only = true`. Unknown tools, filters, sort values, groups, limits, and write requests are rejected before a query executes.

Every handler returns a `ToolResult` containing only bounded verified data plus separate metadata: selected tool, result count, truncation state, validated filters, authorized scope, dataset version, generation time, warnings, and safe navigation links.
