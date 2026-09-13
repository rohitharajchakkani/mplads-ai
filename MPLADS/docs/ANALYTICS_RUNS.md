# Analytics runs and protected access

Each explicit run persists STARTED, COMPLETED, or FAILED status; active dataset release and batch; rules, feature, model, and duplicate-engine versions; timestamps; record and signal counts; and alert count. Historical signals and alerts are not overwritten.

Protected endpoints require `X-MPLADS-Role`. Planned roles are MP (requires MP scope), District Authority (District / IDA scope), State Nodal Authority (State scope), Ministry, and Platform Administrator. Scope filtering is applied server-side; public endpoints have no intelligence dependency.
