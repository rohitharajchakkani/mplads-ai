import type {
  ActiveDataset, AnalyticsResponse, DataQualitySummary, DetailData, ExpenditureByDimension,
  Filters, FinancialSummary, GeographySummary, HouseRow, MPListItem, PaginatedResponse,
  SearchItem, StateListItem, DistrictListItem, StatusDistribution, Trend, WorkDetailData,
  WorkListItem, DashboardMetrics, AlertSummary, AnomalySummary, DuplicateCandidate, MonitoringAlert,
  MonitoringCategorySummary, MonitoringPage, MonitoringRole, RiskSummary, RiskWork, Notification,
  ReviewCase, ReviewCaseDetail, ReviewSummary, BenchmarkResult, BenchmarkSummary, BenchmarkPeers, Recommendation, ExecutiveSummary, ExecutiveAttention, ExecutiveTrends, ExecutiveGeography, ExecutiveComparison, ExecutiveDrilldown, AskAiResponse, FilterOptionsData, VisualizationSpec, OptionField,
} from "./types";

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api/v1").replace(/\/$/, "");

export class ApiError extends Error {
  constructor(
    message: string,
    public readonly status?: number,
    public readonly code?: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

export type Query = Record<string, string | number | boolean | undefined | null>;

export interface MonitoringCredentials { role: MonitoringRole; actor?: string; stateScope?: string; districtScope?: string; mpScope?: string; }
let monitoringCredentials: MonitoringCredentials | undefined;
export function setMonitoringCredentials(credentials: MonitoringCredentials | undefined) { monitoringCredentials = credentials; }

function requiresMonitoringAuthorization(path: string): boolean {
  return ["risk", "alerts", "duplicates", "anomalies", "monitoring", "reviews", "notifications", "benchmarking", "recommendations", "executive", "admin"]
    .some((segment) => path === segment || path.startsWith(`${segment}/`));
}

function endpoint(path: string, query?: Query): string {
  const url = new URL(`${API_BASE_URL}/${path.replace(/^\//, "")}`);
  for (const [key, value] of Object.entries(query ?? {})) {
    if (value !== undefined && value !== null && value !== "") url.searchParams.set(key, String(value));
  }
  return url.toString();
}

async function get<T>(path: string, query?: Query, signal?: AbortSignal): Promise<T> {
  const headers: Record<string, string> = { Accept: "application/json" };
  if (monitoringCredentials && requiresMonitoringAuthorization(path)) {
    headers["X-MPLADS-Role"] = monitoringCredentials.role;
    if (monitoringCredentials.stateScope) headers["X-MPLADS-State-Scope"] = monitoringCredentials.stateScope;
    if (monitoringCredentials.districtScope) headers["X-MPLADS-District-Scope"] = monitoringCredentials.districtScope;
    if (monitoringCredentials.mpScope) headers["X-MPLADS-MP-Scope"] = monitoringCredentials.mpScope;
    if (monitoringCredentials.actor) headers["X-MPLADS-Actor"] = monitoringCredentials.actor;
  }
  const response = await fetch(endpoint(path, query), {
    signal,
    headers,
  });
  if (!response.ok) {
    const body = await response.json().catch(() => undefined) as { detail?: { code?: string; message?: string } } | undefined;
    throw new ApiError(body?.detail?.message ?? `Unable to load data (HTTP ${response.status}).`, response.status, body?.detail?.code);
  }
  return response.json() as Promise<T>;
}

async function post<T>(path: string, body: object, signal?: AbortSignal): Promise<T> {
  const headers: Record<string, string> = { Accept: "application/json", "Content-Type": "application/json" };
  if (monitoringCredentials) {
    headers["X-MPLADS-Role"] = monitoringCredentials.role;
    if (monitoringCredentials.stateScope) headers["X-MPLADS-State-Scope"] = monitoringCredentials.stateScope;
    if (monitoringCredentials.districtScope) headers["X-MPLADS-District-Scope"] = monitoringCredentials.districtScope;
    if (monitoringCredentials.mpScope) headers["X-MPLADS-MP-Scope"] = monitoringCredentials.mpScope;
    if (monitoringCredentials.actor) headers["X-MPLADS-Actor"] = monitoringCredentials.actor;
  }
  const response = await fetch(endpoint(path), { method: "POST", signal, headers, body: JSON.stringify(body) });
  if (!response.ok) {
    const payload = await response.json().catch(() => undefined) as { detail?: { code?: string; message?: string } } | undefined;
    throw new ApiError(payload?.detail?.message ?? `Unable to update data (HTTP ${response.status}).`, response.status, payload?.detail?.code);
  }
  return response.json() as Promise<T>;
}

async function patch<T>(path: string, body: object, signal?: AbortSignal): Promise<T> {
  const headers: Record<string, string> = { Accept: "application/json", "Content-Type": "application/json" };
  if (monitoringCredentials) {
    headers["X-MPLADS-Role"] = monitoringCredentials.role;
    if (monitoringCredentials.stateScope) headers["X-MPLADS-State-Scope"] = monitoringCredentials.stateScope;
    if (monitoringCredentials.districtScope) headers["X-MPLADS-District-Scope"] = monitoringCredentials.districtScope;
    if (monitoringCredentials.mpScope) headers["X-MPLADS-MP-Scope"] = monitoringCredentials.mpScope;
    if (monitoringCredentials.actor) headers["X-MPLADS-Actor"] = monitoringCredentials.actor;
  }
  const response = await fetch(endpoint(path), { method: "PATCH", signal, headers, body: JSON.stringify(body) });
  if (!response.ok) {
    const payload = await response.json().catch(() => undefined) as { detail?: { code?: string; message?: string } } | undefined;
    throw new ApiError(payload?.detail?.message ?? `Unable to update data (HTTP ${response.status}).`, response.status, payload?.detail?.code);
  }
  return response.json() as Promise<T>;
}

const asQuery = (filters: Filters): Query => ({ ...filters });

export const api = {
  dashboardSummary: (filters: Filters = {}, signal?: AbortSignal) => get<AnalyticsResponse<DashboardMetrics>>("dashboard/summary", asQuery(filters), signal),
  workStatus: (filters: Filters = {}, signal?: AbortSignal) => get<AnalyticsResponse<StatusDistribution>>("dashboard/work-status", asQuery(filters), signal),
  houseComparison: (filters: Filters = {}, signal?: AbortSignal) => get<AnalyticsResponse<{ rows: HouseRow[] }>>("dashboard/house-comparison", asQuery(filters), signal),
  stateSummary: (filters: Filters = {}, signal?: AbortSignal) => get<AnalyticsResponse<GeographySummary>>("dashboard/state-summary", asQuery(filters), signal),
  expenditureTrend: (filters: Filters = {}, signal?: AbortSignal) => get<AnalyticsResponse<Trend>>("dashboard/expenditure-trend", asQuery(filters), signal),
  completionTrend: (filters: Filters = {}, signal?: AbortSignal) => get<AnalyticsResponse<Trend>>("dashboard/completion-summary", asQuery(filters), signal),
  filterOptions: (field: OptionField | string, filters: Filters = {}, query?: string, signal?: AbortSignal) => get<AnalyticsResponse<FilterOptionsData>>("filters/options", { field, query, limit: 50, ...asQuery(filters) }, signal),
  exploreVisualization: (metric: string, groupBy: string, filters: Filters = {}, signal?: AbortSignal) => get<AnalyticsResponse<VisualizationSpec>>("visualizations/explore", { metric, group_by: groupBy, ...asQuery(filters) }, signal),
  listMps: (query: Filters & { search?: string; page?: number; page_size?: number; sort?: string } = {}, signal?: AbortSignal) => get<PaginatedResponse<MPListItem>>("mps", { ...query }, signal),
  mp: (id: string, signal?: AbortSignal) => get<AnalyticsResponse<DetailData>>("mps/" + encodeURIComponent(id), undefined, signal),
  listStates: (query: Filters & { page?: number; page_size?: number } = {}, signal?: AbortSignal) => get<PaginatedResponse<StateListItem>>("states", { ...query }, signal),
  state: (id: string, signal?: AbortSignal) => get<AnalyticsResponse<DetailData>>("states/" + encodeURIComponent(id), undefined, signal),
  listDistricts: (query: Filters & { page?: number; page_size?: number } = {}, signal?: AbortSignal) => get<PaginatedResponse<DistrictListItem>>("districts", { ...query }, signal),
  district: (id: string, signal?: AbortSignal) => get<AnalyticsResponse<DetailData>>("districts/" + encodeURIComponent(id), undefined, signal),
  listWorks: (query: Filters & { search?: string; page?: number; page_size?: number; sort?: string } = {}, signal?: AbortSignal) => get<PaginatedResponse<WorkListItem>>("works", { ...query }, signal),
  work: (key: string, signal?: AbortSignal) => get<AnalyticsResponse<WorkDetailData>>("works/" + encodeURIComponent(key), undefined, signal),
  financialSummary: (filters: Filters = {}, signal?: AbortSignal) => get<AnalyticsResponse<FinancialSummary>>("financial/summary", asQuery(filters), signal),
  financialByHouse: (filters: Filters = {}, signal?: AbortSignal) => get<AnalyticsResponse<ExpenditureByDimension>>("financial/by-house", asQuery(filters), signal),
  financialByState: (filters: Filters = {}, signal?: AbortSignal) => get<AnalyticsResponse<ExpenditureByDimension>>("financial/by-state", asQuery(filters), signal),
  quality: (filters: Pick<Filters, "house"> = {}, signal?: AbortSignal) => get<AnalyticsResponse<DataQualitySummary>>("data-quality/summary", asQuery(filters), signal),
  activeDataset: (signal?: AbortSignal) => get<AnalyticsResponse<ActiveDataset>>("datasets/active", undefined, signal),
  search: (q: string, page = 1, pageSize = 20, signal?: AbortSignal) => get<PaginatedResponse<SearchItem>>("search", { q, page, page_size: pageSize }, signal),
  riskSummary: (signal?: AbortSignal) => get<RiskSummary>("risk/summary", undefined, signal),
  riskWorks: (query: Query = {}, signal?: AbortSignal) => get<MonitoringPage<RiskWork>>("risk/works", { page: 1, page_size: 25, ...query }, signal),
  riskWork: (key: string, signal?: AbortSignal) => get<RiskWork>("risk/works/" + encodeURIComponent(key), undefined, signal),
  alertSummary: (signal?: AbortSignal) => get<AlertSummary>("alerts/summary", undefined, signal),
  alerts: (query: Query = {}, signal?: AbortSignal) => get<MonitoringPage<MonitoringAlert>>("alerts", { page: 1, page_size: 25, ...query }, signal),
  alert: (id: string, signal?: AbortSignal) => get<MonitoringAlert>("alerts/" + encodeURIComponent(id), undefined, signal),
  duplicates: (query: Query = {}, signal?: AbortSignal) => get<MonitoringPage<DuplicateCandidate>>("duplicates/candidates", { page: 1, page_size: 25, ...query }, signal),
  anomalySummary: (signal?: AbortSignal) => get<AnomalySummary>("anomalies/summary", undefined, signal),
  financialMonitoring: (signal?: AbortSignal) => get<MonitoringCategorySummary>("monitoring/financial", undefined, signal),
  lifecycleMonitoring: (signal?: AbortSignal) => get<MonitoringCategorySummary>("monitoring/lifecycle", undefined, signal),
  reviewSummary: (signal?: AbortSignal) => get<ReviewSummary>("reviews/summary", undefined, signal),
  reviewCases: (query: Query = {}, signal?: AbortSignal) => get<MonitoringPage<ReviewCase>>("reviews/cases", { page: 1, page_size: 25, ...query }, signal),
  reviewCase: (id: string, signal?: AbortSignal) => get<ReviewCaseDetail>("reviews/cases/" + encodeURIComponent(id), undefined, signal),
  createReviewCase: (source: { alert_id?: string; signal_id?: string }, signal?: AbortSignal) => post<ReviewCase>("reviews/cases", source, signal),
  reviewAction: (id: string, action: string, payload: object, signal?: AbortSignal) => post<ReviewCase>(`reviews/cases/${encodeURIComponent(id)}/${action}`, payload, signal),
  notifications: (signal?: AbortSignal) => get<Notification[]>("notifications", undefined, signal),
  notificationAction: (id: string, action: "read" | "acknowledge", signal?: AbortSignal) => post<Notification>(`notifications/${encodeURIComponent(id)}/${action}`, {}, signal),
  benchmarkSummary: (signal?: AbortSignal) => get<BenchmarkSummary>("benchmarking/summary", undefined, signal),
  benchmarkResults: (query: Query = {}, signal?: AbortSignal) => get<MonitoringPage<BenchmarkResult>>("benchmarking/results", { page: 1, page_size: 25, ...query }, signal),
  benchmarkPeers: (resultId: string, signal?: AbortSignal) => get<BenchmarkPeers>("benchmarking/peers", { result_id: resultId }, signal),
  recommendations: (query: Query = {}, signal?: AbortSignal) => get<MonitoringPage<Recommendation>>("recommendations", { page: 1, page_size: 25, ...query }, signal),
  recommendationStatus: (id: string, status: string, version: number, signal?: AbortSignal) => post<Recommendation>(`recommendations/${encodeURIComponent(id)}/status`, { status, version }, signal),
  recommendationReviewCase: (id: string, signal?: AbortSignal) => post<ReviewCase>(`recommendations/${encodeURIComponent(id)}/review-case`, {}, signal),
  executiveSummary: (signal?: AbortSignal) => get<ExecutiveSummary>("executive/summary", undefined, signal),
  executiveAttention: (query: Query = {}, signal?: AbortSignal) => get<ExecutiveAttention>("executive/attention", query, signal),
  executiveTrends: (signal?: AbortSignal) => get<ExecutiveTrends>("executive/trends", undefined, signal),
  executiveGeography: (signal?: AbortSignal) => get<ExecutiveGeography>("executive/geography", undefined, signal),
  executiveComparison: (signal?: AbortSignal) => get<ExecutiveComparison>("executive/comparison", undefined, signal),
  executiveDrilldown: (query: Query = {}, signal?: AbortSignal) => get<ExecutiveDrilldown>("executive/drilldown", query, signal),
  askAi: (question: string, context: Record<string, string> = {}, signal?: AbortSignal) => post<AskAiResponse>("ai/ask", { question, context }, signal),
  adminAccessRequests: (query: Query = {}, signal?: AbortSignal) => get<import("./types").AdminPage<import("./types").AccessRequest>>("admin/access-requests", { page: 1, page_size: 25, ...query }, signal),
  adminApproveAccessRequest: (id: string, body: object, signal?: AbortSignal) => post<import("./types").AuthorizedUser>(`admin/access-requests/${encodeURIComponent(id)}/approve`, body, signal),
  adminRejectAccessRequest: (id: string, body: object, signal?: AbortSignal) => post<import("./types").AccessRequest>(`admin/access-requests/${encodeURIComponent(id)}/reject`, body, signal),
  adminUsers: (query: Query = {}, signal?: AbortSignal) => get<import("./types").AdminPage<import("./types").AuthorizedUser>>("admin/users", { page: 1, page_size: 25, ...query }, signal),
  adminUpdateUser: (id: string, body: object, signal?: AbortSignal) => patch<import("./types").AuthorizedUser>(`admin/users/${encodeURIComponent(id)}`, body, signal),
  adminDisableUser: (id: string, body: object, signal?: AbortSignal) => post<import("./types").AuthorizedUser>(`admin/users/${encodeURIComponent(id)}/disable`, body, signal),
  adminRevokeUser: (id: string, body: object, signal?: AbortSignal) => post<import("./types").AuthorizedUser>(`admin/users/${encodeURIComponent(id)}/revoke`, body, signal),
  adminDatasetVersions: (query: Query = {}, signal?: AbortSignal) => get<import("./types").AdminPage<import("./types").AdminDatasetRelease>>("admin/datasets/versions", { page: 1, page_size: 25, ...query }, signal),
  adminActiveDataset: (signal?: AbortSignal) => get<import("./types").AdminDatasetRelease>("admin/datasets/active", undefined, signal),
  adminPromoteDataset: (id: string, body: object, signal?: AbortSignal) => post<import("./types").AdminDatasetRelease>(`admin/datasets/releases/${encodeURIComponent(id)}/promote`, body, signal),
  adminRollbackDataset: (body: object, signal?: AbortSignal) => post<import("./types").AdminDatasetRelease>("admin/datasets/rollback", body, signal),
  adminDataQuality: (signal?: AbortSignal) => get<import("./types").AdminDataQuality>("admin/data-quality", undefined, signal),
  adminQualityFindings: (query: Query = {}, signal?: AbortSignal) => get<import("./types").AdminPage<import("./types").QualityFinding>>("admin/data-quality/findings", { page: 1, page_size: 25, ...query }, signal),
  adminAuditLogs: (query: Query = {}, signal?: AbortSignal) => get<import("./types").AdminPage<import("./types").AdminAuditLog>>("admin/audit-logs", { page: 1, page_size: 25, ...query }, signal),
  adminSystem: (signal?: AbortSignal) => get<import("./types").AdminSystemStatus>("admin/system", undefined, signal),
  adminConfiguration: (signal?: AbortSignal) => get<import("./types").SafeConfigurationStatus>("admin/configuration", undefined, signal),
};

export { API_BASE_URL };
