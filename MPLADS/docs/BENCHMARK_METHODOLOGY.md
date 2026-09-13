# Benchmark methodology

The benchmark version is `benchmark-v2`. Cohorts are MP entities in the same House; the focal MP is excluded from its peer statistics.

- **Observed Sanction Latency** is the MP-level median number of calendar days from source recommendation date to source sanction date, using only linked works with both valid dates. Larger values can indicate a longer-than-peer observed duration; no policy deadline is inferred.
- **Completion Ratio** is the count of linked completed works divided by the count of works with a linked sanction record. Lower values can be flagged only as lower-than-peer contextual evidence.
- **Expenditure Pacing Ratio** is total linked expenditure divided by total linked sanction amount, limited to works having both record types and a positive sanction total. It is an observed source-record ratio, not a target or expected spend schedule.

Peer statistics are median, P25, P75, P90, and IQR. For sanction latency, a potential bottleneck is `value > P90` or `value > P75 + 1.5 × IQR`. For lower-is-concern ratios, it is `value < P25 - 1.5 × IQR`. A benchmark is contextual evidence, not an assessment of a person or a finding of wrongdoing.
