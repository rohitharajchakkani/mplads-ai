# Monitoring-priority methodology

The score is a monitoring-priority measure, not a probability of fraud, corruption, guilt, or legal risk. Components are capped independently: Financial 25, Payment 20, Lifecycle 15, Duplicate candidate 20, and ML anomaly 15. `normalized_score = raw_score / 95 * 100`; bands are Low <30, Medium <60, High <80, and Very High >=80.

Configured deterministic thresholds are versioned in `app.intelligence.engine.CONFIG`: expenditure/sanction >1.0; payment concentration >=80%; transaction-count peer p95; at least five payments within 30 observed days; and state-peer lifecycle p90 with at least 20 observations. They are analytical comparison thresholds, not policy deadlines. Data-quality gaps are stored separately as interpretation context and contribute no points.
