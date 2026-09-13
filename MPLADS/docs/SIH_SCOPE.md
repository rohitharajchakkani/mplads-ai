# SIH26102 Product Scope

MPLADS AI is focused on SIH26102: an AI-powered decision-support system for detecting anomalies, fraud-risk indicators, and inefficiencies in MPLAD Scheme implementation. It does not make legal findings or label a person, organisation, or work as guilty of fraud.

## Core required features

- Active-release anomaly detection and explainable risk indicators
- Fraud-risk and suspicious-pattern review signals, including potential duplicate candidates
- Inefficiency context from financial, lifecycle, and peer-comparison evidence
- Server-authorized Monitoring, alerts, and evidence drill-down
- Human review cases with immutable evidence snapshots and auditable actions
- Grounded Ask AI: planner, authorized backend tool, active-release result, optional Gemini explanation, visualization/table, provenance, and report
- Current-result reporting: Generate Report, Download CSV, and Print / Save PDF

## Supporting features

- Peer performance comparison for evidence-backed bottleneck context
- Recommendations that link source evidence to a possible review case
- Concise executive attention summary
- Public work records, search, and implementation context used to locate and understand records before protected investigation

## Public and protected boundary

Public pages provide active-release context only: Home, Dashboard, Works, Search, and Methodology. MPs, States, Districts, and Statistics remain available through direct drill-down/search routes where they help locate a work, but are no longer promoted in primary navigation.

Protected Monitoring is the investigation workspace: Monitoring Overview, Risk, Anomalies, Alerts, Potential Duplicates, Financial Monitoring, Lifecycle Monitoring, Reviews, Ask AI, Peer comparison, Recommendations, and Executive. The backend remains authoritative for all roles and scopes; hiding a control is never treated as authorization.

## Removed or hidden from the primary experience

- Primary links for MPs, States, Districts, and Statistics were hidden to avoid duplicating the Work and Search investigation flow. Their existing API-backed routes remain available for legitimate drill-down.
- Generic public-statistics emphasis was reduced. The public Dashboard now explains that protected monitoring is where risk, anomaly, alert, and review signals are available.
- No maps were added because the active release does not provide a defensible coordinate source for all relevant records.
- No new export formats, decorative dashboards, unrelated AI features, raw database access, static data, or fake records were introduced.

## Guardrails retained

- No datasets, canonical mappings, active release, database schema, or analytical calculations are changed by scope cleanup.
- No fake MPLADS values, monitoring records, AI answers, or reports are used.
- Forecasting, unsupported claims, SQL/filesystem requests, scope bypass attempts, and secret requests remain safely rejected by Ask AI.
- Every result keeps active-release provenance; every protected request is server-authorized.
