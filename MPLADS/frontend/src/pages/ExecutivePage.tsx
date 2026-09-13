import { useCallback } from "react";
import { Link } from "react-router-dom";
import { Activity, AlertTriangle, ClipboardCheck, GitCompareArrows, Lightbulb, Timer } from "lucide-react";
import { api, ApiError } from "../api/client";
import { EmptyState, ErrorState, LoadingBlock } from "../components/DataState";
import { MetricCard } from "../components/MetricCard";
import { PageHeader } from "../components/PageHeader";
import { Panel } from "../components/Panel";
import { ReportActions } from "../components/ReportActions";
import { SmartVisualization } from "../components/SmartVisualization";
import { useApi } from "../hooks/useApi";
import { formatInteger } from "../lib/format";

const readable = (value: string) => value.replaceAll("_", " ");
function failure(error: Error, retry: () => void) { return <ErrorState title={error instanceof ApiError && error.status === 403 ? "You do not have permission to view this executive scope." : "Unable to load executive intelligence."} error={error} onRetry={retry} />; }
function ExecutiveDistribution({ title, values, description = "Current persisted authorized evidence." }: { title: string; values: Record<string, number>; description?: string }) {
  const rows = Object.entries(values).map(([label, value]) => ({ label: readable(label), value }));
  return rows.length ? <SmartVisualization spec={{ title, description, chart_type: "DISTRIBUTION", x_axis: "Category", y_axis: "Count", unit: "Count", series: [{ key: "value", label: "Count" }], rows, record_count: rows.length, data_available: true }} /> : <EmptyState title="No current summary values are available for this scope." />;
}

