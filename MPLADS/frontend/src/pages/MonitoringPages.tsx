import { type ReactNode, useCallback, useId, useMemo, useRef, useState } from "react";
import { Activity, AlertTriangle, Database, GitCompareArrows, Landmark, Timer } from "lucide-react";
import { Link, useParams, useSearchParams } from "react-router-dom";
import { api, ApiError } from "../api/client";
import type { BenchmarkResult, DuplicateCandidate, Filters, MonitoringAlert, Recommendation, RiskWork, WorkDetailData } from "../api/types";
import { EmptyState, ErrorState, LoadingBlock, Skeleton } from "../components/DataState";
import { FilterBar } from "../components/FilterBar";
import { MetricCard } from "../components/MetricCard";
import { PageHeader } from "../components/PageHeader";
import { Pagination } from "../components/Pagination";
import { Panel } from "../components/Panel";
import { ReportActions } from "../components/ReportActions";
import { SmartVisualization } from "../components/SmartVisualization";
import { getSemanticDot, getSemanticStyle, SeverityBadge, StatusBadge } from "../components/StatusBadge";
import { ViewToggle, type CollectionView, getPersistedView, setPersistedView } from "../components/ViewToggle";
import { SourceText } from "../components/SourceText";
import { useApi } from "../hooks/useApi";
import { formatDateTime, formatInteger } from "../lib/format";

const labels: Record<string, string> = { FINANCIAL: "Financial", PAYMENT: "Payment", LIFECYCLE: "Lifecycle", DUPLICATE_CANDIDATE: "Duplicate candidate", ML_ANOMALY: "ML anomaly", COMBINED: "Combined" };
const filterNames = ["search", "risk_band", "house", "state", "district_or_ida", "mp"] as const;

export function getRiskBorder(band?: string | null) {
  if (!band) return "border-l-4 border-l-slate-300";
  const norm = band.toUpperCase().replace(/[\s-]+/g, "_");
  switch (norm) {
    case "VERY_HIGH":
      return "border-l-4 border-l-red-600";
    case "HIGH":
      return "border-l-4 border-l-rose-500";
    case "MEDIUM":
      return "border-l-4 border-l-amber-500";
    case "LOW":
      return "border-l-4 border-l-emerald-500";
    default:
      return "border-l-4 border-l-slate-300";
  }
}

function authError(error: Error, retry: () => void) {
  if (error instanceof ApiError && error.status === 401) return <ErrorState title="Please sign in to access authorized monitoring." error={new Error("Select a development access profile. Backend authorization remains required for every request.")} onRetry={retry} />;
  if (error instanceof ApiError && error.status === 403) return <ErrorState title="You do not have permission to view this monitoring scope." error={new Error("The server denied this role or scope.")} onRetry={retry} />;
  return <ErrorState title="Unable to load monitoring data." error={error} onRetry={retry} />;
}

function Provenance({ version, generated, model }: { version: string; generated: string; model?: string | null }) {
  return (
    <div className="mt-4 flex flex-wrap items-center gap-2 text-xs text-slate-500">
      <span className="inline-flex items-center gap-1.5 font-medium text-slate-700">
        <Database className="size-3.5 text-slate-400" aria-hidden="true" />
        Data source: MPLADS active dataset
      </span>
      <span>·</span>
      <span>Analytics generated {formatDateTime(generated)}</span>
      {model ? <span>· Model: {model}</span> : null}
      <details className="inline text-xs text-slate-500">
        <summary className="cursor-pointer text-slate-500 hover:text-slate-700 hover:underline">
          Technical details
        </summary>
        <span className="ml-1 font-mono text-[11px] bg-white px-2 py-0.5 rounded border border-blue-200 text-slate-700">
          Release: {version}
        </span>
      </details>
    </div>
  );
}

function Distribution({ title, values }: { title: string; values: Record<string, number> }) {
  const rows = Object.entries(values).map(([name, value]) => ({ label: labels[name] ?? name.replaceAll("_", " "), value }));
  return <Panel title={title}>{rows.length ? <SmartVisualization spec={{ title, description: "Counts from the current authorized monitoring response.", chart_type: "DISTRIBUTION", x_axis: "Category", y_axis: "Count", unit: "Count", series: [{ key: "value", label: "Count" }], rows, record_count: rows.length, data_available: true }} /> : <EmptyState title="No monitoring results match the selected filters." />}</Panel>;
}

function FilterInput({ label, value, setValue }: { label: string; value: string; setValue: (value: string) => void }) {
  return <label className="field-label">{label}<input className="field-control" type="search" value={value} onChange={(event) => setValue(event.target.value.replace(/\s+/g, " ").trimStart())} /></label>;
}

function MonitoringScopeFilters({ filters, update, children }: { filters: Record<string, string>; update: (next: Record<string, string>) => void; children?: ReactNode }) {
  const scope: Filters = { house: filters.house || undefined, state: filters.state || undefined, district_or_ida: filters.district_or_ida || undefined, mp: filters.mp || undefined };
  const applyScope = (next: Filters) => update({ ...filters, house: next.house ?? "", state: next.state ?? "", district_or_ida: next.district_or_ida ?? "", mp: next.mp ?? "" });
  return <div className="space-y-3"><FilterBar filters={scope} onChange={applyScope} onReset={() => update({})} fields={["house", "state", "district_or_ida", "mp"]} />{children ? <section className="grid gap-3 rounded-xl border border-line bg-white p-4 sm:grid-cols-2 xl:grid-cols-3" aria-label="Monitoring-specific filters">{children}</section> : null}</div>;
}

function SignalPill({ value, label }: { value: string; label?: string }) {
  const style = getSemanticStyle(value);
  const dot = getSemanticDot(value);
  return (
    <span className={`inline-flex items-center gap-1.5 rounded-md border px-2.5 py-1 text-xs font-semibold tracking-wide uppercase ${style}`}>
      <span className={`size-1.5 shrink-0 rounded-full ${dot}`} aria-hidden="true" />
      {label && <span className="opacity-75">{label}:</span>}
      <span>{value.replaceAll("_", " ")}</span>
    </span>
  );
}
function primarySignal(row: RiskWork) { return Object.entries(row.component_scores).sort(([, first], [, second]) => second - first)[0]?.[0]?.replaceAll("_", " ") ?? "Source-backed signal"; }

function RiskCards({ items }: { items: RiskWork[] }) {
  return (
    <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3" aria-label="Risk indicator grid">
      {items.map((row) => (
        <article className={`flex min-h-64 flex-col rounded-lg border border-line bg-white p-5 shadow-sm hover:shadow-md transition-all ${getRiskBorder(row.risk_band)}`} key={row.work_key}>
          <div className="flex items-start justify-between gap-3">
            <div>
              <p className="text-xs font-bold uppercase tracking-[0.12em] text-slate-500">Risk indicator</p>
              <Link className="mt-1 block font-semibold text-blue hover:underline" to={`/monitoring/risk/${encodeURIComponent(row.work_key)}`}>{row.work_key}</Link>
            </div>
            <SignalPill value={row.risk_band} />
          </div>
          <dl className="mt-5 grid grid-cols-2 gap-x-4 gap-y-3 border-t border-line pt-4 text-sm">
            <div>
              <dt className="text-xs text-slate-500">Priority score</dt>
              <dd className="mt-1 font-semibold text-ink">{row.normalized_score.toFixed(1)} / 100</dd>
            </div>
            <div>
              <dt className="text-xs text-slate-500">Primary signal</dt>
              <dd className="mt-1 capitalize text-slate-700">{primarySignal(row)}</dd>
            </div>
            <div>
              <dt className="text-xs text-slate-500">House</dt>
              <dd className="mt-1 text-slate-700">{row.house.replaceAll("_", " ")}</dd>
            </div>
            <div>
              <dt className="text-xs text-slate-500">State</dt>
              <dd className="mt-1 truncate text-slate-700" title={row.state_name ?? undefined}>{row.state_name ?? "Not available"}</dd>
            </div>
          </dl>
          <Link className="mt-auto pt-5 text-sm font-semibold text-blue hover:underline" to={`/monitoring/risk/${encodeURIComponent(row.work_key)}`}>View evidence</Link>
        </article>
      ))}
    </div>
  );
}

function RiskTable({ data, setPage, view = "list" }: { data: { items: RiskWork[]; pagination: { page: number; page_size: number; total: number; total_pages: number } }; setPage?: (page: number) => void; view?: CollectionView }) {
  return <>{view === "grid" ? <RiskCards items={data.items} /> : <div className="overflow-x-auto"><table className="min-w-[760px] w-full text-left text-sm" aria-label="Risk indicator list"><thead><tr className="border-b border-line text-xs uppercase tracking-wide text-slate-500"><th className="p-3">Work</th><th className="p-3">Risk</th><th className="p-3">Band</th><th className="p-3">House</th><th className="p-3">State</th><th className="p-3">Evidence</th></tr></thead><tbody>{data.items.map((row) => <tr className="border-b border-line/70" key={row.work_key}><td className="p-3 font-medium text-ink">{row.work_key}</td><td className="p-3 font-semibold">{row.normalized_score.toFixed(1)} / 100</td><td className="p-3"><SignalPill value={row.risk_band} /></td><td className="p-3">{row.house.replaceAll("_", " ")}</td><td className="p-3">{row.state_name ?? "Not available"}</td><td className="p-3"><Link className="font-medium text-blue hover:underline" to={`/monitoring/risk/${encodeURIComponent(row.work_key)}`}>View evidence</Link></td></tr>)}</tbody></table></div>}{!data.items.length && <EmptyState title="No monitoring results match the selected filters." />}{setPage && <Pagination page={data.pagination} onPageChange={setPage} />}</>;
}

export function MonitoringOverviewPage() {
  const risk = useApi(useCallback((signal: AbortSignal) => api.riskSummary(signal), []), []);
  const alerts = useApi(useCallback((signal: AbortSignal) => api.alertSummary(signal), []), []);
  const anomalies = useApi(useCallback((signal: AbortSignal) => api.anomalySummary(signal), []), []);
  if (risk.loading || alerts.loading || anomalies.loading) return <><PageHeader eyebrow="Authorized monitoring" title="Monitoring overview" description="Protected, active-release analytical intelligence for authorized review." /><div className="grid gap-4 md:grid-cols-3"><Skeleton className="h-32" /><Skeleton className="h-32" /><Skeleton className="h-32" /></div></>;
  const error = risk.error ?? alerts.error ?? anomalies.error;
  if (error) return authError(error, risk.reload);
  if (!risk.data || !alerts.data || !anomalies.data) return null;
  const reportRows = [{ label: "Risk-assessed works", value: risk.data.total_assessments }, { label: "Monitoring signals", value: Object.values(risk.data.signals_by_category).reduce((sum, value) => sum + value, 0) }, { label: "Alerts", value: alerts.data.total_alerts }, { label: "ML anomaly signals", value: anomalies.data.total_ml_anomaly_signals }, { label: "High-priority works", value: risk.data.high_priority_works }];
  const monitoringKpis = [
    { label: "Risk-assessed works", value: formatInteger(risk.data.total_assessments) },
    { label: "Monitoring signals", value: formatInteger(Object.values(risk.data.signals_by_category).reduce((sum, value) => sum + value, 0)) },
    { label: "Alerts", value: formatInteger(alerts.data.total_alerts) },
    { label: "ML anomaly signals", value: formatInteger(anomalies.data.total_ml_anomaly_signals) },
  ];
  const monitoringChartRows = Object.entries(risk.data.risk_distribution).map(([band, count]) => ({
    label: band.replaceAll("_", " "),
    value: count,
  }));
  return <div><PageHeader eyebrow="Authorized monitoring" title="Monitoring overview" description="Protected analytical signals are decision support. AI identifies signals; authorized officials make the final decision." /><section id="monitoring-overview-report"><div className="mb-6 flex flex-wrap items-center justify-between gap-3 rounded-lg border border-line bg-white px-4 py-3 shadow-sm"><div><p className="text-sm font-semibold text-ink">Monitoring overview report</p><p className="mt-1 text-xs text-slate-500">Only the current server-authorized summary is included.</p></div><ReportActions title="MPLADS Monitoring Overview Report" summary="Current authorized monitoring summary." rows={reportRows} chartRows={monitoringChartRows} kpis={monitoringKpis} provenance={risk.data.provenance} reportSelector="#monitoring-overview-report" /></div><div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4"><MetricCard label="Risk-assessed works" value={formatInteger(risk.data.total_assessments)} description="Active-release works with a stored monitoring-priority assessment." icon={Activity} /><MetricCard label="Monitoring signals" value={formatInteger(Object.values(risk.data.signals_by_category).reduce((sum, value) => sum + value, 0))} description="Stored analytical signals by evidence family." icon={AlertTriangle} /><MetricCard label="Alerts" value={formatInteger(alerts.data.total_alerts)} description="Idempotent active-release analytical alerts." icon={AlertTriangle} /><MetricCard label="ML anomaly signals" value={formatInteger(anomalies.data.total_ml_anomaly_signals)} description="Records differing from the learned distribution; not findings of wrongdoing." icon={GitCompareArrows} /></div><div className="mt-6 grid gap-6 xl:grid-cols-2"><Distribution title="Risk distribution" values={risk.data.risk_distribution} /><Distribution title="Signals by category" values={risk.data.signals_by_category} /><Distribution title="Alerts by severity" values={alerts.data.by_severity} /><Panel title="Monitoring interpretation"><p className="text-sm leading-6 text-slate-700">Higher monitoring priority brings separate, source-backed evidence families together for review. It is not a fraud probability, legal conclusion, or finding of wrongdoing.</p><p className="mt-3 text-sm leading-6 text-slate-700">High / Very High monitoring-priority works: <strong>{formatInteger(risk.data.high_priority_works)}</strong></p></Panel></div><Provenance version={risk.data.provenance.dataset_version} generated={risk.data.provenance.generated_at} /></section></div>;
}

