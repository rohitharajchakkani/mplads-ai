# Analytical architecture

## Query path

`ACTIVE release -> centralized scope resolver -> reusable analytical service -> SQL aggregation -> typed result with provenance`

The services are backend-only and do not serve a frontend in this phase.

- `dashboard_service`: core work/financial/domain metrics.
- `financial_analytics_service`: transaction-grain expenditure totals and dimensions.
- `geography_analytics_service`: state, district/IDA, MP and constituency summaries.
- `work_analytics_service`: preserved source-status and source-work-category distributions.
- `lifecycle_analytics_service`: observed lifecycle durations from valid source dates.
- `data_quality_service`: unresolved references, validation and completeness metrics.
- `integrity_service`: active-release database checks.

Every result contains the release version, batch ID, service name, generated timestamp, and applied filters. SQL performs ordinary counts and sums. Lifecycle percentiles retrieve only valid duration values after database filtering, then calculate quantiles without loading the work dataset itself.

`district_or_ida` retains the source `IDA` value. It is not asserted to be a conventional district. No physical-progress percentage is present in the source or calculated by the analytical layer.
