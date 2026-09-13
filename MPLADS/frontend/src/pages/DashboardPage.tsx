import { useCallback, useMemo, useRef, useState } from "react";
import { Banknote, Building2, CheckCircle2, Landmark, Users } from "lucide-react";
import { Link, useSearchParams } from "react-router-dom";
import { api } from "../api/client";
import type { Filters } from "../api/types";
import { HouseChart, ExpenditureTrendChart, StateChart, StatusChart } from "../components/Charts";
import { ErrorState, LoadingBlock, Skeleton } from "../components/DataState";
import { FilterBar } from "../components/FilterBar";
import { MetricCard } from "../components/MetricCard";
import { PageHeader } from "../components/PageHeader";
import { Panel } from "../components/Panel";
import { ReportActions, type ReportSection } from "../components/ReportActions";
import { SmartVisualization } from "../components/SmartVisualization";
import { SourceIndicator } from "../components/SourceIndicator";
import { useApi } from "../hooks/useApi";
import { filtersFromSearch, queryFromFilters } from "../lib/filters";
import { formatCompactCurrency, formatCurrency, formatInteger } from "../lib/format";

function DashboardKpis({
  filters,
  statusData,
  trendData,
  stateData,
  houseData,
}: {
  filters: Filters;
  statusData?: Awaited<ReturnType<typeof api.workStatus>>;
  trendData?: Awaited<ReturnType<typeof api.expenditureTrend>>;
  stateData?: Awaited<ReturnType<typeof api.stateSummary>>;
  houseData?: Awaited<ReturnType<typeof api.houseComparison>>;
}) {
  const request = useCallback((signal: AbortSignal) => api.dashboardSummary(filters, signal), [filters]);
  const summary = useApi(request, [request]);

  if (summary.loading && !summary.data) {
    return (
      <div className="space-y-4">
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6">
          {Array.from({ length: 6 }, (_, index) => <Skeleton key={`mon-${index}`} className="h-24" />)}
        </div>
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          {Array.from({ length: 4 }, (_, index) => <Skeleton key={`fin-${index}`} className="h-24" />)}
        </div>
      </div>
    );
  }

  if (summary.error && !summary.data) return <ErrorState error={summary.error} onRetry={summary.reload} />;
  if (!summary.data) return null;
  const data = summary.data.data;
  const optionalMoney = (value: string | { available: boolean; message: string }) => typeof value === "string" ? formatCompactCurrency(value) : "Not available";
  
  const reportRows = [
    ["Monitored works", data.monitored_works ?? data.total_canonical_works],
    ["Risk signals", data.risk_signals_count ?? 0],
    ["Analytical alerts", data.alerts_count ?? 0],
    ["Potential duplicates", data.potential_duplicates_count ?? 0],
    ["Open review workload", data.open_reviews_count ?? 0],
    ["Recommendations", data.recommendations_count ?? 0],
    ["Total works", data.total_canonical_works],
    ["Recommended works", data.recommended_works],
    ["Sanctioned works", data.sanctioned_works],
    ["Completed works", data.completed_works],
    ["Sanction amount", data.total_sanction_amount],
    ["Total expenditure", data.total_expenditure],
    ["MP records", data.mp_count],
    ["District / IDA records", data.district_or_ida_count],
  ].map(([label, value]) => ({ label: String(label), value: value as string | number }));

  const dashboardKpis = [
    { label: "Monitored works", value: formatInteger(data.monitored_works ?? data.total_canonical_works) },
    { label: "Risk signals", value: formatInteger(data.risk_signals_count ?? 0) },
    { label: "Alerts", value: formatInteger(data.alerts_count ?? 0) },
    { label: "Potential duplicates", value: formatInteger(data.potential_duplicates_count ?? 0) },
    { label: "Open reviews", value: formatInteger(data.open_reviews_count ?? 0) },
    { label: "Sanction amount", value: optionalMoney(data.total_sanction_amount) },
    { label: "Total expenditure", value: optionalMoney(data.total_expenditure) },
  ];

  const sections: ReportSection[] = [
    {
      title: "Scheme Monitoring & Risk Indicators",
      subtitle: "High-priority analytical signals for human review",
      kpis: [
        { label: "Monitored works", value: formatInteger(data.monitored_works ?? data.total_canonical_works), description: "Canonical works in scope" },
        { label: "Risk signals", value: formatInteger(data.risk_signals_count ?? 0), description: "Active risk signals" },
        { label: "Alerts", value: formatInteger(data.alerts_count ?? 0), description: "Analytical alerts" },
        { label: "Potential duplicates", value: formatInteger(data.potential_duplicates_count ?? 0), description: "Similarity pairs" },
        { label: "Open reviews", value: formatInteger(data.open_reviews_count ?? 0), description: "Pending workload" },
        { label: "Recommendations", value: formatInteger(data.recommendations_count ?? 0), description: "Advisory items" },
      ],
    },
    {
      title: "Financial & Lifecycle Execution",
      subtitle: "Sanction, expenditure, and completion metrics",
      kpis: [
        { label: "Sanction amount", value: optionalMoney(data.total_sanction_amount), description: "Linked sanctions" },
        { label: "Total expenditure", value: optionalMoney(data.total_expenditure), description: "Disbursed expenditure" },
        { label: "Sanctioned works", value: formatInteger(data.sanctioned_works), description: "Works with sanction" },
        { label: "Completed works", value: formatInteger(data.completed_works), description: "Works with completion" },
      ],
    },
    ...(statusData?.data?.rows?.length ? [{
      title: "Work Status Distribution",
      subtitle: "Status classification as reported in source records",
      chartType: "DONUT" as const,
      chartRows: statusData.data.rows,
      rows: statusData.data.rows,
    }] : []),
    ...(stateData?.data?.rows?.length ? [{
      title: "State / UT Work Distribution",
      subtitle: "Leading State / UT distributions by canonical work count",
      chartType: "BAR" as const,
      chartRows: stateData.data.rows,
      rows: stateData.data.rows,
    }] : []),
    ...(houseData?.data?.rows?.length ? [{
      title: "House Comparison (Lok Sabha vs Rajya Sabha)",
      subtitle: "Comparison of source-supported works across Houses",
      chartType: "BAR" as const,
      chartRows: houseData.data.rows,
      rows: houseData.data.rows,
    }] : []),
    ...(trendData ? [{
      title: "Expenditure Trend",
      subtitle: "Monthly expenditure disbursements when source dates exist",
      chartType: "LINE" as const,
      chartRows: trendData.data.data_available ? trendData.data.rows : [],
      rows: trendData.data.data_available ? trendData.data.rows : [],
      emptyMessage: trendData.data.data_available ? undefined : (trendData.data.message ?? "Trend unavailable for the selected data."),
    }] : []),
  ];

  return <>
    <div className="mb-5 flex flex-wrap items-center justify-between gap-3 rounded-lg border border-line bg-white px-4 py-3 shadow-sm">
      <div>
        <p className="text-sm font-semibold text-ink">Current dashboard report</p>
        <p className="mt-1 text-xs text-slate-500">Generate a print-safe report or export the visible active-release summary.</p>
      </div>
      <ReportActions
        title="MPLADS Dashboard Report"
        summary="Current active-release dashboard summary and analytical sections."
        rows={reportRows}
        kpis={dashboardKpis}
        sections={sections}
        filters={filters}
        provenance={summary.data.provenance}
        reportSelector="#dashboard-report"
      />
    </div>

    {/* SIH Core Monitoring KPIs (Priority 1) */}
    <div className="mb-4">
      <div className="mb-2 flex items-center justify-between">
        <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-500">SIH Scheme Monitoring & Risk Indicators</h3>
        <Link to="/monitoring" className="text-xs font-medium text-blue hover:underline">Open Monitoring Center →</Link>
      </div>
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6">
        <MetricCard
          label="Monitored works"
          value={formatInteger(data.monitored_works ?? data.total_canonical_works)}
          description="Distinct canonical works in scope."
          icon={Building2}
        />
        <MetricCard
          label="Risk signals"
          value={formatInteger(data.risk_signals_count ?? 0)}
          description="Active risk signals detected."
          icon={Landmark}
        />
        <MetricCard
          label="Alerts"
          value={formatInteger(data.alerts_count ?? 0)}
          description="Analytical alerts triggered."
          icon={CheckCircle2}
        />
        <MetricCard
          label="Potential duplicates"
          value={formatInteger(data.potential_duplicates_count ?? 0)}
          description="High/medium duplicate candidates."
          icon={Users}
        />
        <MetricCard
          label="Open reviews"
          value={formatInteger(data.open_reviews_count ?? 0)}
          description="Pending investigation workload."
          icon={CheckCircle2}
        />
        <MetricCard
          label="Recommendations"
          value={formatInteger(data.recommendations_count ?? 0)}
          description="Operational advisory items."
          icon={Landmark}
        />
      </div>
    </div>

    {/* Financial & Lifecycle Execution KPIs */}
    <div>
      <h3 className="mb-2 text-xs font-semibold uppercase tracking-wider text-slate-500">Scheme Lifecycle & Financial Execution</h3>
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <MetricCard
          label="Sanction amount"
          value={formatCompactCurrency(data.total_sanction_amount)}
          exactValue={formatCurrency(data.total_sanction_amount)}
          description="Sum of linked sanction amounts."
          icon={Banknote}
        />
        <MetricCard
          label="Total expenditure"
          value={formatCompactCurrency(data.total_expenditure)}
          exactValue={formatCurrency(data.total_expenditure)}
          description="Sum of source expenditure transactions."
          icon={Banknote}
        />
        <MetricCard
          label="Sanctioned works"
          value={formatInteger(data.sanctioned_works)}
          description="Works with linked sanction records."
          icon={CheckCircle2}
        />
        <MetricCard
          label="Completed works"
          value={formatInteger(data.completed_works)}
          description="Works with linked completion records."
          icon={CheckCircle2}
        />
      </div>
    </div>

    <div className="mt-4 grid gap-4 lg:grid-cols-2">
      <div className="rounded-xl border border-line bg-white p-4 text-sm text-slate-700">
        <strong className="text-ink">Allocation:</strong> {optionalMoney(data.allocation)}
        {typeof data.allocation !== "string" && <span className="block pt-1 text-xs text-slate-500">{data.allocation.message}</span>}
      </div>
      <div className="rounded-xl border border-line bg-white p-4 text-sm text-slate-700">
        <strong className="text-ink">Calamity amount:</strong> {optionalMoney(data.calamity_amount)}
        {typeof data.calamity_amount !== "string" && <span className="block pt-1 text-xs text-slate-500">{data.calamity_amount.message}</span>}
      </div>
    </div>
    <div className="mt-4"><SourceIndicator provenance={summary.data.provenance} /></div>
  </>;
}