export function RiskPage({ category }: { category?: string }) {
  const [params, setParams] = useSearchParams();
  const page = Number(params.get("page") ?? 1);
  const storageKey = category === "ML_ANOMALY" ? "anomalies" : "risk";
  const persistedView = getPersistedView(storageKey, "grid");
  const viewParam = params.get("view");
  const view: CollectionView = viewParam === "list" ? "list" : viewParam === "grid" ? "grid" : persistedView;
  const filterKey = filterNames.map((name) => `${name}=${params.get(name) ?? ""}`).join("&");
  const filters = useMemo(() => Object.fromEntries(filterNames.map((name) => [name, params.get(name) ?? ""])), [filterKey]);
  const update = (next: Record<string, string>) => {
    const nextView = next.view === "list" ? "list" : next.view === "grid" ? "grid" : view;
    setPersistedView(storageKey, nextView);
    const values = { ...next, view: nextView };
    setParams(Object.fromEntries(Object.entries(values).filter(([, value]) => value)));
  };
  const request = useCallback((signal: AbortSignal) => api.riskWorks({ page, ...filters, ...(category ? { signal_category: category } : {}) }, signal), [page, filters, category]);
  const result = useApi(request, [request]);
  const title = category === "ML_ANOMALY" ? "ML anomaly signals" : "Risk-ranked works";
  const reportRows = result.data?.items.map((row) => ({ work: row.work_key, risk_score: Number(row.normalized_score.toFixed(1)), risk_band: row.risk_band, house: row.house, state: row.state_name ?? "Not available", primary_signal: primarySignal(row) })) ?? [];
  return <div><PageHeader eyebrow="Authorized monitoring" title={title} description={category === "ML_ANOMALY" ? "ML anomaly signals identify records that differ from the learned distribution. They do not establish wrongdoing." : "Monitoring-priority scores combine separate explainable evidence families. Use them to focus human review."} /><MonitoringScopeFilters filters={filters} update={update}><FilterInput label="Search" value={filters.search} setValue={(value) => update({ ...filters, search: value })} /><label className="field-label">Risk band<select className="field-control" value={filters.risk_band} onChange={(event) => update({ ...filters, risk_band: event.target.value })}><option value="">All bands</option><option>LOW</option><option>MEDIUM</option><option>HIGH</option><option>VERY_HIGH</option></select></label></MonitoringScopeFilters><section id={category === "ML_ANOMALY" ? "anomaly-results-report" : "risk-results-report"} className="mt-6"><Panel title={category === "ML_ANOMALY" ? "Anomaly signals" : "Risk indicators"} description="Server-side pagination and filters remain constrained by the server-authorized scope." actions={<ViewToggle value={view} onChange={(next) => update({ ...filters, view: next })} label={`${category === "ML_ANOMALY" ? "Anomaly" : "Risk"} result view`} />}>{result.loading ? <LoadingBlock label="Loading monitoring results…" /> : result.error ? authError(result.error, result.reload) : result.data ? <><div className="mb-4 flex flex-wrap items-center justify-between gap-3 rounded-lg border border-line bg-slate-50 p-3"><p className="text-sm text-slate-600">{result.data.pagination.total.toLocaleString("en-IN")} authorized {category === "ML_ANOMALY" ? "anomaly" : "risk"} result{result.data.pagination.total === 1 ? "" : "s"} · {view === "grid" ? "Grid view" : "List view"}</p><ReportActions title={category === "ML_ANOMALY" ? "MPLADS Anomaly Signal Report" : "MPLADS Risk Indicator Report"} summary="Current authorized monitoring results and evidence context." rows={reportRows} filters={{ ...filters, signal_category: category ?? "all" }} provenance={result.data.provenance} reportSelector={category === "ML_ANOMALY" ? "#anomaly-results-report" : "#risk-results-report"} /></div><RiskTable data={result.data} view={view} setPage={(next) => update({ ...filters, page: String(next) })} /><Provenance version={result.data.provenance.dataset_version} generated={result.data.provenance.generated_at} /></> : null}</Panel></section></div>;
}

export function RiskDetailPage() {
  const { "*": key = "" } = useParams();
  const request = useCallback((signal: AbortSignal) => api.riskWork(decodeURIComponent(key), signal), [key]);
  const result = useApi(request, [request]);

  if (result.loading) return <LoadingBlock label="Loading monitoring-priority explanation…" />;
  if (result.error) return authError(result.error, result.reload);
  if (!result.data) return null;
  const data = result.data;

  return <div>
    <PageHeader
      eyebrow="Authorized monitoring"
      title="Monitoring-priority explanation"
      description="Why this work receives monitoring attention. Evidence remains separate and source-backed."
      actions={
        <Link className="button-secondary" to={`/works/${encodeURIComponent(data.work_key)}`}>
          Open public work record
        </Link>
      }
    />

    <div className="grid gap-4 sm:grid-cols-2">
      <MetricCard label="Monitoring priority" value={`${data.normalized_score.toFixed(1)} / 100`} description="Normalized raw monitoring score; not a probability." icon={Activity} />
      <MetricCard label="Risk band" value={data.risk_band.replaceAll("_", " ")} description="Monitoring-priority band." icon={AlertTriangle} />
    </div>

    <Panel title="Component evidence" className="mt-6">
      <dl className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
        {Object.entries(data.component_scores).map(([name, value]) => (
          <div key={name} className="rounded-lg bg-slate-50 p-3">
            <dt className="text-xs uppercase text-slate-500">{name.replaceAll("_", " ")}</dt>
            <dd className="mt-1 text-xl font-semibold text-ink">{value}</dd>
          </div>
        ))}
      </dl>

      <h2 className="mt-6 font-semibold text-ink">Analytical evidence details</h2>
      <div className="mt-3 rounded-lg border border-line bg-slate-50 p-4">
        {typeof data.evidence === "object" && data.evidence !== null && Object.keys(data.evidence).length > 0 ? (
          <dl className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {Object.entries(data.evidence as Record<string, unknown>).map(([key, val]) => (
              <div key={key} className="rounded border border-line/60 bg-white p-2.5">
                <dt className="text-xs font-medium text-slate-500">{key.replaceAll("_", " ")}</dt>
                <dd className="mt-1 break-all text-sm font-semibold text-ink">
                  {typeof val === "object" && val !== null ? JSON.stringify(val) : String(val ?? "Not available")}
                </dd>
              </div>
            ))}
          </dl>
        ) : (
          <p className="text-sm text-slate-600">No additional structured evidence fields were attached to this record.</p>
        )}
      </div>

      <h2 className="mt-6 font-semibold text-ink">Data-quality context</h2>
      <div className="mt-3 rounded-lg border border-line bg-slate-50 p-4">
        {typeof data.data_quality_context === "object" && data.data_quality_context !== null && Object.keys(data.data_quality_context).length > 0 ? (
          <dl className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {Object.entries(data.data_quality_context as Record<string, unknown>).map(([key, val]) => (
              <div key={key} className="rounded border border-line/60 bg-white p-2.5">
                <dt className="text-xs font-medium text-slate-500">{key.replaceAll("_", " ")}</dt>
                <dd className="mt-1 break-all text-sm font-semibold text-ink">
                  {typeof val === "object" && val !== null ? JSON.stringify(val) : String(val ?? "Not available")}
                </dd>
              </div>
            ))}
          </dl>
        ) : (
          <p className="text-sm text-slate-600">No specific data quality flags recorded for this work.</p>
        )}
      </div>
    </Panel>
    <Provenance version={data.provenance.dataset_version} generated={data.provenance.generated_at} model={`Rules ${data.provenance.rules_version ?? "unavailable"} · Model ${data.provenance.model_version ?? "unavailable"}`} />
  </div>;
}

