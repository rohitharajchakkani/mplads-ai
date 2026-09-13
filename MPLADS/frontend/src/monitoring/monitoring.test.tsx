import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { api, ApiError, setMonitoringCredentials } from "../api/client";
import { BenchmarkingPage, DuplicatesPage, MonitoringOverviewPage, RecommendationsPage, ReviewCaseDetailPage, ReviewsPage, RiskPage } from "../pages/MonitoringPages";
import { ExecutivePage } from "../pages/ExecutivePage";
import { AskAiPage } from "../pages/AskAiPage";

const provenance = { dataset_version: "test-release", generated_at: "2026-01-01T00:00:00Z" };
const risk = { work_key: "work-a", house: "LOK_SABHA", state_name: "Test State", district_or_ida: "Test District", mp_source_name: "Test MP", raw_score: 70, normalized_score: 70, risk_band: "HIGH", component_scores: {}, evidence: {}, data_quality_context: {}, provenance };
const page = (items: unknown[] = [risk], total = 1) => ({ items, pagination: { page: 1, page_size: 25, total, total_pages: total > 1 ? 2 : 1 }, provenance });
const response = (body: unknown, status = 200) => new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });

afterEach(() => { cleanup(); vi.unstubAllGlobals(); setMonitoringCredentials(undefined); });