function StatusPanel({ filters, result }: { filters: Filters; result?: ReturnType<typeof useApi<Awaited<ReturnType<typeof api.workStatus>>>> }) {
  const fallback = useApi(useCallback((signal: AbortSignal) => api.workStatus(filters, signal), [filters]), [filters]);
  const active = result ?? fallback;
  return <Panel title="Source work status" description="Status labels are preserved from the supplied source; no frontend remapping is applied.">{active.loading && !active.data ? <LoadingBlock /> : active.error && !active.data ? <ErrorState error={active.error} onRetry={active.reload} /> : active.data ? <><StatusChart rows={active.data.data.rows} /><p className="mt-3 text-xs text-slate-500">{active.data.data.normalization}</p><SourceIndicator provenance={active.data.provenance} /></> : null}</Panel>;
}

function TrendPanel({ filters, result }: { filters: Filters; result?: ReturnType<typeof useApi<Awaited<ReturnType<typeof api.expenditureTrend>>>> }) {
  const fallback = useApi(useCallback((signal: AbortSignal) => api.expenditureTrend(filters, signal), [filters]), [filters]);
  const active = result ?? fallback;
  return <Panel title="Expenditure trend" description="Monthly expenditure totals only when source dates are available.">{active.loading && !active.data ? <LoadingBlock /> : active.error && !active.data ? <ErrorState error={active.error} onRetry={active.reload} /> : active.data?.data.data_available ? <><ExpenditureTrendChart rows={active.data.data.rows} /><SourceIndicator provenance={active.data.provenance} /></> : <p className="rounded-lg bg-slate-50 p-4 text-sm text-slate-600">{active.data?.data.message ?? "Trend unavailable for the selected data."}</p>}</Panel>;
}

