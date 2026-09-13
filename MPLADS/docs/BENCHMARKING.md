# Peer benchmarking

Protected peer benchmarks are persisted against the active dataset release and current benchmark configuration. Phase 12 implements MP-level comparisons only, because the source contains enough MP entities for a same-House cohort. Lok Sabha and Rajya Sabha records are never combined.

A result is available only when the focal MP has at least 10 valid works for the metric and at least five other same-House peer MPs satisfy that same valid-work threshold. Otherwise the result explicitly says: `Benchmark unavailable: insufficient comparable data.`

Results retain run, benchmark version, dataset version, formula, peer counts, robust statistics, peer IDs, per-entity calculation details, and a deterministic provenance hash. Completion results retain their completed-work numerator and sanctioned-work denominator; latency results retain the observed mean, minimum, and maximum alongside the median; pacing results retain matched-work count and source totals. The frontend only renders those persisted records.