describe("authorized monitoring", () => {
  it("sends development role headers and server-side pagination/filter parameters", async () => {
    const fetchMock = vi.fn().mockResolvedValue(response(page()));
    vi.stubGlobal("fetch", fetchMock);
    setMonitoringCredentials({ role: "STATE_NODAL_AUTHORITY", stateScope: "Test State" });
    await api.riskWorks({ page: 2, state: "Another State", risk_band: "HIGH" });
    expect(String(fetchMock.mock.calls[0][0])).toContain("page=2");
    expect(String(fetchMock.mock.calls[0][0])).toContain("risk_band=HIGH");
    expect(fetchMock.mock.calls[0][1].headers["X-MPLADS-Role"]).toBe("STATE_NODAL_AUTHORITY");
    expect(fetchMock.mock.calls[0][1].headers["X-MPLADS-State-Scope"]).toBe("Test State");
  });

  it.each([401, 403])("surfaces protected API status %i without a fallback", async (status) => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(response({ detail: { message: "Denied" } }, status)));
    await expect(api.riskSummary()).rejects.toMatchObject({ status } as Partial<ApiError>);
  });

  it("renders overview metrics supplied by protected APIs", async () => {
    vi.stubGlobal("fetch", vi.fn((input: RequestInfo | URL) => {
      const url = String(input);
      if (url.includes("alerts/summary")) return Promise.resolve(response({ total_alerts: 8, by_category: { FINANCIAL: 8 }, by_severity: { HIGH: 8 }, provenance }));
      if (url.includes("anomalies/summary")) return Promise.resolve(response({ total_ml_anomaly_signals: 3, model_version: "test-model", dataset_version: "test-release", generated_at: provenance.generated_at }));
      return Promise.resolve(response({ total_assessments: 12, risk_distribution: { HIGH: 2 }, signals_by_category: { FINANCIAL: 7 }, alerts_by_severity: { HIGH: 8 }, high_priority_works: 2, provenance }));
    }));
    render(<MemoryRouter><MonitoringOverviewPage /></MemoryRouter>);
    expect(await screen.findByText("Risk-assessed works")).toBeInTheDocument();
    expect(screen.getByText("12")).toBeInTheDocument();
    expect(screen.getByText("test-release", { exact: false })).toBeInTheDocument();
  });

  it("uses selected risk filters and advances with backend pagination", async () => {
    const fetchMock = vi.fn((input: RequestInfo | URL) => Promise.resolve(response(String(input).includes("filters/options") ? { data: { field: "house", options: [] }, provenance } : page([risk], 26))));
    vi.stubGlobal("fetch", fetchMock);
    render(<MemoryRouter initialEntries={["/monitoring/risk?state=Test%20State"]}><RiskPage /></MemoryRouter>);
    await screen.findByText("work-a");
    expect(fetchMock.mock.calls.map(([input]) => String(input)).find((url) => url.includes("risk/works"))).toContain("state=Test+State");
    fireEvent.click(screen.getByRole("button", { name: "Next" }));
    await waitFor(() => expect(String(fetchMock.mock.calls.at(-1)?.[0])).toContain("page=2"));
  });

  it("switches the risk result display without requerying the authorized result", async () => {
    const fetchMock = vi.fn((input: RequestInfo | URL) => Promise.resolve(response(String(input).includes("filters/options") ? { data: { field: "house", options: [] }, provenance } : page())));
    vi.stubGlobal("fetch", fetchMock);
    render(<MemoryRouter initialEntries={["/monitoring/risk"]}><RiskPage /></MemoryRouter>);
    await screen.findByText("work-a");
    const resultCalls = () => fetchMock.mock.calls.filter(([input]) => String(input).includes("risk/works")).length;
    const before = resultCalls();
    fireEvent.click(screen.getByRole("button", { name: "Grid" }));
    expect(await screen.findByLabelText("Risk indicator grid")).toBeInTheDocument();
    expect(resultCalls()).toBe(before);
  });

  it("opens a source-backed visual comparison for a duplicate candidate", async () => {
    const candidate = { candidate_id: "pair-1", work_a_key: "work-a", work_b_key: "work-b", similarity_score: 0.95, review_priority: "HIGH", contextual_comparison: {}, reason: "Engine comparison evidence", generated_at: provenance.generated_at, provenance };
    vi.stubGlobal("fetch", vi.fn((input: RequestInfo | URL) => {
      const url = String(input);
      if (url.includes("filters/options")) return Promise.resolve(response({ data: { field: "house", options: [] }, provenance }));
      if (url.includes("duplicates/candidates")) return Promise.resolve(response(page([candidate])));
      const key = url.includes("work-b") ? "work-b" : "work-a";
      return Promise.resolve(response({ data: { work: { canonical_work_key: key, house: "LOK_SABHA", state: "Test State", district_or_ida: "Test District", mp: "Test MP", work_description: `${key} description` }, sanctions: [], completions: [], expenditure: { total: "0", transaction_count: 0 }, recommendations: [], provenance: {} }, provenance: {} }));
    }));
    render(<MemoryRouter><DuplicatesPage /></MemoryRouter>);
    fireEvent.click(await screen.findByRole("button", { name: "Compare evidence" }));
    expect(await screen.findByText("Work A vs Work B")).toBeInTheDocument();
    expect(screen.getByText("work-a description")).toBeInTheDocument();
    expect(screen.getByText("work-b description")).toBeInTheDocument();
  });

  it("renders a server-paginated review queue and frozen case timeline", async () => {
    const reviewCase = { case_id: "case-1", source_alert_id: "alert-1", source_signal_id: null, canonical_work_key: "work-a", house: "LOK_SABHA", state_name: "Test State", district_or_ida: "Test District", mp_source_name: "Test MP", status: "OPEN", priority: "HIGH", assignee: null, dataset_version: "test-release", version: 1, created_at: provenance.generated_at, updated_at: provenance.generated_at, closed_at: null };
    vi.stubGlobal("fetch", vi.fn((input: RequestInfo | URL) => {
      const url = String(input);
      if (url.includes("reviews/summary")) return Promise.resolve(response({ by_status: { OPEN: 1 }, active_escalations: 0, provenance }));
      if (url.includes("reviews/cases/case-1")) return Promise.resolve(response({ ...reviewCase, evidence_snapshot_id: "snapshot-1", evidence_snapshot: { source_alert: { alert_id: "alert-1" } }, evidence_hash: "hash", events: [{ event_id: "event-1", actor: "test-reviewer", occurred_at: provenance.generated_at, action: "CREATED", metadata: {}, comment: null }], provenance }));
      return Promise.resolve(response(page([reviewCase])));
    }));
    const queue = render(<MemoryRouter><ReviewsPage /></MemoryRouter>);
    expect(await screen.findByText("case-1")).toBeInTheDocument();
    expect(screen.getByText("Open cases")).toBeInTheDocument();
    queue.unmount();
    render(<MemoryRouter initialEntries={["/monitoring/reviews/case-1"]}><Routes><Route path="/monitoring/reviews/:caseId" element={<ReviewCaseDetailPage />} /></Routes></MemoryRouter>);
    expect(await screen.findByText("Frozen analytical evidence")).toBeInTheDocument();
    expect(screen.getByText("CREATED")).toBeInTheDocument();
  });

  it("renders persisted peer benchmarks and evidence-based recommendations", async () => {
    const benchmark = { result_id: "benchmark-1", entity_type: "MP", entity_id: "Test MP", house: "LOK_SABHA", state_name: "Test State", district_or_ida: "Test District", mp_source_name: "Test MP", metric: "SANCTION_LATENCY_DAYS", formula: "Observed source dates", value: 20, peer_median: 12, p25: 8, p75: 16, p90: 19, iqr: 8, peer_count: 6, valid_work_count: 12, benchmark_available: true, unavailable_reason: null, directionality: "HIGHER_IS_CONCERN", bottleneck_flag: true, interpretation: "Potential bottleneck: longer-than-peer observed duration.", dataset_version: "test-release", benchmark_version: "benchmark-test", provenance_hash: "hash", generated_at: provenance.generated_at };
    const recommendation = { recommendation_id: "recommendation-1", canonical_work_key: "work-a", entity_type: "WORK", entity_id: "work-a", house: "LOK_SABHA", state_name: "Test State", district_or_ida: "Test District", mp_source_name: "Test MP", recommendation_type: "LIFECYCLE_SOURCE_REVIEW", reason: "Review the available lifecycle timeline.", evidence_references: { signal_id: "signal-1" }, priority: "HIGH", dataset_version: "test-release", status: "NOTED", generated_at: provenance.generated_at, updated_at: provenance.generated_at, version: 1 };
    vi.stubGlobal("fetch", vi.fn((input: RequestInfo | URL) => {
      const url = String(input);
      if (url.includes("filters/options")) return Promise.resolve(response({ data: { field: "house", options: [] }, provenance }));
      if (url.includes("benchmarking/summary")) return Promise.resolve(response({ run_id: "run-1", entity_count: 1, result_count: 3, by_metric: { SANCTION_LATENCY_DAYS: 1 }, bottleneck_count: 1, benchmark_version: "benchmark-test", dataset_version: "test-release", generated_at: provenance.generated_at }));
      if (url.includes("benchmarking/results")) return Promise.resolve(response(page([benchmark])));
      if (url.includes("benchmarking/peers")) return Promise.resolve(response({ result_id: "benchmark-1", cohort_definition: { same_house: true, minimum_peers: 5, minimum_valid_works: 10 }, peer_ids: ["Peer A"], peer_count: 1, provenance }));
      return Promise.resolve(response(page([recommendation])));
    }));
    const benchmarks = render(<MemoryRouter><BenchmarkingPage /></MemoryRouter>);
    expect((await screen.findAllByText("Test MP")).length).toBeGreaterThan(0);
    fireEvent.click(screen.getByRole("button", { name: "Cohort" }));
    expect(await screen.findByText("Same-House peer cohort")).toBeInTheDocument();
    benchmarks.unmount();
    render(<MemoryRouter><RecommendationsPage /></MemoryRouter>);
    expect(await screen.findByText("Review the available lifecycle timeline.")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Create review case" })).toBeInTheDocument();
  });

  it("renders an API-driven executive attention summary and unavailable trends", async () => {
    const executiveSummary = { total_monitored_works: 12, total_signals: 8, total_alerts: 4, high_priority_alerts: 3, high_priority_risk_works: 2, review_backlog: { OPEN: 1 }, active_escalations: 0, available_benchmarks: 6, benchmark_bottlenecks: 1, active_recommendations: 2, recommendations_by_priority: {}, recommendations_by_status: {}, provenance };
    vi.stubGlobal("fetch", vi.fn((input: RequestInfo | URL) => {
      const url = String(input);
      if (url.includes("executive/summary")) return Promise.resolve(response(executiveSummary));
      if (url.includes("executive/attention")) return Promise.resolve(response({ level: "MODERATE", signal_count: 6, drivers: [{ label: "High-priority alerts", count: 3, href: "/monitoring/alerts" }], high_priority_categories: { FINANCIAL: 3 }, scope: { role: "MINISTRY" }, provenance }));
      if (url.includes("executive/trends")) return Promise.resolve(response({ available: false, message: "Historical trend unavailable: only one completed analytical run is available.", rows: [], provenance }));
      if (url.includes("executive/geography")) return Promise.resolve(response({ rows: [], material_concentration: false, message: "No material concentration identified from the current data.", provenance }));
      if (url.includes("executive/comparison")) return Promise.resolve(response({ rows: [{ house: "LOK_SABHA", monitored_works: 12, high_priority_risk_works: 2, available_benchmarks: 6 }], provenance }));
      return Promise.resolve(response({ summary: executiveSummary, priority_queue: [], links: {}, provenance }));
    }));
    render(<MemoryRouter><ExecutivePage /></MemoryRouter>);
    expect(await screen.findByText("Executive command center")).toBeInTheDocument();
    expect(screen.getByText("Signal Count: 6. Derived from review workload, escalations, high-priority alerts, and high-priority risk works.")).toBeInTheDocument();
    expect(await screen.findByText("Historical trend unavailable: only one completed analytical run is available.")).toBeInTheDocument();
  });

  it("renders protected Ask AI data, provenance, and a clarification without preloaded answers", async () => {
    const aiResult = { request_id: "ai-test", answer: "Please specify the State.", intent: "RISK_QUERY", tool_results_summary: {}, tool_result: null, visualization: null, grounding: { source_data: "Verified data returned by an authorized MPLADS backend tool.", analytical_result: "Persisted monitoring output.", explanation: "Gemini prose is non-authoritative." }, provenance: { tool_used: null, filters_applied: {}, authorized_scope: { role: "MINISTRY", state: null, district_or_ida: null, mp: null }, dataset_version: "test-release" }, dataset_version: "test-release", generated_at: provenance.generated_at, scope: { role: "MINISTRY", state: null, district_or_ida: null, mp: null }, warnings: [], navigation_links: [], clarification_required: true, clarification_options: [{ entity_type: "DISTRICT", label: "Test District", filters: { state: "Test State", district_or_ida: "Test District" } }] };
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(response(aiResult)));
    render(<MemoryRouter><AskAiPage /></MemoryRouter>);
    fireEvent.change(screen.getByPlaceholderText(/Ask about MPLADS data or monitoring evidence/), { target: { value: "Show Test District works" } });
    fireEvent.click(screen.getByRole("button", { name: "Ask AI" }));
    expect(await screen.findByText("Clarification needed")).toBeInTheDocument();
    expect(screen.getAllByText("Test District").length).toBeGreaterThan(0);
    expect(screen.getByText("Gemini prose is non-authoritative.")).toBeInTheDocument();
  });

  it("renders a chart and report controls only for a successful verified Ask AI result", async () => {
    const aiResult = { request_id: "ai-chart", answer: "The verified distribution is shown below.", intent: "RISK_QUERY", tool_results_summary: { risk_distribution: { HIGH: 2 } }, tool_result: { tool_name: "get_risk_summary", success: true, data: { risk_distribution: { HIGH: 2 } }, result_count: 1, truncated: false, filters_applied: {}, scope: {}, dataset_version: "test-release", generated_at: provenance.generated_at, warnings: [], navigation_links: [] }, visualization: { title: "Risk distribution", description: "Verified tool result.", chart_type: "DONUT", x_axis: "Category", y_axis: "Count", unit: "Count", series: [{ key: "value", label: "Count" }], rows: [{ label: "HIGH", value: 2 }], record_count: 1, data_available: true }, grounding: { source_data: "Verified data", analytical_result: "Persisted output", explanation: "Gemini prose is non-authoritative." }, provenance: { tool_used: "get_risk_summary", filters_applied: {}, authorized_scope: { role: "MINISTRY", state: null, district_or_ida: null, mp: null }, dataset_version: "test-release" }, dataset_version: "test-release", generated_at: provenance.generated_at, scope: { role: "MINISTRY", state: null, district_or_ida: null, mp: null }, warnings: [], navigation_links: [], clarification_required: false, clarification_options: [] };
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(response(aiResult)));
    render(<MemoryRouter><AskAiPage /></MemoryRouter>);
    fireEvent.change(screen.getByPlaceholderText(/Ask about MPLADS data or monitoring evidence/), { target: { value: "What is the current risk distribution?" } });
    fireEvent.click(screen.getByRole("button", { name: "Ask AI" }));
    expect(await screen.findByText("Verified visualization")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Download CSV" })).toBeInTheDocument();
  });

  it("renders a verified work-status-by-House chart instead of an unsupported intent", async () => {
    const aiResult = { request_id: "ai-work-status", answer: "The verified source-status composition is shown below.", intent: "WORK_QUERY", tool_results_summary: { work_status_by_house: [{ house: "LOK_SABHA", status: "COMPLETED", work_count: 2 }] }, tool_result: { tool_name: "get_work_summary", success: true, data: { work_status_by_house: [{ house: "LOK_SABHA", status: "COMPLETED", work_count: 2 }] }, result_count: 1, truncated: false, filters_applied: { view: "WORK_STATUS_BY_HOUSE" }, scope: {}, dataset_version: "test-release", generated_at: provenance.generated_at, warnings: [], navigation_links: [] }, visualization: { title: "Source work status by House", description: "Verified active-release result.", chart_type: "STACKED_BAR", x_axis: "House", y_axis: "Works", unit: "Works", series: [{ key: "series_0", label: "COMPLETED" }], rows: [{ label: "LOK SABHA", value: 2, series_0: 2 }], record_count: 1, data_available: true, selection: { rule: "category_composition", rationale: "Verified categories are stacked by House.", source: "verified_tool_result" } }, grounding: { source_data: "Verified data", analytical_result: "Persisted output", explanation: "Gemini prose is non-authoritative." }, provenance: { tool_used: "get_work_summary", filters_applied: { view: "WORK_STATUS_BY_HOUSE" }, authorized_scope: { role: "MINISTRY", state: null, district_or_ida: null, mp: null }, dataset_version: "test-release" }, dataset_version: "test-release", generated_at: provenance.generated_at, scope: { role: "MINISTRY", state: null, district_or_ida: null, mp: null }, warnings: [], navigation_links: [], clarification_required: false, clarification_options: [] };
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(response(aiResult)));
    render(<MemoryRouter><AskAiPage /></MemoryRouter>);
    fireEvent.change(screen.getByPlaceholderText(/Ask about MPLADS data or monitoring evidence/), { target: { value: "Show work status by House" } });
    fireEvent.click(screen.getByRole("button", { name: "Ask AI" }));
    expect(await screen.findByText("Verified visualization")).toBeInTheDocument();
    expect(screen.getByRole("figure", { name: "Source work status by House" })).toBeInTheDocument();
    expect(screen.getByText("Inspect supporting table")).toBeInTheDocument();
    expect(screen.getByText("MPLADS active dataset")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Download CSV" })).toBeInTheDocument();
    expect(screen.queryByText("Intent: UNSUPPORTED QUERY")).not.toBeInTheDocument();
  });
});