function StatePanel({ filters, result }: { filters: Filters; result?: ReturnType<typeof useApi<Awaited<ReturnType<typeof api.stateSummary>>>> }) {
  const fallback = useApi(useCallback((signal: AbortSignal) => api.stateSummary(filters, signal), [filters]), [filters]);
  const active = result ?? fallback;
  return <Panel title="State summary" description="Leading state/UT source values by canonical work count.">{active.loading && !active.data ? <LoadingBlock /> : active.error && !active.data ? <ErrorState error={active.error} onRetry={active.reload} /> : active.data ? <><StateChart rows={active.data.data.rows} /><SourceIndicator provenance={active.data.provenance} /></> : null}</Panel>;
}

function HousePanel({ filters, result }: { filters: Filters; result?: ReturnType<typeof useApi<Awaited<ReturnType<typeof api.houseComparison>>>> }) {
  const comparisonFilters = useMemo(() => ({ ...filters, house: undefined }), [filters]);
  const fallback = useApi(useCallback((signal: AbortSignal) => api.houseComparison(comparisonFilters, signal), [comparisonFilters]), [comparisonFilters]);
  const active = result ?? fallback;
  const note = filters.house ? "Comparison keeps other selected filters but omits House so both Houses can be compared." : "Work counts across the two Houses in the active selection.";
  return <Panel title="House comparison" description={note}>{active.loading && !active.data ? <LoadingBlock /> : active.error && !active.data ? <ErrorState error={active.error} onRetry={active.reload} /> : active.data ? <><HouseChart rows={active.data.data.rows} /><SourceIndicator provenance={active.data.provenance} /></> : null}</Panel>;
}

