import { useCallback } from "react";
import { Building2, CheckCircle2, Landmark, MapPinned, Users } from "lucide-react";
import { Link, useParams } from "react-router-dom";
import { api } from "../api/client";
import type { DetailData } from "../api/types";
import { ExpenditureTrendChart, StatusChart } from "../components/Charts";
import { ErrorState, LoadingBlock } from "../components/DataState";
import { MetricCard } from "../components/MetricCard";
import { PageHeader } from "../components/PageHeader";
import { Panel } from "../components/Panel";
import { SourceIndicator } from "../components/SourceIndicator";
import { useApi } from "../hooks/useApi";
import { displayHouse, formatCompactCurrency, formatCurrency, formatInteger } from "../lib/format";

type DetailType = "mp" | "state" | "district";

function Details({ data, type }: { data: DetailData; type: DetailType }) {
  const metrics = data.metrics;
  const heading = type === "mp" ? data.name : type === "state" ? data.name : data.district_or_ida;
  const context = type === "mp" ? [["House", displayHouse(data.house)], ["State", data.state ?? "Not available"], ["Constituency", data.constituency ?? "Not available"]] : type === "state" ? [["State / UT", data.name ?? "Not available"]] : [["State", data.state ?? "Not available"], ["District / Implementing Authority", data.district_or_ida ?? "Not available"]];
  return <><PageHeader eyebrow={type === "mp" ? "MP record" : type === "state" ? "State record" : "District / IDA record"} title={heading ?? "Record detail"} description="All values below are calculated from the active dataset selection for this source record." actions={<Link to="/works" className="button-secondary">Explore works</Link>} /><dl className="grid gap-4 rounded-xl border border-line bg-white p-5 sm:grid-cols-2 lg:grid-cols-3">{context.map(([label, value]) => <div key={label}><dt className="text-xs font-medium uppercase tracking-wide text-slate-500">{label}</dt><dd className="mt-1 font-medium text-ink">{value}</dd></div>)}</dl><nav className="mt-4 flex flex-wrap gap-2" aria-label="Continue exploring"><Link to="/states" className="button-secondary">States</Link><Link to="/districts" className="button-secondary">Districts / IDA</Link><Link to="/mps" className="button-secondary">MPs</Link><Link to="/works" className="button-secondary">Works</Link></nav><section className="mt-6 grid gap-4 sm:grid-cols-2 xl:grid-cols-4"><MetricCard label="Total works" value={formatInteger(metrics.total_canonical_works)} description="Distinct canonical work records connected to this entity." icon={Building2} /><MetricCard label="Recommended" value={formatInteger(metrics.recommended_works)} description="Works with recommendation records connected to this entity." icon={Landmark} /><MetricCard label="Sanctioned" value={formatInteger(metrics.sanctioned_works)} description="Works with sanction records connected to this entity." icon={CheckCircle2} /><MetricCard label="Completed" value={formatInteger(metrics.completed_works)} description="Works with completion records connected to this entity." icon={CheckCircle2} /><MetricCard label="Sanction amount" value={formatCompactCurrency(metrics.total_sanction_amount)} exactValue={formatCurrency(metrics.total_sanction_amount)} description="Sum of linked source sanction amounts." icon={Landmark} /><MetricCard label="Expenditure" value={formatCompactCurrency(metrics.total_expenditure)} exactValue={formatCurrency(metrics.total_expenditure)} description="Sum of linked source expenditure transactions." icon={Landmark} /><MetricCard label="MP records" value={formatInteger(metrics.mp_count)} description="Distinct MP source names in this selection." icon={Users} /><MetricCard label="District / IDA records" value={formatInteger(metrics.district_or_ida_count)} description="Distinct source District / Implementing Authority values in this selection." icon={MapPinned} /></section><div className="mt-6 grid gap-6 xl:grid-cols-2"><Panel title="Source work status" description="The source status vocabulary is retained without semantic remapping."><StatusChart rows={data.status_distribution.rows} /><p className="mt-3 text-xs text-slate-500">{data.status_distribution.normalization}</p></Panel><Panel title="Expenditure trend" description="Monthly values are shown only where source dates are available.">{data.expenditure_trend.data_available ? <ExpenditureTrendChart rows={data.expenditure_trend.rows} /> : <p className="rounded-lg bg-slate-50 p-4 text-sm text-slate-600">{data.expenditure_trend.message ?? "Information not available in supplied source data."}</p>}</Panel></div></>;
}

export default function EntityDetailPage({ type }: { type: DetailType }) {
  const { id = "" } = useParams();
  const decodedId = decodeURIComponent(id);
  const request = useCallback((signal: AbortSignal) => type === "mp" ? api.mp(decodedId, signal) : type === "state" ? api.state(decodedId, signal) : api.district(decodedId, signal), [decodedId, type]);
  const result = useApi(request, [request]);
  if (result.loading && !result.data) return <LoadingBlock label="Loading record detail…" />;
  if (result.error && !result.data) return <ErrorState error={result.error} onRetry={result.reload} title={result.error.message.includes("not found") ? "Resource not found." : undefined} />;
  return result.data ? <div><Details data={result.data.data} type={type} /><div className="mt-6"><SourceIndicator provenance={result.data.provenance} /></div></div> : null;
}
