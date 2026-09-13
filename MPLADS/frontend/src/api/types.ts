export type Nullable<T> = T | null;

export interface Provenance {
  service: string;
  release_version: string;
  batch_id: string;
  filters: Record<string, Nullable<string>>;
  generated_at: string;
}

export interface AnalyticsResponse<T extends object = Record<string, unknown>> {
  data: T;
  provenance: Provenance;
}

export interface Pagination {
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface PaginatedResponse<T> {
  items: T[];
  pagination: Pagination;
  provenance: Provenance;
}

export interface Filters {
  house?: string;
  state?: string;
  district_or_ida?: string;
  mp?: string;
  work?: string;
  constituency?: string;
  financial_year?: string;
  work_status?: string;
}

export type OptionField = "house" | "state" | "district_or_ida" | "mp" | "work" | "financial_year" | "work_status";

export interface FilterOption {
  value: string;
  label: string;
  count: number;
}

export interface FilterOptionsData {
  field: OptionField | string;
  options: FilterOption[];
  query?: Nullable<string>;
  limited: boolean;
}

export type VisualizationChartType = "KPI" | "BAR" | "HORIZONTAL_BAR" | "LINE" | "AREA" | "PIE" | "DONUT" | "DISTRIBUTION" | "GROUPED_BAR" | "STACKED_BAR" | "HISTOGRAM" | "SCATTER" | "HEATMAP" | "TABLE";
export interface VisualizationSelection {
  rule: string;
  rationale: string;
  source: "active_release_aggregate" | "verified_tool_result" | string;
}
export interface VisualizationSpec {
  title: string;
  description: string;
  chart_type: VisualizationChartType;
  x_axis: Nullable<string>;
  y_axis: Nullable<string>;
  unit: Nullable<string>;
  series: Array<{ key: string; label: string }>;
  rows: Array<Record<string, string | number | null>>;
  record_count: number;
  selection?: VisualizationSelection;
  applied_filters?: Record<string, Nullable<string>>;
  data_available: boolean;
  message?: string;
}

export interface DashboardMetrics {
  total_canonical_works: number;
  monitored_works?: number;
  risk_signals_count?: number;
  alerts_count?: number;
  potential_duplicates_count?: number;
  open_reviews_count?: number;
  recommendations_count?: number;
  recommended_works: number;
  sanctioned_works: number;
  completed_works: number;
  total_sanction_amount: string;
  total_expenditure: string;
  mp_count: number;
  state_count: number;
  district_or_ida_count: number;
  allocation: string | Availability;
  calamity_amount: string | Availability;
  sector: Availability;
  physical_progress: Availability;
}

export interface Availability {
  available: boolean;
  message: string;
}

export interface StatusRow {
  source_status: Nullable<string>;
  normalized_status: null;
  work_count: number;
}

export interface StatusDistribution {
  rows: StatusRow[];
  normalization: string;
}

export interface GeographyRow {
  value: Nullable<string>;
  work_count: number;
  expenditure: string;
  sanction_amount: string;
  sanctioned_work_count: number;
}

export interface GeographySummary {
  dimension: string;
  rows: GeographyRow[];
  notes: string;
}

export interface TrendRow {
  period: string;
  record_count: number;
  amount?: string;
}

export interface Trend {
  data_available: boolean;
  message?: string;
  rows: TrendRow[];
}

export interface HouseRow {
  house: string;
  total_canonical_works: number;
  sanctioned_works: number;
  completed_works: number;
  total_sanction_amount: string;
  total_expenditure: string;
}

export interface MPListItem {
  mp_id: string;
  name: string;
  house: string;
  state: Nullable<string>;
  constituency: Nullable<string>;
  work_count: number;
}

export interface StateListItem {
  state_id: string;
  name: string;
  work_count: number;
}

export interface DistrictListItem {
  district_id: string;
  state: Nullable<string>;
  district_or_ida: string;
  work_count: number;
}

export interface WorkListItem {
  canonical_work_key: string;
  work_id: Nullable<string>;
  house: string;
  financial_year: Nullable<string>;
  mp: Nullable<string>;
  state: Nullable<string>;
  district_or_ida: Nullable<string>;
  constituency: Nullable<string>;
  work_description: Nullable<string>;
  source_work_category: Nullable<string>;
  sector: null;
  subsector: null;
}

export interface DetailData {
  name?: string;
  state?: Nullable<string>;
  house?: string;
  constituency?: Nullable<string>;
  district_or_ida?: string;
  metrics: DashboardMetrics;
  status_distribution: StatusDistribution;
  expenditure_trend: Trend;
}

export interface WorkTimelineRecord {
  date?: Nullable<string>;
  recommended_date?: Nullable<string>;
  sanction_date?: Nullable<string>;
  completion_date?: Nullable<string>;
  amount?: string;
  reported_disbursed_amount?: string;
  work_reference_status?: Nullable<string>;
  source_status?: Nullable<string>;
}

export interface WorkDetailData {
  work: WorkListItem;
  recommendations: WorkTimelineRecord[];
  sanctions: WorkTimelineRecord[];
  completions: WorkTimelineRecord[];
  expenditure: {
    total: string;
    transaction_count: number;
    first_expenditure_date: Nullable<string>;
    latest_expenditure_date: Nullable<string>;
    transactions: Array<{
      date: Nullable<string>;
      vendor_name: Nullable<string>;
      payment_status: Nullable<string>;
      amount: string;
    }>;
    transactions_truncated: boolean;
  };
  provenance: {
    release_version: string;
    batch_id: string;
    source_dataset_versions: string[];
  };
}

export interface FinancialSummary {
  total_expenditure: string;
  transaction_count: number;
  unmatched_expenditure_transactions: number;
}

export interface ExpenditureByDimension {
  dimension: string;
  rows: Array<{ value: Nullable<string>; expenditure: string; transaction_count: number }>;
}

export interface DataQualitySummary {
  unresolved_work_references: number;
  blank_work_references: number;
  orphan_expenditure_transactions: number;
  orphan_completed_records: number;
  missing_mp: number;
  missing_state: number;
  missing_district_or_ida: number;
  validation_warnings: number;
  rejected_canonical_records: number;
  physical_progress_available: false;
}

export interface ActiveDataset {
  release_version: string;
  status: string;
  promoted_at: string;
  datasets: Array<{
    dataset_type: string;
    house: string;
    status: string;
    source_filename: string;
    source_sheet: string;
    source_row_count: number;
    staged_row_count: number;
    valid_row_count: number;
    warning_row_count: number;
    rejected_row_count: number;
  }>;
}

export interface SearchItem {
  entity_type: "WORK" | "MP" | "STATE" | "DISTRICT_OR_IDA" | "CONSTITUENCY";
  identifier: string;
  label: Nullable<string>;
  title?: Nullable<string>;
  description?: Nullable<string>;
  house?: Nullable<string>;
  state?: Nullable<string>;
  district?: Nullable<string>;
  mp?: Nullable<string>;
  constituency?: Nullable<string>;
}

export type MonitoringRole = "MP" | "DISTRICT_AUTHORITY" | "STATE_NODAL_AUTHORITY" | "MINISTRY" | "PLATFORM_ADMINISTRATOR";

export interface ProtectedProvenance { dataset_version: string; generated_at: string; rules_version?: string | null; model_version?: string | null; }
export interface MonitoringPage<T> { items: T[]; pagination: Pagination; provenance: ProtectedProvenance; }
export interface RiskWork { work_key: string; house: string; state_name: Nullable<string>; district_or_ida: Nullable<string>; mp_source_name: Nullable<string>; raw_score: number; normalized_score: number; risk_band: string; component_scores: Record<string, number>; evidence: Record<string, unknown>; data_quality_context: Record<string, boolean>; provenance: ProtectedProvenance; }
export interface RiskSummary { total_assessments: number; risk_distribution: Record<string, number>; signals_by_category: Record<string, number>; alerts_by_severity: Record<string, number>; high_priority_works: number; provenance: ProtectedProvenance; }
export interface MonitoringAlert { alert_id: string; work_key: string; house: string; state_name?: Nullable<string>; district_or_ida?: Nullable<string>; mp_source_name?: Nullable<string>; category: string; severity: string; title: string; explanation: string; evidence: Record<string, unknown>; status: string; generated_at: string; provenance: ProtectedProvenance; }
export interface AlertSummary { total_alerts: number; by_category: Record<string, number>; by_severity: Record<string, number>; provenance: ProtectedProvenance; }
export interface DuplicateCandidate { candidate_id: string; work_a_key: string; work_b_key: string; similarity_score: number; review_priority: string; contextual_comparison: Record<string, unknown>; reason: string; generated_at: string; provenance: ProtectedProvenance; }
export interface AnomalySummary { total_ml_anomaly_signals: number; model_version: string; dataset_version: string; generated_at: string; }
export interface MonitoringCategorySummary { category: string; total_signals: number; by_severity: Record<string, number>; by_house: Record<string, number>; by_state: Record<string, number>; related_category_counts: Record<string, number>; financial_patterns?: Record<string, unknown> | null; observed_lifecycle?: Record<string, unknown> | null; provenance: ProtectedProvenance; }
export interface ReviewCase { case_id: string; source_alert_id: Nullable<string>; source_signal_id: Nullable<string>; canonical_work_key: Nullable<string>; house: Nullable<string>; state_name: Nullable<string>; district_or_ida: Nullable<string>; mp_source_name: Nullable<string>; status: string; priority: string; assignee: Nullable<string>; dataset_version: string; version: number; created_at: string; updated_at: string; closed_at: Nullable<string>; }
export interface ReviewEvent { event_id: string; actor: string; occurred_at: string; action: string; metadata: Record<string, unknown>; comment: Nullable<string>; }
export interface ReviewCaseDetail extends ReviewCase { evidence_snapshot_id: string; evidence_snapshot: Record<string, unknown>; evidence_hash: string; events: ReviewEvent[]; provenance: ProtectedProvenance; }
export interface ReviewSummary { by_status: Record<string, number>; active_escalations: number; provenance: ProtectedProvenance; }
export interface Notification { notification_id: string; case_id: string; event_id: string; recipient: string; state: string; message: string; created_at: string; }
export interface BenchmarkResult { result_id: string; entity_type: string; entity_id: string; house: string; state_name: Nullable<string>; district_or_ida: Nullable<string>; mp_source_name: Nullable<string>; metric: string; formula: string; metric_details?: Record<string, unknown> | null; value: Nullable<number>; peer_median: Nullable<number>; p25: Nullable<number>; p75: Nullable<number>; p90: Nullable<number>; iqr: Nullable<number>; peer_count: number; valid_work_count: number; benchmark_available: boolean; unavailable_reason: Nullable<string>; directionality: string; bottleneck_flag: boolean; interpretation: string; dataset_version: string; benchmark_version: string; provenance_hash: string; generated_at: string; }
export interface BenchmarkSummary { run_id: string; entity_count: number; result_count: number; by_metric: Record<string, number>; bottleneck_count: number; benchmark_version: string; dataset_version: string; generated_at: string; }
export interface BenchmarkPeers { result_id: string; cohort_definition: Record<string, unknown>; peer_ids: string[]; peer_count: number; provenance: ProtectedProvenance; }
export interface Recommendation { recommendation_id: string; canonical_work_key: Nullable<string>; entity_type: string; entity_id: string; house: Nullable<string>; state_name: Nullable<string>; district_or_ida: Nullable<string>; mp_source_name: Nullable<string>; recommendation_type: string; reason: string; evidence_references: Record<string, unknown>; priority: string; dataset_version: string; status: string; generated_at: string; updated_at: string; version: number; }
export interface ExecutiveSummary { total_monitored_works: number; total_signals: number; total_alerts: number; high_priority_alerts: number; high_priority_risk_works: number; review_backlog: Record<string, number>; active_escalations: number; available_benchmarks: number; benchmark_bottlenecks: number; active_recommendations: number; recommendations_by_priority: Record<string, number>; recommendations_by_status: Record<string, number>; provenance: ProtectedProvenance; }
export interface ExecutiveAttention { level: string; signal_count: number; drivers: Array<{ label: string; count: number; href: string }>; high_priority_categories: Record<string, number>; scope: Record<string, Nullable<string>>; provenance: ProtectedProvenance; }
export interface ExecutiveTrends { available: boolean; message: Nullable<string>; rows: Array<{ category: string; current_value: number; previous_value: Nullable<number>; absolute_change: Nullable<number>; percentage_change: Nullable<number> }>; provenance: ProtectedProvenance; }
export interface ExecutiveGeography { rows: Array<{ state: string; monitored_works: number; high_priority_risk_works: number; high_priority_risk_rate: Nullable<number> }>; material_concentration: boolean; message: Nullable<string>; provenance: ProtectedProvenance; }
export interface ExecutiveComparison { rows: Array<{ house: string; monitored_works: number; high_priority_risk_works: number; available_benchmarks: number }>; provenance: ProtectedProvenance; }
export interface ExecutiveDrilldown { summary: ExecutiveSummary; priority_queue: Array<{ alert_id: string; work_key: string; category: string; severity: string; title: string; generated_at: string; reason: string }>; links: Record<string, string>; provenance: ProtectedProvenance; }
export interface AskAiToolResult { tool_name: string; success: boolean; data: Record<string, unknown>; result_count: number; truncated: boolean; filters_applied: Record<string, string | number | null>; scope: Record<string, string | null>; dataset_version: string; generated_at: string; warnings: string[]; navigation_links: Array<{ label: string; href: string }>; }
export interface AskAiClarification { entity_type: string; label: string; filters: Record<string, string>; navigation_link?: { label: string; href: string }; }
export interface AskAiResponse { request_id: string; answer: string; intent: string; tool_results_summary: Record<string, unknown>; tool_result?: AskAiToolResult | null; visualization?: VisualizationSpec | null; grounding: { source_data: string; analytical_result: string; explanation: string }; provenance: { tool_used: string | null; filters_applied: Record<string, string | number | null>; authorized_scope: Record<string, string | null>; dataset_version: string }; dataset_version: Nullable<string>; generated_at: string; scope: Record<string, string | null>; warnings: string[]; navigation_links: Array<{ label: string; href: string }>; clarification_required?: boolean; clarification_options?: AskAiClarification[]; }

export interface AdminPage<T> { items: T[]; pagination: Pagination; }
export interface AccessRequest { request_id: string; name: string; designation: Nullable<string>; office: Nullable<string>; state_name: Nullable<string>; district_or_ida: Nullable<string>; reason: string; status: "PENDING" | "APPROVED" | "REJECTED"; created_at: string; decided_at: Nullable<string>; decided_by: Nullable<string>; decision_note: Nullable<string>; approved_user_id: Nullable<string>; }
export interface AuthorizedUser { user_id: string; display_name: string; designation: Nullable<string>; office: Nullable<string>; role: MonitoringRole; state_scope: Nullable<string>; district_scope: Nullable<string>; mp_scope: Nullable<string>; status: "ACTIVE" | "DISABLED" | "REVOKED"; source_access_request_id: Nullable<string>; version: number; created_at: string; updated_at: string; changed_by: string; disabled_at: Nullable<string>; }
export interface DatasetAsset { dataset_type: string; house: string; status: string; source_filename: string; source_sheet: string; source_checksum: string; source_row_count: number; staged_row_count: number; valid_row_count: number; warning_row_count: number; rejected_row_count: number; }
export interface AdminDatasetRelease { release_id: string; batch_id: string; release_version: string; status: string; approved_by: string; approved_at: string; validation_version: string; approval_notes: Nullable<string>; promoted_at: Nullable<string>; rolled_back_at: Nullable<string>; datasets: DatasetAsset[]; lifecycle_events: Array<{ event_type: string; actor: string; occurred_at: string; has_notes: boolean }>; }
export interface AdminDataQuality { dataset_version: string; generated_at: string; metrics: Record<string, number | boolean>; }
export interface QualityFinding { finding_id: number; dataset_version_id: number; source_row_number: number; severity: string; code: string; field_name: Nullable<string>; message: string; }
export interface AdminAuditLog { audit_id: string; source: string; event_type: string; entity_type: string; entity_id: string; actor: string; occurred_at: string; metadata: Record<string, unknown>; }
export interface AdminSystemStatus { api_status: string; database_status: string; active_dataset_status: string; active_release_version: Nullable<string>; migration_version: Nullable<string>; application_version: string; app_environment: string; cors_status: string; gemini_status: string; gemini_model: Nullable<string>; latest_analytics_run: Nullable<{ run_id: string; status: string; dataset_version: string; started_at: string; completed_at: Nullable<string> }>; checked_at: string; }
export interface SafeConfigurationStatus { database: string; gemini: string; cors: string; active_dataset: string; environment: string; migration: string; checked_at: string; }
