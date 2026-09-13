# Analytics methodology

## Status

Core backend analytical computations are active against the promoted release only. Metrics and filters are documented in [METRICS.md](METRICS.md) and [FILTERING.md](FILTERING.md). Risk, anomaly, duplicate-candidate, benchmarking, and AI features are not part of this phase.

## Non-negotiable conventions

- Work counts use distinct canonical works, never expenditure rows.
- Expenditure sums valid transaction values linked to canonical works.
- Missing values are not converted to zero without source-semantic evidence.
- A monitoring priority score is explainable evidence, not a fraud finding or ML prediction.
- Potential duplicates are candidates, not confirmed duplicates.