export function ExecutivePage() {
  const summary = useApi(useCallback((signal: AbortSignal) => api.executiveSummary(signal), []), []);
  const attention = useApi(useCallback((signal: AbortSignal) => api.executiveAttention({}, signal), []), []);
  const trends = useApi(useCallback((signal: AbortSignal) => api.executiveTrends(signal), []), []);
  const geography = useApi(useCallback((signal: AbortSignal) => api.executiveGeography(signal), []), []);
  const comparison = useApi(useCallback((signal: AbortSignal) => api.executiveComparison(signal), []), []);
  const drilldown = useApi(useCallback((signal: AbortSignal) => api.executiveDrilldown({}, signal), []), []);
  if (summary.loading || attention.loading) return <LoadingBlock label="Loading executive intelligence from persisted evidence…" />;
  if (summary.error) return failure(summary.error, summary.reload);
  if (attention.error) return failure(attention.error, attention.reload);
  if (!summary.data || !attention.data) return null;
  const data = summary.data;
  const reviewTotal = Object.values(data.review_backlog).reduce((total, value) => total + value, 0);
  const reportRows = [
    { label: "Monitored works", value: data.total_monitored_works }, { label: "Signals", value: data.total_signals }, { label: "Alerts", value: data.total_alerts }, { label: "High-priority alerts", value: data.high_priority_alerts }, { label: "High-priority risk works", value: data.high_priority_risk_works }, { label: "Review backlog", value: reviewTotal }, { label: "Active escalations", value: data.active_escalations }, { label: "Available peer comparisons", value: data.available_benchmarks }, { label: "Active recommendations", value: data.active_recommendations },
  ];
  const executiveKpis = [
    { label: "Attention Level", value: attention.data.level, description: `Signal count: ${attention.data.signal_count}` },
    { label: "Monitored Works", value: formatInteger(data.total_monitored_works) },
    { label: "High-Priority Alerts", value: formatInteger(data.high_priority_alerts) },
    { label: "Review Backlog", value: formatInteger(reviewTotal) },
  ];
  const executiveChartRows = Object.entries(attention.data.high_priority_categories).length
    ? Object.entries(attention.data.high_priority_categories).map(([label, value]) => ({ label: readable(label), value }))
    : [
        { label: "Alerts", value: data.total_alerts },
        { label: "High priority alerts", value: data.high_priority_alerts },
        { label: "High priority risk", value: data.high_priority_risk_works },
        { label: "Review backlog", value: reviewTotal },
        { label: "Escalations", value: data.active_escalations },
      ];
  const executiveSections = [
    {
      title: "Current Monitoring Attention",
      subtitle: `Level: ${attention.data.level} · Derived from review workload, escalations, high-priority alerts, and high-priority risk works`,
      kpis: executiveKpis,
      narrative: attention.data.drivers.length
        ? `Active Attention Drivers:\n${attention.data.drivers.map((d) => `• ${d.label}: ${formatInteger(d.count)}`).join("\n")}`
        : "No current attention drivers present in authorized scope.",
    },
    {
      title: "Review Workload by Status",
      subtitle: "Persisted human review backlog in the authorized scope",
      chartType: "DONUT" as const,
      chartRows: Object.entries(data.review_backlog).map(([label, value]) => ({ label: readable(label), value })),
      rows: Object.entries(data.review_backlog).map(([status, count]) => ({ status: readable(status), count })),
    },
    {
      title: "Geographic Concentration",
      subtitle: "Absolute workload and high-priority risk rate by State / UT",
      rows: geography.data?.rows?.length
        ? geography.data.rows.map((row) => ({
            state: row.state,
            monitored_works: row.monitored_works,
            high_priority_rate: row.high_priority_risk_rate === null ? "Not available" : `${(row.high_priority_risk_rate * 100).toFixed(1)}%`,
          }))
        : [],
      emptyMessage: geography.data?.message ?? "No material geographic concentration identified from current data.",
    },
    {
      title: "House Comparison",
      subtitle: "Neutral comparison of source-supported works across Houses",
      chartType: "BAR" as const,
      chartRows: comparison.data?.rows?.map((row) => ({ label: readable(row.house), value: row.monitored_works })) ?? [],
      rows: comparison.data?.rows?.map((row) => ({ house: readable(row.house), monitored_works: row.monitored_works, available_benchmarks: row.available_benchmarks })) ?? [],
    },
    {
      title: "Analytical Run Trends",
      subtitle: "Historical changes across verified completed runs",
      rows: trends.data?.available && trends.data.rows?.length
        ? trends.data.rows.map((row) => ({
            category: readable(row.category),
            current_value: row.current_value,
            absolute_change: row.absolute_change ?? "N/A",
            percentage_change: row.percentage_change !== null ? `${row.percentage_change}%` : "N/A",
          }))
        : [],
      emptyMessage: trends.data?.message ?? "Trend unavailable: insufficient historical runs.",
    },
  ];

  return <div><PageHeader eyebrow="Authorized executive intelligence" title="Executive command center" description="Understand → Prioritize → Drill down → Act. This layer summarizes persisted evidence; it does not create findings." /><section id="executive-report"><div className="mb-6 flex flex-wrap items-center justify-between gap-3 rounded-lg border border-line bg-white px-4 py-3 shadow-sm"><div><p className="text-sm font-semibold text-ink">Executive report</p><p className="mt-1 text-xs text-slate-500">Includes the current authorized scope, persisted summaries, and only valid trends.</p></div><ReportActions title="MPLADS Executive Intelligence Report" summary="Current executive evidence in the authorized scope." rows={reportRows} chartRows={executiveChartRows} kpis={executiveKpis} sections={executiveSections} filters={attention.data.scope} provenance={data.provenance} reportSelector="#executive-report" /></div>
    <section className={`rounded-xl border p-5 ${attention.data.level === "HIGH" ? "border-red-200 bg-red-50" : attention.data.level === "MODERATE" ? "border-amber-200 bg-amber-50" : "border-blue-200 bg-blue-50"}`}><p className="text-xs font-semibold uppercase tracking-wide">Current monitoring attention</p><div className="mt-2 flex flex-wrap items-end justify-between gap-4"><div><h2 className="text-3xl font-semibold text-ink">{attention.data.level}</h2><p className="mt-1 text-sm text-slate-700">Signal Count: {formatInteger(attention.data.signal_count)}. Derived from review workload, escalations, high-priority alerts, and high-priority risk works.</p></div><p className="text-sm text-slate-600">Active release: {attention.data.provenance.dataset_version}</p></div>{attention.data.drivers.length ? <ul className="mt-4 flex flex-wrap gap-2">{attention.data.drivers.map((driver) => <li key={driver.label}><Link className="button-secondary" to={driver.href}>{driver.label}: {formatInteger(driver.count)}</Link></li>)}</ul> : <p className="mt-4 text-sm text-slate-700">No current attention drivers are present in this authorized scope.</p>}</section>
    <section className="mt-6 grid gap-4 sm:grid-cols-2 xl:grid-cols-4"><MetricCard label="Monitored works" value={formatInteger(data.total_monitored_works)} description="Persisted risk-assessment records in scope." icon={Activity} /><MetricCard label="High-priority alerts" value={formatInteger(data.high_priority_alerts)} description="High and very-high severity alerts." icon={AlertTriangle} /><MetricCard label="Review backlog" value={formatInteger(reviewTotal)} description="Human review workload; not a finding." icon={ClipboardCheck} /><MetricCard label="Available peer comparisons" value={formatInteger(data.available_benchmarks)} description="Comparable same-House benchmark results." icon={GitCompareArrows} /></section>
    <section className="mt-6 grid gap-6 xl:grid-cols-2"><Panel title="Review and recommendation activity" description="Current persisted workflow counts."><ExecutiveDistribution title="Review workload by status" values={data.review_backlog} description="Persisted review-case workload in the authorized scope." /></Panel><Panel title="Peer and signal context" description="Contextual evidence, not a performance score."><ExecutiveDistribution title="High-priority categories" values={attention.data.high_priority_categories} description="Current attention drivers from persisted monitoring evidence." /></Panel></section>
    <section className="mt-6 grid gap-6 xl:grid-cols-2"><Panel title="Geographic concentration" description="Absolute workload and high-priority risk rate by state; no inferred conclusions.">{geography.loading ? <LoadingBlock /> : geography.error ? failure(geography.error, geography.reload) : geography.data?.rows.length ? <table className="w-full text-left text-sm"><thead><tr><th>State</th><th>Works</th><th>High-priority rate</th></tr></thead><tbody>{geography.data.rows.slice(0, 6).map((row) => <tr key={row.state} className="border-t border-line"><td className="py-2">{row.state}</td><td>{formatInteger(row.monitored_works)}</td><td>{row.high_priority_risk_rate === null ? "Not available" : `${(row.high_priority_risk_rate * 100).toFixed(1)}%`}</td></tr>)}</tbody></table> : <EmptyState title={geography.data?.message ?? "No material concentration identified from the current data."} />}</Panel><Panel title="House comparison" description="Neutral comparison of source-supported measures.">{comparison.loading ? <LoadingBlock /> : comparison.error ? failure(comparison.error, comparison.reload) : <table className="w-full text-left text-sm"><thead><tr><th>House</th><th>Works</th><th>Benchmarks</th></tr></thead><tbody>{comparison.data?.rows.map((row) => <tr key={row.house} className="border-t border-line"><td className="py-2">{readable(row.house)}</td><td>{formatInteger(row.monitored_works)}</td><td>{formatInteger(row.available_benchmarks)}</td></tr>)}</tbody></table>}</Panel></section>
    <section className="mt-6 grid gap-6 xl:grid-cols-2"><Panel title="Trends" description="Only completed analytical runs are compared.">{trends.loading ? <LoadingBlock /> : trends.data?.available ? <ul className="space-y-2 text-sm">{trends.data.rows.map((row) => <li key={row.category}><strong>{readable(row.category)}:</strong> {formatInteger(row.current_value)}; change {row.absolute_change === null ? "unavailable" : formatInteger(row.absolute_change)}{row.percentage_change === null ? "" : ` (${row.percentage_change}%)`}</li>)}</ul> : <EmptyState title={trends.data?.message ?? "Trend unavailable: insufficient historical runs."} icon={<Timer className="size-5" />} />}</Panel><Panel title="Priority queue" description="Persisted alerts ordered by severity, then recency.">{drilldown.loading ? <LoadingBlock /> : drilldown.data?.priority_queue.length ? <ul className="space-y-3 text-sm">{drilldown.data.priority_queue.slice(0, 5).map((item) => <li key={item.alert_id} className="border-b border-line pb-2"><Link className="font-medium text-blue hover:underline" to={`/monitoring/alerts/${encodeURIComponent(item.alert_id)}`}>{item.title}</Link><p>{readable(item.severity)} · {readable(item.category)}</p></li>)}</ul> : <EmptyState title="No priority alerts are currently generated for this scope." icon={<Lightbulb className="size-5" />} />}</Panel></section>
  </section></div>;
}