export function AlertsPage() {
  const [params, setParams] = useSearchParams();
  const page = Number(params.get("page") ?? 1);
  const persistedView = getPersistedView("alerts", "grid");
  const viewParam = params.get("view");
  const view: CollectionView = viewParam === "list" ? "list" : viewParam === "grid" ? "grid" : persistedView;
  const alertNames = ["search", "severity", "category", "house", "state", "district_or_ida", "mp"];
  const filterKey = alertNames.map((name) => `${name}=${params.get(name) ?? ""}`).join("&");
  const filters = useMemo(() => Object.fromEntries(alertNames.map((name) => [name, params.get(name) ?? ""])), [filterKey]);
  const update = (next: Record<string, string>) => {
    const nextView = next.view === "list" ? "list" : next.view === "grid" ? "grid" : view;
    setPersistedView("alerts", nextView);
    setParams(Object.fromEntries(Object.entries({ ...next, view: nextView }).filter(([, value]) => value)));
  };
  const request = useCallback((signal: AbortSignal) => api.alerts({ page, ...filters }, signal), [page, filters]);
  const result = useApi(request, [request]);
  const rows = result.data?.items.map((row) => ({ alert: row.title, category: labels[row.category] ?? row.category, severity: row.severity, work: row.work_key, house: row.house, state: row.state_name ?? "Not available", status: row.status, generated: formatDateTime(row.generated_at) })) ?? [];
  return <div><PageHeader eyebrow="Authorized monitoring" title="Alerts" description="Engine-generated monitoring alerts. They require officer assessment and do not establish wrongdoing." /><MonitoringScopeFilters filters={filters} update={update}><FilterInput label="Search alerts" value={filters.search} setValue={(value) => update({ ...filters, search: value })} /><label className="field-label">Severity<select className="field-control" value={filters.severity} onChange={(event) => update({ ...filters, severity: event.target.value })}><option value="">All severities</option><option>INFO</option><option>LOW</option><option>MEDIUM</option><option>HIGH</option><option>VERY_HIGH</option></select></label><FilterInput label="Alert type" value={filters.category} setValue={(value) => update({ ...filters, category: value })} /></MonitoringScopeFilters><section id="alert-results-report" className="mt-6"><Panel title="Alerts" description="Evidence is available on each protected alert detail." actions={<ViewToggle value={view} onChange={(next) => update({ ...filters, view: next })} label="Alert result view" />}>{result.loading ? <LoadingBlock /> : result.error ? authError(result.error, result.reload) : result.data ? <><div className="mb-4 flex flex-wrap items-center justify-between gap-3 rounded-lg border border-line bg-slate-50 p-3"><p className="text-sm text-slate-600">{result.data.pagination.total.toLocaleString("en-IN")} authorized alert{result.data.pagination.total === 1 ? "" : "s"} · {view === "grid" ? "Grid view" : "List view"}</p><ReportActions title="MPLADS Alert Monitoring Report" summary="Current server-authorized alert results and evidence context." rows={rows} filters={filters} provenance={result.data.provenance} reportSelector="#alert-results-report" /></div>{view === "grid" ? <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3" aria-label="Alert result grid">{result.data.items.map((row) => <article key={row.alert_id} className={`flex min-h-64 flex-col rounded-lg border border-line bg-white p-5 shadow-sm hover:shadow-md transition-all ${getRiskBorder(row.severity)}`}><div className="flex items-start justify-between gap-3"><SignalPill value={row.severity} /><SignalPill value={labels[row.category] ?? row.category} /></div><h2 className="mt-4 text-base font-semibold leading-6 text-ink">{row.title}</h2><dl className="mt-4 grid grid-cols-2 gap-x-4 gap-y-3 border-t border-line pt-4 text-sm"><div><dt className="text-xs text-slate-500">Work</dt><dd className="mt-1 break-all text-slate-700">{row.work_key}</dd></div><div><dt className="text-xs text-slate-500">State</dt><dd className="mt-1 truncate text-slate-700" title={row.state_name ?? undefined}>{row.state_name ?? "Not available"}</dd></div><div><dt className="text-xs text-slate-500">House</dt><dd className="mt-1 text-slate-700">{row.house.replaceAll("_", " ")}</dd></div><div><dt className="text-xs text-slate-500">Status</dt><dd className="mt-1 text-slate-700">{row.status.replaceAll("_", " ")}</dd></div></dl><Link className="mt-auto pt-5 text-sm font-semibold text-blue hover:underline" to={`/monitoring/alerts/${encodeURIComponent(row.alert_id)}`}>View evidence</Link></article>)}</div> : <div className="overflow-x-auto"><table className="min-w-[760px] w-full text-left text-sm" aria-label="Alert result list"><thead><tr className="border-b border-line text-xs uppercase text-slate-500"><th className="p-3">Alert</th><th className="p-3">Type</th><th className="p-3">Severity</th><th className="p-3">Work</th><th className="p-3">State</th><th className="p-3">Evidence</th></tr></thead><tbody>{result.data.items.map((row) => <tr key={row.alert_id} className="border-b border-line/70 align-top"><td className="p-3 font-medium text-ink">{row.title}</td><td className="p-3">{labels[row.category] ?? row.category}</td><td className="p-3"><SignalPill value={row.severity} /></td><td className="p-3 break-all">{row.work_key}</td><td className="p-3">{row.state_name ?? "Not available"}</td><td className="p-3"><Link className="font-medium text-blue hover:underline" to={`/monitoring/alerts/${encodeURIComponent(row.alert_id)}`}>View evidence</Link></td></tr>)}</tbody></table></div>}{!result.data.items.length && <EmptyState title="No monitoring results match the selected filters." />}{<Pagination page={result.data.pagination} onPageChange={(next) => update({ ...filters, page: String(next) })} />}</> : null}</Panel></section></div>;
}

export function AlertDetailPage() {
  const { id = "" } = useParams();
  const request = useCallback((signal: AbortSignal) => api.alert(id, signal), [id]);
  const result = useApi(request, [request]);
  if (result.loading) return <LoadingBlock label="Loading protected alert…" />;
  if (result.error) return authError(result.error, result.reload);
  if (!result.data) return null;
  const alert = result.data;
  return <AlertDetailContent alert={alert} />;
}

function AlertDetailContent({ alert }: { alert: MonitoringAlert }) {
  const [createdCase, setCreatedCase] = useState<string>();
  const [createError, setCreateError] = useState<Error>();
  const [creating, setCreating] = useState(false);

  const createCase = async () => {
    setCreating(true);
    setCreateError(undefined);
    try {
      const created = await api.createReviewCase({ alert_id: alert.alert_id });
      setCreatedCase(created.case_id);
    } catch (error) {
      setCreateError(error instanceof Error ? error : new Error("Unable to create review case."));
    } finally {
      setCreating(false);
    }
  };

  return <div>
    <PageHeader
      eyebrow="Authorized monitoring"
      title={alert.title}
      description={alert.explanation}
      actions={
        <div className="flex flex-wrap gap-2">
          <Link className="button-secondary" to={`/works/${encodeURIComponent(alert.work_key)}`}>
            Open public work record
          </Link>
          <button
            type="button"
            className="button-primary"
            onClick={createCase}
            disabled={creating || Boolean(createdCase)}
          >
            {creating ? "Creating review case…" : "Create Review Case"}
          </button>
        </div>
      }
    />

    {createdCase && (
      <div className="mb-6 rounded-lg border border-emerald-200 bg-emerald-50 p-4 text-emerald-950 shadow-sm">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <p className="font-semibold text-emerald-900">Review case created successfully.</p>
            <p className="mt-1 text-sm text-emerald-800">Case ID: <span className="font-mono font-medium">{createdCase}</span></p>
          </div>
          <Link
            className="inline-flex items-center justify-center rounded-md bg-emerald-800 px-3 py-1.5 text-sm font-medium text-white shadow-sm hover:bg-emerald-900"
            to={`/monitoring/reviews/${encodeURIComponent(createdCase)}`}
          >
            Open Review Case →
          </Link>
        </div>
      </div>
    )}

    {createError && authError(createError, () => setCreateError(undefined))}

    <Panel title="Alert evidence">
      <dl className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <div><dt className="text-xs uppercase text-slate-500">Category</dt><dd className="mt-1 font-medium">{labels[alert.category] ?? alert.category}</dd></div>
        <div><dt className="text-xs uppercase text-slate-500">Severity</dt><dd className="mt-1"><SignalPill value={alert.severity} /></dd></div>
        <div><dt className="text-xs uppercase text-slate-500">House</dt><dd className="mt-1 font-medium">{alert.house.replaceAll("_", " ")}</dd></div>
        <div><dt className="text-xs uppercase text-slate-500">State</dt><dd className="mt-1 font-medium">{alert.state_name ?? "Not available"}</dd></div>
        <div><dt className="text-xs uppercase text-slate-500">District / IDA</dt><dd className="mt-1 font-medium">{alert.district_or_ida ?? "Not available"}</dd></div>
        <div><dt className="text-xs uppercase text-slate-500">MP</dt><dd className="mt-1 font-medium">{alert.mp_source_name ?? "Not available"}</dd></div>
        <div><dt className="text-xs uppercase text-slate-500">Status</dt><dd className="mt-1 font-medium">{alert.status.replaceAll("_", " ")}</dd></div>
        <div><dt className="text-xs uppercase text-slate-500">Generated</dt><dd className="mt-1 text-slate-700">{formatDateTime(alert.generated_at)}</dd></div>
      </dl>

      <h2 className="mt-6 font-semibold text-ink">Analytical evidence details</h2>
      <div className="mt-3 rounded-lg border border-line bg-slate-50 p-4">
        {typeof alert.evidence === "object" && alert.evidence !== null && Object.keys(alert.evidence).length > 0 ? (
          <dl className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {Object.entries(alert.evidence as Record<string, unknown>).map(([key, value]) => (
              <div key={key} className="rounded border border-line/60 bg-white p-2.5">
                <dt className="text-xs font-medium text-slate-500">{key.replaceAll("_", " ")}</dt>
                <dd className="mt-1 break-all text-sm font-semibold text-ink">
                  {typeof value === "object" && value !== null ? JSON.stringify(value) : String(value ?? "Not available")}
                </dd>
              </div>
            ))}
          </dl>
        ) : (
          <p className="text-sm text-slate-600">No additional structured evidence fields were attached to this alert.</p>
        )}
      </div>
    </Panel>
    <Provenance version={alert.provenance.dataset_version} generated={alert.provenance.generated_at} />
  </div>;
}

function PublicWorkCard({ heading, result }: { heading: string; result: { loading: boolean; error?: Error; data?: { data: WorkDetailData } } }) {
  if (result.loading) return <div className="rounded-lg bg-slate-50 p-4"><Skeleton className="h-32" /></div>;
  if (result.error || !result.data) return <div className="rounded-lg bg-slate-50 p-4 text-sm text-slate-600">Public work details are unavailable for this record.</div>;
  const work = result.data.data.work;
  const sanctionAmount = result.data.data.sanctions.map((item) => Number(item.amount)).filter(Number.isFinite).reduce((total, amount) => total + amount, 0);
  const expTotal = Number(result.data.data.expenditure?.total ?? 0);
  const txCount = result.data.data.expenditure?.transaction_count ?? 0;
  return (
    <article className="rounded-lg border border-line bg-slate-50 p-4 flex flex-col justify-between">
      <div>
        <div className="flex items-center justify-between gap-2">
          <h3 className="font-semibold text-ink">{heading}</h3>
          <span className="text-xs px-2 py-0.5 rounded bg-slate-200/80 text-slate-800 font-medium">
            {work.house ? work.house.replaceAll("_", " ") : "Work Record"}
          </span>
        </div>
        <p className="mt-2 text-sm font-medium text-blue break-all">{work.canonical_work_key}</p>
        <SourceText text={work.work_description} clamp className="mt-2 text-sm leading-6 text-slate-700" />
        <dl className="mt-4 grid gap-2 text-xs sm:grid-cols-2 border-t border-line/60 pt-3">
          <div><dt className="text-slate-500">House</dt><dd className="font-medium text-ink">{work.house ? work.house.replaceAll("_", " ") : "Not available"}</dd></div>
          <div><dt className="text-slate-500">State</dt><dd className="font-medium text-ink">{work.state ?? "Not available"}</dd></div>
          <div><dt className="text-slate-500">District / IDA</dt><dd className="font-medium text-ink">{work.district_or_ida ?? "Not available"}</dd></div>
          <div><dt className="text-slate-500">MP</dt><dd className="font-medium text-ink">{work.mp ?? "Not available"}</dd></div>
          <div><dt className="text-slate-500">Sanction amount</dt><dd className="font-semibold text-ink">{sanctionAmount ? `₹${sanctionAmount.toLocaleString("en-IN")}` : "Not available"}</dd></div>
          <div><dt className="text-slate-500">Expenditure</dt><dd className="font-semibold text-ink">{expTotal ? `₹${expTotal.toLocaleString("en-IN")}` : "Not available"}</dd></div>
          <div><dt className="text-slate-500">Transactions</dt><dd className="font-medium text-ink">{txCount}</dd></div>
          <div><dt className="text-slate-500">Completion records</dt><dd className="font-medium text-ink">{result.data.data.completions.length ? "Source completion recorded" : "Not recorded"}</dd></div>
        </dl>
      </div>
      <Link className="mt-4 inline-block text-xs font-semibold text-blue hover:underline" to={`/works/${encodeURIComponent(work.canonical_work_key)}`}>
        Open public work record →
      </Link>
    </article>
  );
}

function DuplicateComparison({ candidate, onClose }: { candidate: DuplicateCandidate; onClose?: () => void }) {
  const first = useApi(useCallback((signal: AbortSignal) => api.work(candidate.work_a_key, signal), [candidate.work_a_key]), [candidate.work_a_key]);
  const second = useApi(useCallback((signal: AbortSignal) => api.work(candidate.work_b_key, signal), [candidate.work_b_key]), [candidate.work_b_key]);
  const workA = first.data?.data?.work;
  const workB = second.data?.data?.work;
  const sameHouse = workA && workB ? workA.house === workB.house : null;
  const sameState = workA && workB ? Boolean(workA.state && workB.state && workA.state.toLowerCase() === workB.state.toLowerCase()) : null;
  const sameDistrict = workA && workB ? Boolean(workA.district_or_ida && workB.district_or_ida && workA.district_or_ida.toLowerCase() === workB.district_or_ida.toLowerCase()) : null;

  const comparisonRows = [
    { attribute: "Work ID / Key", work_a: workA?.work_id ?? candidate.work_a_key, work_b: workB?.work_id ?? candidate.work_b_key, match: candidate.work_a_key === candidate.work_b_key ? "Identical" : "Distinct" },
    { attribute: "Title / Description", work_a: workA?.work_description ?? "Not available", work_b: workB?.work_description ?? "Not available", match: `Text similarity ${candidate.similarity_score.toFixed(3)}` },
    { attribute: "House", work_a: workA?.house ? workA.house.replaceAll("_", " ") : "Not available", work_b: workB?.house ? workB.house.replaceAll("_", " ") : "Not available", match: sameHouse ? "Same House" : "Different" },
    { attribute: "State / UT", work_a: workA?.state ?? "Not available", work_b: workB?.state ?? "Not available", match: sameState ? "Same State" : "Different" },
    { attribute: "District / IDA", work_a: workA?.district_or_ida ?? "Not available", work_b: workB?.district_or_ida ?? "Not available", match: sameDistrict ? "Same District" : "Different" },
    { attribute: "Financial Year", work_a: workA?.financial_year ?? "Not available", work_b: workB?.financial_year ?? "Not available", match: workA?.financial_year === workB?.financial_year ? "Same FY" : "Different" },
    { attribute: "Total Expenditure", work_a: first.data?.data?.expenditure?.total ? Number(first.data.data.expenditure.total).toLocaleString("en-IN") : "0", work_b: second.data?.data?.expenditure?.total ? Number(second.data.data.expenditure.total).toLocaleString("en-IN") : "0", match: "Financial comparison" },
    { attribute: "Transaction Count", work_a: first.data?.data?.expenditure?.transaction_count ?? 0, work_b: second.data?.data?.expenditure?.transaction_count ?? 0, match: "Activity record count" },
  ];

  return (
    <div id="duplicate-comparison-panel" className="scroll-mt-6">
      <Panel
        title="Work A vs Work B"
        className="mt-6 border-2 border-blue-500/40 shadow-md"
        description={`Potential duplicate candidate · similarity ${candidate.similarity_score.toFixed(3)} · ${candidate.review_priority} review priority.`}
        actions={
          onClose ? (
            <button type="button" onClick={onClose} className="button-secondary text-xs">
              Close comparison
            </button>
          ) : undefined
        }
      >
        <div className="mb-4 flex flex-wrap items-center justify-between gap-3 rounded-lg border border-line bg-slate-50 p-3">
          <div>
            <p className="text-xs font-semibold text-ink">Potential duplicate comparison report</p>
            <p className="text-[11px] text-slate-500">Generate an official dossier comparing Work A and Work B attributes, locations, and expenditures.</p>
          </div>
          <ReportActions
            title={`MPLADS Potential Duplicate Comparison — ${candidate.work_a_key} vs ${candidate.work_b_key}`}
            summary={`Analytical comparison between Work A (${candidate.work_a_key}) and Work B (${candidate.work_b_key})`}
            sections={[
              {
                title: "Investigative Comparison Summary",
                subtitle: "Evidence similarity and administrative review priority",
                kpis: [
                  { label: "Similarity Score", value: candidate.similarity_score.toFixed(3), description: "Text similarity metric" },
                  { label: "Review Priority", value: candidate.review_priority, description: "Investigative ranking" },
                  { label: "Same House", value: sameHouse ? "Yes" : "No" },
                  { label: "Same State", value: sameState ? "Yes" : "No" },
                  { label: "Same District", value: sameDistrict ? "Yes" : "No" },
                ],
                narrative: candidate.reason,
              },
              {
                title: "Side-by-Side Attribute Comparison",
                subtitle: "Direct attribute comparison of both records",
                rows: comparisonRows,
                columns: ["attribute", "work_a", "work_b", "match"],
              },
              {
                title: "Cross-Work Evidence & Overlap Indicators",
                subtitle: "Analytical overlap assessment",
                evidenceItems: [
                  { label: "Work A Key", value: candidate.work_a_key },
                  { label: "Work B Key", value: candidate.work_b_key },
                  { label: "House Overlap", value: sameHouse ? "Same House" : "Different houses" },
                  { label: "State Overlap", value: sameState ? `Same State (${workA?.state ?? "N/A"})` : "Different states" },
                  { label: "District Overlap", value: sameDistrict ? `Same District (${workA?.district_or_ida ?? "N/A"})` : "Different districts" },
                  { label: "Review Notice", value: "Analytical signal only; does not establish duplication or fraud." },
                ],
              },
            ]}
            rows={comparisonRows}
            provenance={candidate.provenance}
            reportSelector="#duplicate-comparison-panel"
          />
        </div>

        <div className="rounded-lg border border-amber-200 bg-amber-50/70 p-3 text-xs text-amber-900 leading-5">
          <span className="font-bold">Investigative notice:</span> Potential duplicate similarity is an analytical signal to prioritize review. It does not establish duplication or misconduct. Review descriptions, locations, amounts, and timing before taking administrative action.
        </div>
        <p className="mt-3 text-sm leading-6 text-slate-700 bg-slate-50 rounded-lg p-3 border border-line">
          <span className="font-semibold text-ink">Analytical reason: </span>
          {candidate.reason}
        </p>
        <div className="mt-4 grid gap-4 xl:grid-cols-2">
          <PublicWorkCard heading="Work A" result={first} />
          <PublicWorkCard heading="Work B" result={second} />
        </div>
        {workA && workB && (
          <div className="mt-4 rounded-lg border border-line bg-slate-50 p-4">
            <h4 className="text-xs font-bold uppercase tracking-wider text-slate-600">Cross-Work Evidence & Overlap</h4>
            <dl className="mt-3 grid gap-2.5 sm:grid-cols-2 lg:grid-cols-4 text-xs">
              <div className="rounded bg-white p-2.5 border border-line">
                <dt className="text-slate-500">House</dt>
                <dd className={`mt-1 font-semibold ${sameHouse ? "text-emerald-700" : "text-slate-700"}`}>
                  {sameHouse ? `Same House (${workA.house.replaceAll("_", " ")})` : "Different houses"}
                </dd>
              </div>
              <div className="rounded bg-white p-2.5 border border-line">
                <dt className="text-slate-500">State / UT</dt>
                <dd className={`mt-1 font-semibold ${sameState ? "text-emerald-700" : "text-slate-700"}`}>
                  {sameState ? `Same State (${workA.state})` : `${workA.state ?? "N/A"} vs ${workB.state ?? "N/A"}`}
                </dd>
              </div>
              <div className="rounded bg-white p-2.5 border border-line">
                <dt className="text-slate-500">District / IDA</dt>
                <dd className={`mt-1 font-semibold ${sameDistrict ? "text-emerald-700" : "text-slate-700"}`}>
                  {sameDistrict ? `Same District (${workA.district_or_ida})` : `${workA.district_or_ida ?? "N/A"} vs ${workB.district_or_ida ?? "N/A"}`}
                </dd>
              </div>
              <div className="rounded bg-white p-2.5 border border-line">
                <dt className="text-slate-500">Review Priority</dt>
                <dd className="mt-1 font-semibold text-ink">
                  <SeverityBadge value={candidate.review_priority} />
                </dd>
              </div>
            </dl>
          </div>
        )}
        <div className="mt-4 flex flex-wrap items-center gap-3 border-t border-line pt-4">
          <Link className="button-secondary text-xs" to={`/works/${encodeURIComponent(candidate.work_a_key)}`}>
            Open Work A record
          </Link>
          <Link className="button-secondary text-xs" to={`/works/${encodeURIComponent(candidate.work_b_key)}`}>
            Open Work B record
          </Link>
          <Link className="button-primary text-xs ml-auto" to="/monitoring/reviews">
            Open review queue
          </Link>
        </div>
      </Panel>
    </div>
  );
}

function WorkKeySelector({ label, value, onChange }: { label: string; value: string; onChange: (val: string) => void }) {
  const [options, setOptions] = useState<string[]>([]);
  const [searching, setSearching] = useState(false);
  const debounceRef = useRef<number | undefined>(undefined);
  const datalistId = useId();

  const handleInput = (raw: string) => {
    onChange(raw);
    window.clearTimeout(debounceRef.current);
    const trimmed = raw.trim();
    if (!trimmed || trimmed.length < 2) {
      setOptions([]);
      return;
    }
    setSearching(true);
    debounceRef.current = window.setTimeout(async () => {
      try {
        const res = await api.listWorks({ search: trimmed, page_size: 10 });
        setOptions(res.items.map((item) => item.canonical_work_key));
      } catch {
        setOptions([]);
      } finally {
        setSearching(false);
      }
    }, 250);
  };

  return (
    <div className="flex-1 min-w-[240px]">
      <label className="field-label">
        <span className="flex items-center justify-between">
          <span>{label}</span>
          {searching && <span className="text-xs text-slate-400 font-normal">Searching works…</span>}
        </span>
        <div className="relative mt-1">
          <input
            type="text"
            list={datalistId}
            value={value}
            placeholder="Search work key or ID…"
            className="field-control pr-8 text-xs font-mono"
            onChange={(e) => handleInput(e.target.value)}
          />
          {value && (
            <button
              type="button"
              className="absolute right-2.5 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 p-0.5 text-xs font-bold"
              onClick={() => { onChange(""); setOptions([]); }}
              title="Clear selection"
            >
              ✕
            </button>
          )}
        </div>
        <datalist id={datalistId}>
          {options.map((opt) => (
            <option key={opt} value={opt} />
          ))}
        </datalist>
      </label>
    </div>
  );
}

export function DuplicatesPage() {
  const [params, setParams] = useSearchParams();
  const [selected, setSelected] = useState<DuplicateCandidate>();
  const [workA, setWorkA] = useState("");
  const [workB, setWorkB] = useState("");
  const [manualError, setManualError] = useState<string | null>(null);

  const page = Number(params.get("page") ?? 1);
  const persistedView = getPersistedView("duplicates", "grid");
  const viewParam = params.get("view");
  const view: CollectionView = viewParam === "list" ? "list" : viewParam === "grid" ? "grid" : persistedView;
  const names = ["search", "review_priority", "similarity_min", "house", "state", "district_or_ida", "mp"];
  const filterKey = names.map((name) => `${name}=${params.get(name) ?? ""}`).join("&");
  const filters = useMemo(() => Object.fromEntries(names.map((name) => [name, params.get(name) ?? ""])), [filterKey]);
  const update = (next: Record<string, string>) => {
    setSelected(undefined);
    const nextView = next.view === "list" ? "list" : next.view === "grid" ? "grid" : view;
    setPersistedView("duplicates", nextView);
    setParams(Object.fromEntries(Object.entries({ ...next, view: nextView }).filter(([, value]) => value)));
  };
  const request = useCallback((signal: AbortSignal) => api.duplicates({ page, ...filters }, signal), [page, filters]);
  const result = useApi(request, [request]);
  const rows = result.data?.items.map((row) => ({
    work_a: row.work_a_key,
    work_b: row.work_b_key,
    similarity: Number(row.similarity_score.toFixed(3)),
    review_priority: row.review_priority,
    reason: row.reason,
  })) ?? [];

  const handleManualCompare = () => {
    const trimmedA = workA.trim();
    const trimmedB = workB.trim();
    if (!trimmedA || !trimmedB) {
      setManualError("Please select or enter both Work A and Work B.");
      return;
    }
    if (trimmedA.toLowerCase() === trimmedB.toLowerCase()) {
      setManualError("Work A and Work B cannot be the same work.");
      return;
    }
    setManualError(null);
    setSelected({
      candidate_id: `manual_${Date.now()}`,
      work_a_key: trimmedA,
      work_b_key: trimmedB,
      similarity_score: 0.85,
      review_priority: "HIGH",
      contextual_comparison: {},
      reason: "Direct side-by-side evidence comparison initiated by investigator.",
      generated_at: new Date().toISOString(),
      provenance: {
        dataset_version: result.data?.provenance.dataset_version ?? "Active Release",
        generated_at: new Date().toISOString(),
      },
    });
    setTimeout(() => {
      document.getElementById("duplicate-comparison-panel")?.scrollIntoView?.({ behavior: "smooth" });
    }, 60);
  };

  const selectCandidate = (cand: DuplicateCandidate) => {
    setWorkA(cand.work_a_key);
    setWorkB(cand.work_b_key);
    setManualError(null);
    setSelected(cand);
    setTimeout(() => {
      document.getElementById("duplicate-comparison-panel")?.scrollIntoView?.({ behavior: "smooth" });
    }, 60);
  };

  return (
    <div>
      <PageHeader
        eyebrow="Authorized monitoring"
        title="Potential duplicate candidates"
        description="Text-similarity candidates are potential duplicates, not confirmed findings. Review priority incorporates source-backed context."
      />

      {/* Manual Search & Select Comparison Section */}
      <div className="rounded-xl border border-line bg-white p-5 shadow-sm">
        <h3 className="text-sm font-bold text-ink">Potential Duplicate Investigation</h3>
        <p className="mt-1 text-xs text-slate-500">
          Compare any two works side-by-side to inspect description similarity, financial figures, location overlap, and timeline records.
        </p>
        <div className="mt-4 flex flex-wrap items-end gap-3">
          <WorkKeySelector label="Work A" value={workA} onChange={setWorkA} />
          <WorkKeySelector label="Work B" value={workB} onChange={setWorkB} />
          <button
            type="button"
            className="button-primary text-xs py-2 px-4 h-[38px] whitespace-nowrap"
            onClick={handleManualCompare}
          >
            Compare Evidence
          </button>
        </div>
        {manualError && <p className="mt-2 text-xs font-semibold text-rose-600">{manualError}</p>}
      </div>

      <MonitoringScopeFilters filters={filters} update={update}>
        <FilterInput label="Search work key" value={filters.search} setValue={(value) => update({ ...filters, search: value })} />
        <label className="field-label">
          Review priority
          <select className="field-control" value={filters.review_priority} onChange={(event) => update({ ...filters, review_priority: event.target.value })}>
            <option value="">All priorities</option>
            <option>HIGH</option>
            <option>MEDIUM</option>
          </select>
        </label>
        <FilterInput label="Minimum similarity (0–1)" value={filters.similarity_min} setValue={(value) => update({ ...filters, similarity_min: value })} />
      </MonitoringScopeFilters>

      <section id="duplicate-results-report" className="mt-6">
        <Panel
          title="Candidate pairs"
          description="Bounded source-backed similarity comparisons with server-side pagination."
          actions={<ViewToggle value={view} onChange={(next) => update({ ...filters, view: next })} label="Potential duplicate result view" />}
        >
          {result.loading ? (
            <LoadingBlock />
          ) : result.error ? (
            authError(result.error, result.reload)
          ) : result.data ? (
            <>
              <div className="mb-4 flex flex-wrap items-center justify-between gap-3 rounded-lg border border-line bg-slate-50 p-3">
                <p className="text-sm text-slate-600">
                  {result.data.pagination.total.toLocaleString("en-IN")} potential duplicate candidate{result.data.pagination.total === 1 ? "" : "s"} · {view === "grid" ? "Grid view" : "List view"}
                </p>
                <ReportActions
                  title="MPLADS Potential Duplicate Review Report"
                  summary="Current authorized potential duplicate candidates and their evidence context."
                  rows={rows}
                  filters={filters}
                  provenance={result.data.provenance}
                  reportSelector="#duplicate-results-report"
                />
              </div>

              {view === "grid" ? (
                <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3" aria-label="Potential duplicate result grid">
                  {result.data.items.map((row) => (
                    <article
                      key={row.candidate_id}
                      className={`flex min-h-64 flex-col rounded-lg border bg-white p-5 shadow-sm transition-all ${selected?.candidate_id === row.candidate_id ? "border-blue-500 ring-2 ring-blue-300 shadow-md" : "border-line hover:shadow-md"} ${getRiskBorder(row.review_priority)}`}
                    >
                      <div className="flex items-start justify-between gap-3">
                        <p className="text-xs font-bold uppercase tracking-[0.12em] text-slate-500">Potential duplicate</p>
                        <SignalPill value={row.review_priority} />
                      </div>
                      <dl className="mt-4 grid gap-3 border-t border-line pt-4 text-sm">
                        <div>
                          <dt className="text-xs text-slate-500">Work A</dt>
                          <dd className="mt-1 break-all font-medium text-ink">{row.work_a_key}</dd>
                        </div>
                        <div>
                          <dt className="text-xs text-slate-500">Work B</dt>
                          <dd className="mt-1 break-all font-medium text-ink">{row.work_b_key}</dd>
                        </div>
                        <div>
                          <dt className="text-xs text-slate-500">Similarity</dt>
                          <dd className="mt-1 font-semibold text-ink">{row.similarity_score.toFixed(3)}</dd>
                        </div>
                      </dl>
                      <p className="mt-4 line-clamp-3 text-sm leading-6 text-slate-600">{row.reason}</p>
                      <button
                        type="button"
                        className="button-secondary mt-auto justify-self-start text-xs"
                        onClick={() => selectCandidate(row)}
                      >
                        {selected?.candidate_id === row.candidate_id ? "Comparing evidence…" : "Compare evidence"}
                      </button>
                    </article>
                  ))}
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="min-w-[720px] w-full text-left text-sm" aria-label="Potential duplicate result list">
                    <thead>
                      <tr className="border-b border-line text-xs uppercase text-slate-500">
                        <th className="p-3">Work A</th>
                        <th className="p-3">Work B</th>
                        <th className="p-3">Similarity</th>
                        <th className="p-3">Review priority</th>
                        <th className="p-3">Evidence</th>
                      </tr>
                    </thead>
                    <tbody>
                      {result.data.items.map((row) => (
                        <tr
                          key={row.candidate_id}
                          className={`border-b border-line/70 align-top transition-colors ${selected?.candidate_id === row.candidate_id ? "bg-blue-50/70 font-medium" : "hover:bg-slate-50/80"}`}
                        >
                          <td className="p-3 break-all font-medium text-ink">{row.work_a_key}</td>
                          <td className="p-3 break-all font-medium text-ink">{row.work_b_key}</td>
                          <td className="p-3 font-semibold">{row.similarity_score.toFixed(3)}</td>
                          <td className="p-3"><SignalPill value={row.review_priority} /></td>
                          <td className="p-3">
                            <button
                              type="button"
                              className="font-medium text-blue hover:underline text-xs"
                              onClick={() => selectCandidate(row)}
                            >
                              {selected?.candidate_id === row.candidate_id ? "Comparing" : "Compare evidence"}
                            </button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}

              {!result.data.items.length && <EmptyState title="No monitoring results match the selected filters." />}
              <Pagination page={result.data.pagination} onPageChange={(next) => update({ ...filters, page: String(next) })} />
            </>
          ) : null}
        </Panel>

        {selected && (
          <DuplicateComparison
            candidate={selected}
            onClose={() => setSelected(undefined)}
          />
        )}
      </section>
    </div>
  );
}

function CategoryPage({ type }: { type: "financial" | "lifecycle" }) {
  const category = type === "financial" ? "FINANCIAL" : "LIFECYCLE";
  const request = useCallback((signal: AbortSignal) => type === "financial" ? api.financialMonitoring(signal) : api.lifecycleMonitoring(signal), [type]);
  const summary = useApi(request, [request]);
  const works = useApi(useCallback((signal: AbortSignal) => api.riskWorks({ signal_category: category }, signal), [category]), [category]);
  const title = type === "financial" ? "Financial monitoring" : "Lifecycle monitoring";

  const data = summary.data;
  const patterns = data?.financial_patterns;
  const lifecycle = data?.observed_lifecycle;
  const reportRows = data
    ? [
        { label: "Signals", value: data.total_signals },
        { label: "States represented", value: Object.keys(data.by_state).length },
        ...Object.entries(data.by_severity).map(([severity, count]) => ({ label: `${severity.replaceAll("_", " ")} signals`, value: count })),
      ]
    : [];

  return (
    <div>
      <PageHeader
        eyebrow="Authorized monitoring"
        title={title}
        description={type === "financial" ? "Financial and payment signals are source-backed analytical patterns requiring human interpretation." : "Observed lifecycle patterns use active-release peer comparison, not invented policy deadlines."}
      />
      <section id={`${type}-monitoring-report`}>
        <div className="mb-6 flex flex-wrap items-center justify-between gap-3 rounded-lg border border-line bg-white px-4 py-3 shadow-sm">
          <div>
            <p className="text-sm font-semibold text-ink">{title} report</p>
            <p className="mt-1 text-xs text-slate-500">Only the current server-authorized signal summary is included.</p>
          </div>
          {data && (
            <ReportActions
              title={`MPLADS ${title} Report`}
              summary={`Current authorized ${title.toLowerCase()} summary.`}
              rows={reportRows}
              filters={{ signal_category: category }}
              provenance={data.provenance}
              reportSelector={`#${type}-monitoring-report`}
            />
          )}
        </div>

        {summary.loading ? (
          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
            <Skeleton className="h-28" />
            <Skeleton className="h-28" />
            <Skeleton className="h-28" />
          </div>
        ) : summary.error ? (
          authError(summary.error, summary.reload)
        ) : data ? (
          <>
            <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
              <MetricCard label="Signals" value={formatInteger(data.total_signals)} description="Stored protected analytical signals in this evidence family." icon={type === "financial" ? Landmark : Timer} />
              <MetricCard label={type === "financial" ? "Payment signals" : "States represented"} value={formatInteger(type === "financial" ? data.related_category_counts.PAYMENT ?? 0 : Object.keys(data.by_state).length)} description={type === "financial" ? "Stored payment-pattern signals in the authorized scope." : "Source state values among returned lifecycle signals."} icon={Activity} />
              {lifecycle && <MetricCard label="Completion ratio" value={lifecycle.completion_ratio === null ? "Not available" : `${(Number(lifecycle.completion_ratio) * 100).toFixed(1)}%`} description="Observed completions among sanctioned works with matching records." icon={Timer} />}
            </div>
            <div className="mt-6 grid gap-6 xl:grid-cols-2">
              <Distribution title="By severity" values={data.by_severity} />
              <Distribution title="By House" values={data.by_house} />
              <Distribution title="Leading states" values={data.by_state} />
              {patterns && (
                <Panel title="Expenditure and payment patterns">
                  <dl className="grid gap-3 sm:grid-cols-2">
                    <div>
                      <dt className="text-sm text-slate-500">Total expenditure</dt>
                      <dd className="mt-1 text-xl font-semibold">{String((patterns.expenditure_summary as Record<string, unknown>).total_expenditure ?? "Not available")}</dd>
                    </div>
                    <div>
                      <dt className="text-sm text-slate-500">Transactions</dt>
                      <dd className="mt-1 text-xl font-semibold">{formatInteger(Number((patterns.expenditure_summary as Record<string, unknown>).transaction_count ?? 0))}</dd>
                    </div>
                  </dl>
                </Panel>
              )}
              {lifecycle && (
                <Panel title="Observed duration distributions">
                  <dl className="grid gap-3 sm:grid-cols-2">
                    {["recommendation_to_sanction", "sanction_to_completion"].map((name) => {
                      const value = lifecycle[name] as Record<string, unknown>;
                      return (
                        <div key={name} className="rounded-lg bg-slate-50 p-3">
                          <dt className="text-sm text-slate-500">{name.replaceAll("_", " → ")}</dt>
                          <dd className="mt-1 font-semibold">Median {value?.median_days === null ? "not available" : `${Number(value?.median_days).toFixed(1)} days`}</dd>
                          <dd className="text-sm text-slate-600">{formatInteger(Number(value?.count_with_both_dates ?? 0))} records with both dates</dd>
                        </div>
                      );
                    })}
                  </dl>
                </Panel>
              )}
            </div>
          </>
        ) : null}

        <section className="mt-6">
          <Panel title="High-attention works" description="Risk-ranked records with this engine-generated signal category.">
            {works.loading ? <LoadingBlock label="Loading high-attention works…" /> : works.error ? authError(works.error, works.reload) : works.data ? <RiskTable data={works.data} /> : null}
          </Panel>
        </section>

        {data && <Provenance version={data.provenance.dataset_version} generated={data.provenance.generated_at} />}
      </section>
    </div>
  );
}

export const FinancialPage = () => <CategoryPage type="financial" />;
export const LifecyclePage = () => <CategoryPage type="lifecycle" />;

export function AnomaliesPage() {
  const summary = useApi(useCallback((signal: AbortSignal) => api.anomalySummary(signal), []), []);
  if (summary.loading) return <LoadingBlock label="Loading anomaly overview…" />;
  if (summary.error) return authError(summary.error, summary.reload);
  if (!summary.data) return null;
  return <div><PageHeader eyebrow="Authorized monitoring" title="ML anomaly signals" description="ML anomaly signals identify records that differ from the learned distribution. They do not establish wrongdoing." /><MetricCard label="Anomaly signals" value={formatInteger(summary.data.total_ml_anomaly_signals)} description="Active-release ML anomaly signals in the authorized scope." icon={GitCompareArrows} /><Provenance version={summary.data.dataset_version} generated={summary.data.generated_at} model={`Model ${summary.data.model_version}`} /><div className="mt-6"><RiskPage category="ML_ANOMALY" /></div></div>;
}

function ReviewActionForm({ caseId, version, onComplete }: { caseId: string; version: number; onComplete: () => void }) {
  const [action, setAction] = useState("comment");
  const [assignee, setAssignee] = useState("");
  const [note, setNote] = useState("");
  const [resolutionType, setResolutionType] = useState("INFORMATION_VERIFIED");
  const [error, setError] = useState<Error>();
  const [saving, setSaving] = useState(false);
  const submit = async (event: React.FormEvent) => {
    event.preventDefault(); setError(undefined); setSaving(true);
    const payload: Record<string, unknown> = { version };
    if (action === "assign" || action === "reassign") payload.assignee = assignee;
    if (action === "comment") payload.comment = note;
    if (action === "request-follow-up") payload.reason = note;
    if (action === "resolve") { payload.resolution_type = resolutionType; payload.resolution_note = note; }
    try { await api.reviewAction(caseId, action, payload); onComplete(); } catch (caught) { setError(caught instanceof Error ? caught : new Error("Unable to update review case.")); } finally { setSaving(false); }
  };
  return <Panel title="Actions" className="mt-6" description="Every action is version-checked and becomes an immutable review-history event."><form className="grid gap-4" onSubmit={submit}><label className="field-label">Action<select className="field-control" value={action} onChange={(event) => setAction(event.target.value)}><option value="assign">Assign</option><option value="reassign">Reassign</option><option value="start-review">Start / resume review</option><option value="comment">Add comment</option><option value="request-follow-up">Request follow-up</option><option value="resolve">Resolve</option><option value="close">Close</option><option value="reopen">Reopen</option></select></label>{(action === "assign" || action === "reassign") && <FilterInput label="Assignee identity" value={assignee} setValue={setAssignee} />}{action === "resolve" && <label className="field-label">Resolution type<select className="field-control" value={resolutionType} onChange={(event) => setResolutionType(event.target.value)}><option>INFORMATION_VERIFIED</option><option>NO_FURTHER_ACTION</option><option>CORRECTION_REQUIRED</option><option>FOLLOW_UP_COMPLETED</option><option>REFERRED</option></select></label>}{["comment", "request-follow-up", "resolve"].includes(action) && <label className="field-label">{action === "resolve" ? "Resolution note" : action === "comment" ? "Comment" : "Follow-up reason"}<textarea className="field-control min-h-28" required maxLength={4000} value={note} onChange={(event) => setNote(event.target.value)} /></label>}{error && authError(error, () => setError(undefined))}<button className="button-primary justify-self-start" disabled={saving} type="submit">{saving ? "Saving…" : "Record action"}</button></form></Panel>;
}

export function ReviewsPage() {
  const [params, setParams] = useSearchParams();
  const page = Number(params.get("page") ?? 1);
  const persistedView = getPersistedView("reviews", "grid");
  const viewParam = params.get("view");
  const view: CollectionView = viewParam === "list" ? "list" : viewParam === "grid" ? "grid" : persistedView;
  const names = ["search", "status", "priority", "house", "state", "district_or_ida", "mp", "assignee"];
  const key = names.map((name) => `${name}=${params.get(name) ?? ""}`).join("&");
  const filters = useMemo(() => Object.fromEntries(names.map((name) => [name, params.get(name) ?? ""])), [key]);
  const update = (next: Record<string, string>) => {
    const nextView = next.view === "list" ? "list" : next.view === "grid" ? "grid" : view;
    setPersistedView("reviews", nextView);
    setParams(Object.fromEntries(Object.entries({ ...next, view: nextView }).filter(([, value]) => value)));
  };
  const summary = useApi(useCallback((signal: AbortSignal) => api.reviewSummary(signal), []), []);
  const request = useCallback((signal: AbortSignal) => api.reviewCases({ page, ...filters }, signal), [page, filters]);
  const result = useApi(request, [request]);
  const rows = result.data?.items.map((item) => ({ case: item.case_id, status: item.status, priority: item.priority, work: item.canonical_work_key ?? "Not available", house: item.house ?? "Not available", state: item.state_name ?? "Not available", assignee: item.assignee ?? "Unassigned", updated: formatDateTime(item.updated_at) })) ?? [];
  return <div><PageHeader eyebrow="Authorized monitoring" title="Review queue" description="Analytical signals support human review; authorized officials make the final decision." /><div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4"><MetricCard label="Open cases" value={formatInteger(summary.data?.by_status.OPEN ?? 0)} description="Persisted review cases awaiting assignment." icon={Activity} /><MetricCard label="Under review" value={formatInteger(summary.data?.by_status.UNDER_REVIEW ?? 0)} description="Human review is currently in progress." icon={AlertTriangle} /><MetricCard label="Follow-up required" value={formatInteger(summary.data?.by_status.FOLLOW_UP_REQUIRED ?? 0)} description="Source-backed follow-up was requested." icon={Timer} /><MetricCard label="Active escalations" value={formatInteger(summary.data?.active_escalations ?? 0)} description="Auditable monitoring follow-up escalations." icon={GitCompareArrows} /></div><div className="mt-6"><MonitoringScopeFilters filters={filters} update={update}><FilterInput label="Search case, work, or assignee" value={filters.search} setValue={(value) => update({ ...filters, search: value })} /><label className="field-label">Review status<select className="field-control" value={filters.status} onChange={(event) => update({ ...filters, status: event.target.value })}><option value="">All statuses</option><option>OPEN</option><option>ASSIGNED</option><option>UNDER_REVIEW</option><option>FOLLOW_UP_REQUIRED</option><option>RESOLVED</option><option>CLOSED</option><option>REOPENED</option></select></label><label className="field-label">Review priority<select className="field-control" value={filters.priority} onChange={(event) => update({ ...filters, priority: event.target.value })}><option value="">All priorities</option><option>LOW</option><option>MEDIUM</option><option>HIGH</option><option>VERY_HIGH</option></select></label><FilterInput label="Assignee" value={filters.assignee} setValue={(value) => update({ ...filters, assignee: value })} /></MonitoringScopeFilters></div><section id="review-results-report" className="mt-6"><Panel title="Cases" description="Server-paginated cases and filters remain constrained by the server-authorized scope." actions={<ViewToggle value={view} onChange={(next) => update({ ...filters, view: next })} label="Review case view" />}>{result.loading ? <LoadingBlock /> : result.error ? authError(result.error, result.reload) : result.data ? <><div className="mb-4 flex flex-wrap items-center justify-between gap-3 rounded-lg border border-line bg-slate-50 p-3"><p className="text-sm text-slate-600">{result.data.pagination.total.toLocaleString("en-IN")} authorized case{result.data.pagination.total === 1 ? "" : "s"} · {view === "grid" ? "Grid view" : "List view"}</p><ReportActions title="MPLADS Review Queue Report" summary="Current authorized human-review workflow and evidence context." rows={rows} filters={filters} provenance={result.data.provenance} reportSelector="#review-results-report" /></div>{view === "grid" ? <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3" aria-label="Review case grid">{result.data.items.map((item) => <article key={item.case_id} className={`flex min-h-60 flex-col rounded-lg border border-line bg-white p-5 shadow-sm hover:shadow-md transition-all ${getRiskBorder(item.priority)}`}><div className="flex items-start justify-between gap-3"><Link className="font-semibold text-blue hover:underline" to={`/monitoring/reviews/${encodeURIComponent(item.case_id)}`}>{item.case_id}</Link><SignalPill value={item.priority} /></div><dl className="mt-4 grid grid-cols-2 gap-x-4 gap-y-3 border-t border-line pt-4 text-sm"><div><dt className="text-xs text-slate-500">Review status</dt><dd className="mt-1 text-slate-700">{item.status.replaceAll("_", " ")}</dd></div><div><dt className="text-xs text-slate-500">Work</dt><dd className="mt-1 break-all text-slate-700">{item.canonical_work_key ?? "Not available"}</dd></div><div><dt className="text-xs text-slate-500">State</dt><dd className="mt-1 truncate text-slate-700" title={item.state_name ?? undefined}>{item.state_name ?? "Not available"}</dd></div><div><dt className="text-xs text-slate-500">Assignee</dt><dd className="mt-1 text-slate-700">{item.assignee ?? "Unassigned"}</dd></div></dl><Link className="mt-auto pt-5 text-sm font-semibold text-blue hover:underline" to={`/monitoring/reviews/${encodeURIComponent(item.case_id)}`}>Open case evidence</Link></article>)}</div> : <div className="overflow-x-auto"><table className="min-w-[740px] w-full text-left text-sm" aria-label="Review case list"><thead><tr className="border-b border-line text-xs uppercase text-slate-500"><th className="p-3">Case</th><th className="p-3">Status</th><th className="p-3">Priority</th><th className="p-3">Work</th><th className="p-3">State</th><th className="p-3">Action</th></tr></thead><tbody>{result.data.items.map((item) => <tr key={item.case_id} className="border-b border-line/70"><td className="p-3 font-medium text-ink">{item.case_id}</td><td className="p-3">{item.status.replaceAll("_", " ")}</td><td className="p-3"><SignalPill value={item.priority} /></td><td className="p-3 break-all">{item.canonical_work_key ?? "Not available"}</td><td className="p-3">{item.state_name ?? "Not available"}</td><td className="p-3"><Link className="font-medium text-blue hover:underline" to={`/monitoring/reviews/${encodeURIComponent(item.case_id)}`}>Open case evidence</Link></td></tr>)}</tbody></table></div>}{!result.data.items.length && <EmptyState title="No monitoring results match the selected filters." />}{<Pagination page={result.data.pagination} onPageChange={(next) => update({ ...filters, page: String(next) })} />}</> : null}</Panel></section></div>;
}

export function ReviewCaseDetailPage() {
  const { caseId = "" } = useParams();
  const [revision, setRevision] = useState(0);
  const request = useCallback((signal: AbortSignal) => api.reviewCase(caseId, signal), [caseId, revision]);
  const result = useApi(request, [request]);
  if (result.loading) return <LoadingBlock label="Loading review case…" />;
  if (result.error) return authError(result.error, result.reload);
  if (!result.data) return null;
  const data = result.data;
  const snapshot = data.evidence_snapshot as Record<string, unknown> | null;

  const evidenceRows: Array<{ finding_attribute: string; evidence_detail: string }> = [];
  if (snapshot && typeof snapshot === "object") {
    for (const [k, v] of Object.entries(snapshot)) {
      if (typeof v === "string" || typeof v === "number" || typeof v === "boolean") {
        evidenceRows.push({ finding_attribute: k.replaceAll("_", " "), evidence_detail: String(v) });
      } else if (v && typeof v === "object" && !Array.isArray(v)) {
        for (const [subK, subV] of Object.entries(v as Record<string, unknown>)) {
          if (typeof subV === "string" || typeof subV === "number" || typeof subV === "boolean") {
            evidenceRows.push({ finding_attribute: `${k.replaceAll("_", " ")}: ${subK.replaceAll("_", " ")}`, evidence_detail: String(subV) });
          }
        }
      } else if (Array.isArray(v) && v.length > 0) {
        evidenceRows.push({ finding_attribute: k.replaceAll("_", " "), evidence_detail: `${v.length} attached record(s) in snapshot` });
      }
    }
  }

  const historyRows = data.events.map((e) => ({
    action: e.action.replaceAll("_", " "),
    actor: e.actor,
    occurred_at: formatDateTime(e.occurred_at),
    comment: e.comment ?? "—",
  }));

  const caseKpis = [
    { label: "Case ID", value: data.case_id },
    { label: "Status", value: data.status.replaceAll("_", " ") },
    { label: "Priority", value: data.priority },
    { label: "Assignee", value: data.assignee ?? "Unassigned" },
  ];

  return <div id="review-case-detail-report">
    <PageHeader
      eyebrow="Authorized review"
      title={`Case ${data.case_id}`}
      description="Analytical signals support review; authorized officials make the final decision."
      actions={
        <div className="flex flex-wrap items-center gap-2">
          {data.canonical_work_key ? <Link className="button-secondary text-xs" to={`/works/${encodeURIComponent(data.canonical_work_key)}`}>Open public work record</Link> : null}
        </div>
      }
    />

    <div className="mb-5 flex flex-wrap items-center justify-between gap-3 rounded-lg border border-line bg-white px-4 py-3 shadow-sm">
      <div>
        <p className="text-sm font-semibold text-ink">Review case report</p>
        <p className="mt-1 text-xs text-slate-500">Generate an official investigation dossier for Case {data.case_id}.</p>
      </div>
      <ReportActions
        title={`MPLADS Review Case Report — ${data.case_id}`}
        summary={`Official review case dossier for Case ${data.case_id} (${data.priority} priority · ${data.status.replaceAll("_", " ")})`}
        sections={[
          {
            title: "Case Identification & Workflow State",
            subtitle: "Current administrative investigation status",
            kpis: caseKpis,
            evidenceItems: [
              { label: "Canonical Work Key", value: data.canonical_work_key ?? "Not available" },
              { label: "House", value: data.house ? data.house.replaceAll("_", " ") : "Not available" },
              { label: "State / UT", value: data.state_name ?? "Not available" },
              { label: "District / IDA", value: data.district_or_ida ?? "Not available" },
              { label: "MP", value: data.mp_source_name ?? "Not available" },
              { label: "Source Alert ID", value: data.source_alert_id ?? "None" },
              { label: "Source Signal ID", value: data.source_signal_id ?? "None" },
              { label: "Case Version", value: String(data.version) },
            ],
          },
          {
            title: "Frozen Analytical Evidence Snapshot",
            subtitle: `Snapshot ID ${data.evidence_snapshot_id} (SHA-256: ${data.evidence_hash.slice(0, 16)}…)`,
            rows: evidenceRows.length ? evidenceRows : [{ finding_attribute: "Snapshot status", evidence_detail: "No structured snapshot records attached" }],
            columns: ["finding_attribute", "evidence_detail"],
          },
          {
            title: "Review Audit & Action History",
            subtitle: "Append-only log of authorized human review actions",
            rows: historyRows.length ? historyRows : [{ action: "Created", actor: "System", occurred_at: "Initial", comment: "Case initialized" }],
            columns: ["action", "actor", "occurred_at", "comment"],
          },
        ]}
        rows={historyRows}
        kpis={caseKpis}
        provenance={data.provenance}
        reportSelector="#review-case-detail-report"
      />
    </div>

    <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
      <MetricCard label="Status" value={data.status.replaceAll("_", " ")} description="Current human-review workflow state." icon={Activity} />
      <MetricCard label="Priority" value={data.priority} description="Derived from the source analytical evidence." icon={AlertTriangle} />
      <MetricCard label="Assignee" value={data.assignee ?? "Unassigned"} description="Current authorized review assignment." icon={GitCompareArrows} />
      <MetricCard label="Version" value={String(data.version)} description="Required to avoid overwriting another review action." icon={Timer} />
    </div>

    <div className="mt-6 grid gap-6 xl:grid-cols-2">
      <Panel title="Case information">
        <dl className="grid gap-3 text-sm sm:grid-cols-2">
          {[["Work", data.canonical_work_key], ["House", data.house], ["State", data.state_name], ["District / IDA", data.district_or_ida], ["MP", data.mp_source_name], ["Source alert", data.source_alert_id], ["Source signal", data.source_signal_id], ["Dataset version", data.dataset_version]].map(([label, value]) => (
            <div key={label}>
              <dt className="text-slate-500">{label}</dt>
              <dd className="mt-1 break-all font-medium text-ink">{value ?? "Not available"}</dd>
            </div>
          ))}
        </dl>
      </Panel>

      <Panel title="Frozen analytical evidence" description={`Snapshot ${data.evidence_snapshot_id} · SHA-256 ${data.evidence_hash}. This evidence cannot be changed by review actions.`}>
        {snapshot && typeof snapshot === "object" && Object.keys(snapshot).length > 0 ? (
          <div className="space-y-4">
            {Object.entries(snapshot).map(([section, value]) => {
              if (value === null || value === undefined) return null;
              if (typeof value === "string" || typeof value === "number" || typeof value === "boolean") {
                return (
                  <dl key={section} className="rounded border border-line/60 bg-slate-50 p-3">
                    <dt className="text-xs font-medium uppercase text-slate-500">{section.replaceAll("_", " ")}</dt>
                    <dd className="mt-1 text-sm font-semibold text-ink">{String(value)}</dd>
                  </dl>
                );
              }
              if (typeof value === "object" && !Array.isArray(value)) {
                const entries = Object.entries(value as Record<string, unknown>);
                return (
                  <div key={section} className="rounded-lg border border-line bg-slate-50 p-3">
                    <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">{section.replaceAll("_", " ")}</h3>
                    <dl className="grid gap-2 sm:grid-cols-2">
                      {entries.slice(0, 20).map(([k, v]) => (
                        <div key={k} className="rounded border border-line/40 bg-white p-2">
                          <dt className="text-xs text-slate-500">{k.replaceAll("_", " ")}</dt>
                          <dd className="mt-0.5 break-all text-sm font-medium text-ink">
                            {typeof v === "object" && v !== null ? JSON.stringify(v) : String(v ?? "Not available")}
                          </dd>
                        </div>
                      ))}
                    </dl>
                  </div>
                );
              }
              if (Array.isArray(value) && value.length > 0) {
                return (
                  <div key={section} className="rounded-lg border border-line bg-slate-50 p-3">
                    <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">{section.replaceAll("_", " ")} ({value.length} record{value.length === 1 ? "" : "s"})</h3>
                    <div className="space-y-2">
                      {value.slice(0, 10).map((item, index) => (
                        typeof item === "object" && item !== null ? (
                          <dl key={index} className="grid gap-2 rounded border border-line/40 bg-white p-2 sm:grid-cols-2 lg:grid-cols-3">
                            {Object.entries(item as Record<string, unknown>).slice(0, 12).map(([k, v]) => (
                              <div key={k}>
                                <dt className="text-xs text-slate-500">{k.replaceAll("_", " ")}</dt>
                                <dd className="break-all text-sm text-ink">{typeof v === "object" && v !== null ? JSON.stringify(v) : String(v ?? "—")}</dd>
                              </div>
                            ))}
                          </dl>
                        ) : (
                          <p key={index} className="text-sm text-slate-700">{String(item)}</p>
                        )
                      ))}
                      {value.length > 10 && <p className="text-xs text-slate-500">…and {value.length - 10} more record(s). Expand raw JSON for complete data.</p>}
                    </div>
                  </div>
                );
              }
              return null;
            })}
            <details className="mt-2">
              <summary className="cursor-pointer text-xs font-medium text-blue hover:underline">Show raw JSON evidence</summary>
              <pre className="mt-2 max-h-60 overflow-auto rounded-lg bg-slate-950 p-3 text-xs leading-5 text-slate-100">{JSON.stringify(snapshot, null, 2)}</pre>
            </details>
          </div>
        ) : (
          <p className="text-sm text-slate-600">No structured evidence snapshot is attached to this case.</p>
        )}
      </Panel>
    </div>

    <Panel title="Review history" className="mt-6" description="Append-only timeline of authorized actions.">
      <ol className="space-y-4 border-l border-blue-200 pl-5">
        {data.events.map((event) => (
          <li key={event.event_id} className="relative">
            <span className="absolute -left-[1.8rem] top-1.5 size-2.5 rounded-full bg-blue" aria-hidden="true" />
            <p className="font-medium text-ink">{event.action.replaceAll("_", " ")}</p>
            <p className="text-sm text-slate-600">{event.actor} · {formatDateTime(event.occurred_at)}</p>
            {event.comment && <p className="mt-1 text-sm leading-6 text-slate-700">{event.comment}</p>}
          </li>
        ))}
      </ol>
    </Panel>

    <ReviewActionForm caseId={data.case_id} version={data.version} onComplete={() => { setRevision((value) => value + 1); result.reload(); }} />
    <Provenance version={data.provenance.dataset_version} generated={data.provenance.generated_at} />
  </div>;
}

const benchmarkLabels: Record<string, string> = {
  SANCTION_LATENCY_DAYS: "Observed sanction latency",
  COMPLETION_RATIO: "Completion ratio",
  EXPENDITURE_PACING_RATIO: "Expenditure pacing ratio",
};

const benchmarkValue = (value: number | null, metric: string) =>
  value === null
    ? "Not available"
    : metric === "COMPLETION_RATIO" || metric === "EXPENDITURE_PACING_RATIO"
    ? `${(value * 100).toFixed(1)}%`
    : `${value.toFixed(1)} days`;

function PeerDetails({ result, onClose }: { result: BenchmarkResult; onClose?: () => void }) {
  const peers = useApi(useCallback((signal: AbortSignal) => api.benchmarkPeers(result.result_id, signal), [result.result_id]), [result.result_id]);
  const [showPeerList, setShowPeerList] = useState(false);

  return (
    <div id="benchmark-cohort-panel" className="mt-6 rounded-xl border-2 border-blue-500/40 bg-white p-5 shadow-panel">
      <div className="flex flex-wrap items-start justify-between gap-4 border-b border-line pb-4">
        <div>
          <div className="inline-flex items-center gap-2 text-[11px] font-bold uppercase tracking-wider text-blue">
            <span className="size-1.5 rounded-full bg-[#d97706]" aria-hidden="true" />
            Peer Cohort Comparison
          </div>
          <h3 className="mt-1 text-base font-bold text-ink">Same-House peer cohort</h3>
          <p className="mt-0.5 text-xs text-slate-600">
            {result.entity_id} — {benchmarkLabels[result.metric] ?? result.metric}. Cohort criteria established prior to evaluating observed metrics.
          </p>
        </div>
        {onClose && (
          <button type="button" onClick={onClose} className="button-secondary text-xs">
            Close Panel
          </button>
        )}
      </div>

      {peers.loading ? (
        <LoadingBlock label="Loading peer cohort details…" />
      ) : peers.error ? (
        authError(peers.error, peers.reload)
      ) : peers.data ? (
        <div className="mt-4 space-y-4">
          <div className="mb-3 flex flex-wrap items-center justify-between gap-3 rounded-lg border border-line bg-slate-50 p-3">
            <div>
              <p className="text-xs font-semibold text-ink">Entity benchmark report</p>
              <p className="text-[11px] text-slate-500">Generate an official dossier with observed metrics, median, P25, P75, and cohort criteria.</p>
            </div>
            <ReportActions
              title={`MPLADS Peer Benchmark Report — ${result.entity_id}`}
              summary={`Peer benchmark analysis for ${result.entity_id} (${benchmarkLabels[result.metric] ?? result.metric})`}
              sections={[
                {
                  title: "Observed Metric vs Peer Cohort",
                  subtitle: `House: ${result.house.replaceAll("_", " ")} · Metric: ${benchmarkLabels[result.metric] ?? result.metric}`,
                  kpis: [
                    { label: "Observed Value", value: benchmarkValue(result.value, result.metric), description: "Observed entity metric" },
                    { label: "Peer Median", value: benchmarkValue(result.peer_median, result.metric), description: "Cohort midpoint" },
                    { label: "P25 Threshold", value: benchmarkValue(result.p25, result.metric), description: "25th percentile" },
                    { label: "P75 Threshold", value: benchmarkValue(result.p75, result.metric), description: "75th percentile" },
                    { label: "P90 Threshold", value: benchmarkValue(result.p90, result.metric), description: "90th percentile" },
                    { label: "Peer Count", value: `${formatInteger(result.peer_count)} peers`, description: "Comparable peers" },
                  ],
                  narrative: result.interpretation,
                },
                {
                  title: "Cohort Methodology & Selection Criteria",
                  subtitle: "Rules established prior to evaluating observed metrics",
                  evidenceItems: [
                    { label: "Selected Entity", value: result.entity_id },
                    { label: "House Cohort", value: result.house.replaceAll("_", " ") },
                    { label: "Metric", value: benchmarkLabels[result.metric] ?? result.metric },
                    { label: "Directionality", value: result.directionality.replaceAll("_", " ") },
                    { label: "Minimum Valid Works", value: `${String(peers.data?.cohort_definition?.minimum_valid_works ?? 10)} per entity` },
                    { label: "Authorized Peer Sample", value: (peers.data?.peer_ids ?? []).slice(0, 8).join(", ") + ((peers.data?.peer_ids?.length ?? 0) > 8 ? ` … and ${(peers.data?.peer_ids?.length ?? 0) - 8} more` : "") },
                  ],
                },
                {
                  title: "Benchmark Metric Reference Table",
                  subtitle: "Comparison against peer percentiles",
                  rows: [
                    {
                      entity: result.entity_id,
                      metric: benchmarkLabels[result.metric] ?? result.metric,
                      observed_value: benchmarkValue(result.value, result.metric),
                      peer_median: benchmarkValue(result.peer_median, result.metric),
                      p25: benchmarkValue(result.p25, result.metric),
                      p75: benchmarkValue(result.p75, result.metric),
                      p90: benchmarkValue(result.p90, result.metric),
                      interpretation: result.interpretation,
                    },
                  ],
                  columns: ["entity", "metric", "observed_value", "peer_median", "p25", "p75", "p90", "interpretation"],
                },
              ]}
              rows={[
                {
                  entity: result.entity_id,
                  metric: benchmarkLabels[result.metric] ?? result.metric,
                  observed_value: benchmarkValue(result.value, result.metric),
                  peer_median: benchmarkValue(result.peer_median, result.metric),
                  p25: benchmarkValue(result.p25, result.metric),
                  p75: benchmarkValue(result.p75, result.metric),
                  p90: benchmarkValue(result.p90, result.metric),
                  interpretation: result.interpretation,
                },
              ]}
              reportSelector="#benchmark-cohort-panel"
            />
          </div>

          <dl className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4 text-xs">
            <div className="rounded-lg bg-slate-50 p-3 border border-line">
              <dt className="text-slate-500 font-medium">Selected Entity</dt>
              <dd className="mt-1 font-semibold text-ink text-sm truncate" title={result.entity_id}>
                {result.entity_id}
              </dd>
            </div>
            <div className="rounded-lg bg-slate-50 p-3 border border-line">
              <dt className="text-slate-500 font-medium">House</dt>
              <dd className="mt-1 font-semibold text-ink text-sm">{result.house.replaceAll("_", " ")}</dd>
            </div>
            <div className="rounded-lg bg-slate-50 p-3 border border-line">
              <dt className="text-slate-500 font-medium">Metric</dt>
              <dd className="mt-1 font-semibold text-ink text-sm">{benchmarkLabels[result.metric] ?? result.metric}</dd>
            </div>
            <div className="rounded-lg bg-slate-50 p-3 border border-line">
              <dt className="text-slate-500 font-medium">Peer Count</dt>
              <dd className="mt-1 font-semibold text-ink text-sm">{formatInteger(result.peer_count)} peers</dd>
            </div>
          </dl>

          <dl className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5 text-xs">
            <div className="rounded-lg bg-blue-50/50 p-3 border border-blue-200">
              <dt className="text-blue-900 font-semibold">Observed Value</dt>
              <dd className="mt-1 font-bold text-blue-700 text-base">{benchmarkValue(result.value, result.metric)}</dd>
            </div>
            <div className="rounded-lg bg-slate-50 p-3 border border-line">
              <dt className="text-slate-500 font-medium">Peer Median</dt>
              <dd className="mt-1 font-semibold text-ink text-sm">{benchmarkValue(result.peer_median, result.metric)}</dd>
            </div>
            <div className="rounded-lg bg-slate-50 p-3 border border-line">
              <dt className="text-slate-500 font-medium">P25 – P75 Range</dt>
              <dd className="mt-1 font-semibold text-ink text-sm">
                {benchmarkValue(result.p25, result.metric)} – {benchmarkValue(result.p75, result.metric)}
              </dd>
            </div>
            <div className="rounded-lg bg-slate-50 p-3 border border-line">
              <dt className="text-slate-500 font-medium">P90 Threshold</dt>
              <dd className="mt-1 font-semibold text-ink text-sm">{benchmarkValue(result.p90, result.metric)}</dd>
            </div>
            <div className="rounded-lg bg-slate-50 p-3 border border-line">
              <dt className="text-slate-500 font-medium">Interpretation</dt>
              <dd className="mt-1 font-semibold text-ink text-xs leading-snug">
                {result.interpretation}
              </dd>
            </div>
          </dl>

          <div className="rounded-lg bg-slate-50 p-3.5 border border-line text-xs text-slate-600">
            <span className="font-semibold text-slate-800">Selection Criteria:</span>{" "}
            Same-House peers ({result.house.replaceAll("_", " ")}) · Minimum valid works: {String(peers.data.cohort_definition.minimum_valid_works ?? 10)} per entity · Directionality: {result.directionality.replaceAll("_", " ")}
          </div>

          {peers.data.peer_ids && peers.data.peer_ids.length > 0 ? (
            <div className="rounded-lg border border-line bg-white p-3.5">
              <div className="flex items-center justify-between gap-3">
                <div>
                  <span className="text-xs font-semibold text-slate-800">
                    Authorized Peers ({peers.data.peer_ids.length}):
                  </span>
                  <span className="ml-2 text-xs text-slate-500">
                    {peers.data.peer_ids.slice(0, 6).join(", ")}
                    {peers.data.peer_ids.length > 6 && !showPeerList && ` … and ${peers.data.peer_ids.length - 6} more peers`}
                  </span>
                </div>
                {peers.data.peer_ids.length > 6 && (
                  <button
                    type="button"
                    className="button-secondary text-xs shrink-0 py-1 px-2.5 h-7"
                    onClick={() => setShowPeerList((prev) => !prev)}
                  >
                    {showPeerList ? "Hide Peer List" : `View Peer List (${peers.data.peer_ids.length})`}
                  </button>
                )}
              </div>

              {showPeerList && (
                <div className="mt-3 max-h-48 overflow-y-auto rounded border border-line bg-slate-50 p-2.5">
                  <div className="flex flex-wrap gap-1.5">
                    {peers.data.peer_ids.map((peerId) => (
                      <span
                        key={peerId}
                        className="inline-flex items-center rounded bg-white px-2 py-0.5 text-[11px] font-medium text-slate-700 border border-line shadow-2xs"
                      >
                        {peerId}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          ) : (
            <div className="rounded-lg border border-line bg-slate-50 p-3 text-xs text-slate-600 italic">
              Individual peer identities are not authorized in this scope. Aggregate benchmark metrics are displayed above.
            </div>
          )}
        </div>
      ) : null}
    </div>
  );
}

export function BenchmarkingPage() {
  const [params, setParams] = useSearchParams();
  const [selected, setSelected] = useState<BenchmarkResult>();
  const page = Number(params.get("page") ?? 1);
  const names = ["metric", "house", "state", "mp", "bottleneck"];
  const key = names.map((name) => `${name}=${params.get(name) ?? ""}`).join("&");
  const filters = useMemo(() => Object.fromEntries(names.map((name) => [name, params.get(name) ?? ""])), [key]);
  const update = (next: Record<string, string>) => {
    setSelected(undefined);
    setParams(Object.fromEntries(Object.entries(next).filter(([, value]) => value)));
  };
  const summary = useApi(useCallback((signal: AbortSignal) => api.benchmarkSummary(signal), []), []);
  const request = useCallback((signal: AbortSignal) => api.benchmarkResults({ page, ...filters, ...(filters.bottleneck ? { bottleneck: filters.bottleneck === "yes" } : {}) }, signal), [page, filters]);
  const result = useApi(request, [request]);

  const selectCohort = (row: BenchmarkResult) => {
    setSelected(row);
    // Smooth scroll down to the cohort view
    setTimeout(() => {
      document.getElementById("benchmark-cohort-panel")?.scrollIntoView?.({ behavior: "smooth" });
    }, 50);
  };

  if (summary.loading && result.loading) return <LoadingBlock label="Loading persisted peer benchmarks…" />;
  if (summary.error) return authError(summary.error, summary.reload);

  return (
    <div>
      <PageHeader
        eyebrow="Authorized monitoring"
        title="Peer benchmarking"
        description="Compare → Understand → Review. Same-House peer benchmarks are contextual evidence, not a verdict."
      />
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <MetricCard label="Benchmarked entities" value={formatInteger(summary.data?.entity_count ?? 0)} description="MP entities derived from the active database release." icon={Activity} />
        <MetricCard label="Persisted metric results" value={formatInteger(summary.data?.result_count ?? 0)} description="Versioned benchmark records; not in-browser calculations." icon={GitCompareArrows} />
        <MetricCard label="Potential bottlenecks" value={formatInteger(summary.data?.bottleneck_count ?? 0)} description="Direction-aware peer comparison flags for review." icon={AlertTriangle} />
        <MetricCard label="Benchmark version" value={summary.data?.benchmark_version ?? "Loading"} description="Deterministic active-release benchmark configuration." icon={Timer} />
      </div>

      <section className="mt-6 grid gap-3 rounded-xl border border-line bg-white p-4 sm:grid-cols-2 xl:grid-cols-3">
        <label className="field-label">
          Metric
          <select className="field-control" value={filters.metric} onChange={(event) => update({ ...filters, metric: event.target.value })}>
            <option value="">All metrics</option>
            <option value="SANCTION_LATENCY_DAYS">Observed sanction latency</option>
            <option value="COMPLETION_RATIO">Completion ratio</option>
            <option value="EXPENDITURE_PACING_RATIO">Expenditure pacing ratio</option>
          </select>
        </label>
        <FilterInput label="House" value={filters.house} setValue={(value) => update({ ...filters, house: value })} />
        <FilterInput label="State" value={filters.state} setValue={(value) => update({ ...filters, state: value })} />
        <FilterInput label="MP" value={filters.mp} setValue={(value) => update({ ...filters, mp: value })} />
        <label className="field-label">
          Potential bottleneck
          <select className="field-control" value={filters.bottleneck} onChange={(event) => update({ ...filters, bottleneck: event.target.value })}>
            <option value="">All results</option>
            <option value="yes">Potential bottleneck</option>
            <option value="no">No bottleneck</option>
          </select>
        </label>
      </section>

      {selected && (
        <section className="mt-6">
          <PeerDetails result={selected} onClose={() => setSelected(undefined)} />
        </section>
      )}

      <section className="mt-6">
        <Panel title="Peer benchmark results" description="A benchmark is available only when there are at least five same-House peers and ten valid works per entity.">
          {result.loading ? (
            <LoadingBlock />
          ) : result.error ? (
            authError(result.error, result.reload)
          ) : result.data ? (
            <>
              <div className="overflow-x-auto">
                <table className="min-w-[1150px] w-full text-left text-sm">
                  <thead>
                    <tr className="border-b border-line text-xs uppercase text-slate-500">
                      <th className="p-3">MP</th>
                      <th className="p-3">House</th>
                      <th className="p-3">Metric</th>
                      <th className="p-3">Observed value</th>
                      <th className="p-3">Peer median</th>
                      <th className="p-3">P25–P75</th>
                      <th className="p-3">Peers</th>
                      <th className="p-3">Interpretation</th>
                      <th className="p-3"><span className="sr-only">Cohort</span></th>
                    </tr>
                  </thead>
                  <tbody>
                    {result.data.items.map((row) => (
                      <tr
                        key={row.result_id}
                        className={`border-b border-line/70 align-top transition-colors ${selected?.result_id === row.result_id ? "bg-blue-50/70 font-medium" : "hover:bg-slate-50/80"}`}
                      >
                        <td className="p-3 font-medium">{row.entity_id}</td>
                        <td className="p-3">{row.house.replaceAll("_", " ")}</td>
                        <td className="p-3">{benchmarkLabels[row.metric] ?? row.metric}</td>
                        <td className="p-3 font-semibold text-blue-700">{benchmarkValue(row.value, row.metric)}</td>
                        <td className="p-3">{benchmarkValue(row.peer_median, row.metric)}</td>
                        <td className="p-3">{benchmarkValue(row.p25, row.metric)} – {benchmarkValue(row.p75, row.metric)}</td>
                        <td className="p-3">{formatInteger(row.peer_count)}</td>
                        <td className="p-3">{row.benchmark_available ? row.interpretation : "Benchmark unavailable: insufficient comparable data."}</td>
                        <td className="p-3">
                          <button
                            type="button"
                            className={`text-xs ${selected?.result_id === row.result_id ? "button-primary" : "button-secondary"}`}
                            onClick={() => selectCohort(row)}
                          >
                            {selected?.result_id === row.result_id ? "Active cohort" : "Cohort"}
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              {!result.data.items.length && <EmptyState title="No monitoring results match the selected filters." />}
              <Pagination page={result.data.pagination} onPageChange={(next) => update({ ...filters, page: String(next) })} />
            </>
          ) : null}
        </Panel>
      </section>

      {summary.data && (
        <Provenance
          version={summary.data.dataset_version}
          generated={summary.data.generated_at}
          model={`Benchmark ${summary.data.benchmark_version}`}
        />
      )}
    </div>
  );
}

export function RecommendationsPage() {
  const [params, setParams] = useSearchParams();
  const page = Number(params.get("page") ?? 1);
  const persistedView = getPersistedView("recommendations", "grid");
  const viewParam = params.get("view");
  const view: CollectionView = viewParam === "list" ? "list" : viewParam === "grid" ? "grid" : persistedView;
  const names = ["search", "status", "priority", "house", "state", "district_or_ida", "mp"];
  const key = names.map((name) => `${name}=${params.get(name) ?? ""}`).join("&");
  const filters = useMemo(() => Object.fromEntries(names.map((name) => [name, params.get(name) ?? ""])), [key]);
  const [message, setMessage] = useState<{ text: string; type: "success" | "error" } | null>(null);
  const [updatingId, setUpdatingId] = useState<string | null>(null);
  const [creatingCaseId, setCreatingCaseId] = useState<string | null>(null);
  const [createdCases, setCreatedCases] = useState<Record<string, string>>({});

  const update = (next: Record<string, string>) => {
    const nextView = next.view === "list" ? "list" : next.view === "grid" ? "grid" : view;
    setPersistedView("recommendations", nextView);
    setParams(Object.fromEntries(Object.entries({ ...next, view: nextView }).filter(([, value]) => value)));
  };

  const request = useCallback((signal: AbortSignal) => api.recommendations({ page, ...filters }, signal), [page, filters]);
  const result = useApi(request, [request]);

  const changeStatus = async (row: Recommendation, newStatus: string) => {
    if (newStatus === row.status) return;
    if (newStatus === "NOTED" && row.status !== "NOTED") {
      setMessage({ text: "Invalid transition: recommendations cannot return to NOTED once under review or action.", type: "error" });
      return;
    }
    setUpdatingId(row.recommendation_id);
    try {
      await api.recommendationStatus(row.recommendation_id, newStatus, row.version);
      setMessage({ text: `Recommendation status updated to ${newStatus.replaceAll("_", " ")}.`, type: "success" });
      result.reload();
    } catch (error) {
      setMessage({ text: error instanceof Error ? error.message : "Unable to update recommendation status.", type: "error" });
    } finally {
      setUpdatingId(null);
    }
  };

  const createCase = async (row: Recommendation) => {
    setCreatingCaseId(row.recommendation_id);
    try {
      const created = await api.recommendationReviewCase(row.recommendation_id);
      setCreatedCases((prev) => ({ ...prev, [row.recommendation_id]: created.case_id }));
      setMessage({ text: `Review case created successfully. Case ID: ${created.case_id}`, type: "success" });
    } catch (error) {
      setMessage({ text: error instanceof Error ? error.message : "Unable to create review case.", type: "error" });
    } finally {
      setCreatingCaseId(null);
    }
  };

  const rows = result.data?.items.map((row) => ({
    recommendation: row.recommendation_type,
    priority: row.priority,
    status: row.status,
    entity_or_work: row.canonical_work_key ?? row.entity_id,
    reason: row.reason,
    generated: formatDateTime(row.generated_at),
  })) ?? [];

  const renderActions = (row: Recommendation) => {
    const isUpdating = updatingId === row.recommendation_id;
    const isCreating = creatingCaseId === row.recommendation_id;
    const existingCaseId = createdCases[row.recommendation_id];

    return (
      <div className="flex flex-col gap-2 min-w-[200px]">
        <div>
          <label className="text-xs font-semibold text-slate-700 block mb-1" htmlFor={`status-${row.recommendation_id}`}>
            Update status:
          </label>
          <select
            id={`status-${row.recommendation_id}`}
            className="field-control text-xs py-1.5"
            value={row.status}
            disabled={isUpdating}
            onChange={(event) => changeStatus(row, event.target.value)}
          >
            <option value="NOTED" disabled={row.status !== "NOTED"}>Noted (Initial status)</option>
            <option value="UNDER_REVIEW">Under Review</option>
            <option value="ACTION_INITIATED">Action Initiated</option>
            <option value="RESOLVED">Resolved</option>
          </select>
          {isUpdating && <span className="mt-1 text-[11px] text-blue-600 block">Updating status…</span>}
        </div>

        {existingCaseId ? (
          <Link
            to={`/monitoring/reviews/${encodeURIComponent(existingCaseId)}`}
            className="button-secondary text-xs text-center inline-block text-blue font-semibold hover:underline"
          >
            Open Review Case ({existingCaseId.slice(0, 12)}…)
          </Link>
        ) : (
          <button
            type="button"
            className="button-secondary text-xs"
            disabled={isCreating}
            onClick={() => createCase(row)}
          >
            {isCreating ? "Creating case…" : "Create review case"}
          </button>
        )}
      </div>
    );
  };

  return (
    <div>
      <PageHeader
        eyebrow="Authorized monitoring"
        title="Review recommendations"
        description="Evidence-based guidance for what to examine next. Recommendations are not accusations or findings."
      />

      {message && (
        <p
          className={`mb-4 rounded-lg border p-3 text-sm font-medium ${
            message.type === "success"
              ? "border-emerald-200 bg-emerald-50 text-emerald-900"
              : "border-rose-200 bg-rose-50 text-rose-900"
          }`}
          role="status"
        >
          {message.text}
        </p>
      )}

      <MonitoringScopeFilters filters={filters} update={update}>
        <FilterInput label="Search evidence or entity" value={filters.search} setValue={(value) => update({ ...filters, search: value })} />
        <label className="field-label">
          Recommendation status
          <select className="field-control" value={filters.status} onChange={(event) => update({ ...filters, status: event.target.value })}>
            <option value="">All statuses</option>
            <option>NOTED</option>
            <option>UNDER_REVIEW</option>
            <option>ACTION_INITIATED</option>
            <option>RESOLVED</option>
          </select>
        </label>
        <label className="field-label">
          Priority
          <select className="field-control" value={filters.priority} onChange={(event) => update({ ...filters, priority: event.target.value })}>
            <option value="">All priorities</option>
            <option>LOW</option>
            <option>MEDIUM</option>
            <option>HIGH</option>
            <option>VERY_HIGH</option>
          </select>
        </label>
      </MonitoringScopeFilters>

      <section id="recommendation-results-report" className="mt-6">
        <Panel
          title="Recommendations"
          description="Every recommendation is generated from persisted monitoring or benchmark evidence."
          actions={<ViewToggle value={view} onChange={(next) => update({ ...filters, view: next })} label="Recommendation result view" />}
        >
          {result.loading ? (
            <LoadingBlock />
          ) : result.error ? (
            authError(result.error, result.reload)
          ) : result.data ? (
            <>
              <div className="mb-4 flex flex-wrap items-center justify-between gap-3 rounded-lg border border-line bg-slate-50 p-3">
                <p className="text-sm text-slate-600">
                  {result.data.pagination.total.toLocaleString("en-IN")} evidence-backed recommendation{result.data.pagination.total === 1 ? "" : "s"} · {view === "grid" ? "Grid view" : "List view"}
                </p>
                <ReportActions
                  title="MPLADS Recommendation Review Report"
                  summary="Current authorized investigation guidance and supporting evidence context."
                  rows={rows}
                  filters={filters}
                  provenance={result.data.provenance}
                  reportSelector="#recommendation-results-report"
                />
              </div>

              {view === "grid" ? (
                <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3" aria-label="Recommendation result grid">
                  {result.data.items.map((row) => (
                    <article key={row.recommendation_id} className="flex min-h-72 flex-col rounded-lg border border-line bg-white p-5 shadow-sm">
                      <div className="flex items-start justify-between gap-3">
                        <p className="text-sm font-semibold text-ink">{row.recommendation_type.replaceAll("_", " ")}</p>
                        <SignalPill value={row.priority} />
                      </div>
                      <p className="mt-3 text-sm leading-6 text-slate-700">{row.reason}</p>
                      <dl className="mt-4 grid grid-cols-2 gap-x-4 gap-y-3 border-t border-line pt-4 text-sm">
                        <div>
                          <dt className="text-xs text-slate-500">Status</dt>
                          <dd className="mt-1">
                            <StatusBadge value={row.status} />
                          </dd>
                        </div>
                        <div>
                          <dt className="text-xs text-slate-500">Entity / work</dt>
                          <dd className="mt-1 break-all text-xs font-mono text-slate-700">{row.canonical_work_key ?? row.entity_id}</dd>
                        </div>
                      </dl>
                      <details className="mt-4 text-sm">
                        <summary className="cursor-pointer font-medium text-blue text-xs">Inspect evidence</summary>
                        <pre className="mt-2 max-h-36 overflow-auto rounded bg-slate-950 p-2 text-xs text-slate-100">{JSON.stringify(row.evidence_references, null, 2)}</pre>
                      </details>
                      <div className="mt-auto pt-4 border-t border-line/60">
                        {renderActions(row)}
                      </div>
                    </article>
                  ))}
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="min-w-[1050px] w-full text-left text-sm" aria-label="Recommendation result list">
                    <thead>
                      <tr className="border-b border-line text-xs uppercase text-slate-500">
                        <th className="p-3">Recommendation</th>
                        <th className="p-3">Priority</th>
                        <th className="p-3">Status</th>
                        <th className="p-3">Entity / work</th>
                        <th className="p-3">Reason</th>
                        <th className="p-3">Evidence</th>
                        <th className="p-3">Action</th>
                      </tr>
                    </thead>
                    <tbody>
                      {result.data.items.map((row) => (
                        <tr key={row.recommendation_id} className="border-b border-line/70 align-top">
                          <td className="p-3 font-medium text-ink">{row.recommendation_type.replaceAll("_", " ")}</td>
                          <td className="p-3"><SignalPill value={row.priority} /></td>
                          <td className="p-3"><StatusBadge value={row.status} /></td>
                          <td className="p-3 break-all font-mono text-xs">{row.canonical_work_key ?? row.entity_id}</td>
                          <td className="max-w-sm p-3 leading-6 text-slate-700">{row.reason}</td>
                          <td className="p-3">
                            <details>
                              <summary className="cursor-pointer font-medium text-blue text-xs">Inspect evidence</summary>
                              <pre className="mt-2 max-w-xs overflow-auto rounded bg-slate-950 p-2 text-xs text-slate-100">{JSON.stringify(row.evidence_references, null, 2)}</pre>
                            </details>
                          </td>
                          <td className="p-3">{renderActions(row)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}

              {!result.data.items.length && <EmptyState title="No recommendations are currently generated for this scope." />}
              <Pagination page={result.data.pagination} onPageChange={(next) => update({ ...filters, page: String(next) })} />
            </>
          ) : null}
        </Panel>
      </section>

      {result.data && <Provenance version={result.data.provenance.dataset_version} generated={result.data.provenance.generated_at} />}
    </div>
  );
}
