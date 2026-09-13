# Filtering

`AnalyticsFilters` is shared by all analytical services. Supported canonical-work filters are House, State, district/IDA, MP, constituency, financial year extracted from a resolved Work ID, and exact source work status.

House accepts `LOK_SABHA` or `RAJYA_SABHA`; “both” is represented by an omitted House filter. All work metrics apply filters to the canonical work set before counting lifecycle records or payments.

Allocation and calamity have their own source grain. They support House, State, MP, and constituency when present. If a caller requests a non-source-supported filter such as district/IDA or financial year for either domain, the result is explicitly unavailable rather than silently applying an unrelated filter.

Sector and subsector filters are rejected as unavailable because no verified sector/subsector source field exists. This avoids inventing taxonomy or yielding misleading filtered totals.