function LifecyclePanel({ filters }: { filters: Filters }) {
  const request = useCallback((signal: AbortSignal) => api.exploreVisualization("lifecycle", "summary", filters, signal), [filters]);
  const result = useApi(request, [request]);
  return <Panel title="Observed lifecycle duration" description="Only source records with both dates are used; no policy deadline is inferred.">{result.loading && !result.data ? <LoadingBlock /> : result.error && !result.data ? <ErrorState error={result.error} onRetry={result.reload} /> : result.data ? <><SmartVisualization spec={result.data.data} /><div className="mt-4"><SourceIndicator provenance={result.data.provenance} /></div></> : null}</Panel>;
}

const groupOptions: Record<string, Array<[string, string]>> = {
  works: [["summary", "Summary KPI"], ["house", "House share"], ["state", "State / UT"], ["district_or_ida", "District / IDA"], ["mp", "MP"], ["work", "Work details"], ["status", "Source status share"], ["state_category", "State × source category"], ["period", "Period (when dated records exist)"]],
  expenditure: [["house", "House share"], ["state", "State / UT"], ["district_or_ida", "District / IDA"], ["mp", "MP"], ["work", "Work"], ["period", "Period (when dated records exist)"]],
  status: [["status", "Source status share"], ["house", "Source status by House"]],
  progress: [["state", "Sanctioned vs completed by State / UT"], ["house", "Sanctioned vs completed by House"]],
  lifecycle: [["summary", "Observed duration summary"], ["distribution", "Observed sanction-to-completion distribution"]],
  relationship: [["state", "Works vs expenditure by State / UT"]],
};

