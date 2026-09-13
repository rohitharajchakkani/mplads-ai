# API provenance

The active release resolver is the sole source of analytical dataset scope. Responses include:

- `release_version`
- `batch_id`
- `service`
- `generated_at`
- exact applied filters

Work identity is always `canonical_work_key`, derived as `house:normalized_work_id`. Work detail records provide linked lifecycle and expenditure data only where the source-supported canonical relation exists. Expenditure totals sum valid transaction records; allocation and calamity remain in their own source domains.

The API does not read audit markdown or source spreadsheets to form results. It queries the promoted database release and returns unavailable indicators where source fields do not support the requested analysis.
