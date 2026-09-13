# Executive intelligence

The protected executive layer summarizes active-release monitoring, review, benchmarking, and recommendation records. It is decision support, not a performance score, finding, or accusation.

It is available only through `/monitoring/executive` and protected `/api/v1/executive/*` endpoints. Server-side role and geographic scope rules are applied before aggregation. The executive page links to the existing detailed monitoring pages rather than creating separate copies of alerts, cases, or benchmark results.

The priority queue contains persisted analytical alerts ordered by severity and then generated timestamp. Its displayed reason states that ordering rule.