function GuidedVisualization({ filters }: { filters: Filters }) {
  const [metric, setMetric] = useState("expenditure");
  const [groupBy, setGroupBy] = useState("state");
  const [result, setResult] = useState<Awaited<ReturnType<typeof api.exploreVisualization>>>();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<Error>();
  const controller = useRef<AbortController | null>(null);
  const requestId = useRef(0);
  const changeMetric = (next: string) => { setMetric(next); setGroupBy(groupOptions[next][0][0]); };
  const generate = async () => {
    controller.current?.abort();
    const current = ++requestId.current;
    const abort = new AbortController(); controller.current = abort;
    setLoading(true); setError(undefined);
    try {
      const response = await api.exploreVisualization(metric, groupBy, filters, abort.signal);
      if (current === requestId.current) setResult(response);
    } catch (caught) {
      if (current === requestId.current && !(caught instanceof DOMException && caught.name === "AbortError")) setError(caught instanceof Error ? caught : new Error("Unable to generate visualization."));
    } finally { if (current === requestId.current) setLoading(false); }
  };
  return <Panel title="Explore visually" description="Choose a database-backed metric and grouping. A chart is selected only when the active-release result supports it; this does not call an AI provider."><div className="grid gap-3 sm:grid-cols-3"><label className="field-label">Metric<select className="field-control" value={metric} onChange={(event) => changeMetric(event.target.value)}><option value="expenditure">Expenditure</option><option value="works">Works</option><option value="status">Source status</option><option value="progress">Observed work progress</option><option value="lifecycle">Observed lifecycle</option><option value="relationship">Works and expenditure relationship</option></select></label><label className="field-label">Group by<select className="field-control" value={groupBy} onChange={(event) => setGroupBy(event.target.value)}>{groupOptions[metric].map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></label><div className="flex items-end"><button className="button-primary w-full" type="button" onClick={generate} disabled={loading}>{loading ? "Generating…" : "Generate visualization"}</button></div></div>{error ? <div className="mt-4"><ErrorState error={error} /></div> : null}{result ? <div className="mt-5 space-y-4"><SmartVisualization spec={result.data} /><ReportActions title={result.data.title} summary={result.data.description} rows={result.data.rows} filters={filters} provenance={result.provenance} /><SourceIndicator provenance={result.provenance} /></div> : null}</Panel>;
}

export default function DashboardPage() {
  const [search, setSearch] = useSearchParams();
  const filters = useMemo(() => filtersFromSearch(search), [search]);
  const comparisonFilters = useMemo(() => ({ ...filters, house: undefined }), [filters]);
  const setFilters = (next: Filters) => setSearch(queryFromFilters(next), { replace: false });

  // Coordinated analytical requests for panels & reports
  const statusResult = useApi(useCallback((signal: AbortSignal) => api.workStatus(filters, signal), [filters]), [filters]);
  const trendResult = useApi(useCallback((signal: AbortSignal) => api.expenditureTrend(filters, signal), [filters]), [filters]);
  const stateResult = useApi(useCallback((signal: AbortSignal) => api.stateSummary(filters, signal), [filters]), [filters]);
  const houseResult = useApi(useCallback((signal: AbortSignal) => api.houseComparison(comparisonFilters, signal), [comparisonFilters]), [comparisonFilters]);

  return <div>
    <PageHeader eyebrow="Public data context" title="MPLADS implementation context" description="Use active-release records to orient an inquiry. Risk, anomaly, alert and review findings remain inside authorized Monitoring." />
    <section className="mb-6 overflow-hidden rounded-lg border border-blue-100 bg-white shadow-sm" aria-labelledby="monitoring-start">
      <div className="gov-rule h-0.5" aria-hidden="true" />
      <div className="flex flex-wrap items-center justify-between gap-5 p-5">
        <div>
          <p className="eyebrow">Monitoring overview</p>
          <h2 id="monitoring-start" className="mt-2 text-xl font-semibold text-ink">Where should attention go?</h2>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-700">Authorized officers can inspect anomaly signals, fraud-risk indicators, inefficiency evidence, alerts and review workload without exposing those protected findings publicly.</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Link className="button-primary" to="/monitoring">Go to Monitoring</Link>
          <Link className="button-secondary" to="/monitoring/ai">Ask AI</Link>
        </div>
      </div>
    </section>
    <FilterBar filters={filters} onChange={setFilters} onReset={() => setSearch(new URLSearchParams())} />
    <section id="dashboard-report" className="mt-6">
      <DashboardKpis
        filters={filters}
        statusData={statusResult.data}
        trendData={trendResult.data}
        stateData={stateResult.data}
        houseData={houseResult.data}
      />
      <div className="mt-6"><GuidedVisualization filters={filters} /></div>
      <div className="mt-6 grid gap-6 xl:grid-cols-2">
        <StatusPanel filters={filters} result={statusResult} />
        <TrendPanel filters={filters} result={trendResult} />
        <StatePanel filters={filters} result={stateResult} />
        <HousePanel filters={filters} result={houseResult} />
        <LifecyclePanel filters={filters} />
      </div>
    </section>
  </div>;
}
