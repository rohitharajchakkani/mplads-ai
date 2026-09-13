import { useCallback } from "react";
import { ArrowRight, BarChart3, Building2, FileSearch, Landmark, Map, Search, ShieldCheck, Users } from "lucide-react";
import { Link } from "react-router-dom";
import { api } from "../api/client";
import type { DashboardMetrics } from "../api/types";
import { ErrorState, LoadingBlock } from "../components/DataState";
import { MetricCard } from "../components/MetricCard";
import { SourceIndicator } from "../components/SourceIndicator";
import { useApi } from "../hooks/useApi";
import { formatCompactCurrency, formatCurrency, formatInteger } from "../lib/format";

const processSteps = [
  ["Explore", "Search the public record by representative, place, work, or source attribute.", Search],
  ["Analyze", "Use filters and API-generated comparisons to examine implementation patterns.", BarChart3],
  ["Understand", "Read every result alongside its data release and source context.", FileSearch],
  ["Review", "Use the separate protected workspace for authorized programme review.", ShieldCheck],
] as const;

const pathways = [
  ["Work register", "Browse individual works and follow their source-backed lifecycle and financial evidence.", "/works", Building2, "Public context"],
  ["Find a record", "Search works, MPs, States and District / IDA values from the active release.", "/search", Search, "Locate evidence"],
  ["Authorized monitoring", "Inspect anomaly signals, risk indicators, alerts and review workflows when authorized.", "/monitoring", ShieldCheck, "Protected intelligence"],
] as const;

function SummaryCards({ metrics }: { metrics: DashboardMetrics }) {
  return <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4"><MetricCard label="Canonical works" value={formatInteger(metrics.total_canonical_works)} description="Distinct canonical work records in the active dataset release." icon={Building2} /><MetricCard label="Total expenditure" value={formatCompactCurrency(metrics.total_expenditure)} exactValue={formatCurrency(metrics.total_expenditure)} description="Sum of expenditure transactions linked to canonical works in the active release." icon={BarChart3} /><MetricCard label="MP records" value={formatInteger(metrics.mp_count)} description="Distinct source MP names represented by the active canonical-work selection." icon={Users} /><MetricCard label="States / UTs" value={formatInteger(metrics.state_count)} description="Distinct source state values represented by the active canonical-work selection." icon={Map} /></div>;
}

export default function HomePage() {
  const request = useCallback((signal: AbortSignal) => api.dashboardSummary({}, signal), []);
  const summary = useApi(request, [request]);
  return <div className="space-y-14 sm:space-y-16">
    <section className="relative isolate overflow-hidden rounded-lg border border-line bg-white shadow-panel" aria-labelledby="home-title">
      <div className="gov-rule absolute inset-x-0 top-0 h-1" aria-hidden="true" />
      <div className="absolute inset-y-0 right-0 hidden w-[48%] bg-[radial-gradient(circle_at_70%_35%,rgba(23,105,170,0.16),transparent_42%),linear-gradient(135deg,transparent_49.5%,rgba(23,105,170,0.04)_50%,transparent_50.5%)] lg:block" aria-hidden="true" />
      <div className="relative grid gap-8 px-6 py-12 sm:px-10 sm:py-16 lg:grid-cols-[minmax(0,1fr)_18rem] lg:gap-12">
        <div className="max-w-3xl"><p className="eyebrow">MPLADS intelligence workspace</p><h1 id="home-title" className="section-title mt-5 max-w-3xl text-4xl font-semibold leading-[1.06] sm:text-5xl lg:text-6xl">Evidence-led MPLADS anomaly and risk monitoring.</h1><p className="mt-5 max-w-2xl text-lg leading-8 text-slate-700 sm:text-xl">Understand implementation context publicly, then use authorized monitoring to prioritize suspicious patterns, inefficiencies and evidence-led review.</p><p className="mt-4 max-w-2xl leading-7 text-slate-600">Every displayed public figure comes from the active release. Monitoring findings stay behind server-enforced authorization and remain decision support—not conclusions of wrongdoing.</p><div className="mt-8 flex flex-wrap gap-3"><Link className="button-primary" to="/monitoring">Open authorized monitoring <ArrowRight className="size-4" aria-hidden="true" /></Link><Link className="button-secondary" to="/works">Browse work register</Link><Link className="button-secondary" to="/dashboard">View implementation context</Link></div></div>
        <aside className="relative self-end rounded-md border border-blue-100 bg-blue-50/80 p-5 lg:mb-1" aria-label="Portal guidance"><div className="flex items-center gap-2 text-sm font-semibold text-navy"><Landmark className="size-4 text-blue" aria-hidden="true" />A decision-support workspace</div><p className="mt-3 text-sm leading-6 text-slate-700">Locate a work, inspect the evidence, assess a monitoring signal, then use the human review workflow when action is needed.</p><div className="mt-5 border-t border-blue-100 pt-4 text-xs leading-5 text-slate-600"><span className="font-semibold text-[#18794e]">Public context</span> for exploration. <span className="font-semibold text-blue">Protected access</span> for signals, evidence and review.</div></aside>
      </div>
    </section>

    <section aria-labelledby="live-summary"><div className="mb-5 flex flex-wrap items-end justify-between gap-3 border-b border-line pb-5"><div><p className="eyebrow">Active data release</p><h2 id="live-summary" className="section-title mt-3 text-3xl font-semibold">What the current record contains</h2><p className="mt-2 max-w-2xl leading-6 text-slate-600">A live overview of the active analytical release—not pre-filled sample figures.</p></div>{summary.data && <SourceIndicator compact provenance={summary.data.provenance} />}</div>{summary.loading && !summary.data ? <LoadingBlock label="Loading active dataset summary…" /> : summary.error && !summary.data ? <ErrorState error={summary.error} onRetry={summary.reload} /> : summary.data ? <SummaryCards metrics={summary.data.data} /> : null}</section>

    <section aria-labelledby="ways-in"><div className="mb-6 flex flex-wrap items-end justify-between gap-3"><div><p className="eyebrow">Explore the record</p><h2 id="ways-in" className="section-title mt-3 text-3xl font-semibold">Choose a starting point</h2></div><Link to="/search" className="button-quiet">Search the dataset <ArrowRight className="size-3.5" aria-hidden="true" /></Link></div><div className="grid gap-px overflow-hidden rounded-lg border border-line bg-line md:grid-cols-2">{pathways.map(([title, description, to, Icon, tag]) => <Link key={title} to={to} className="group bg-white p-6 transition hover:bg-blue-50/50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-blue"><div className="flex items-start justify-between gap-5"><div className="rounded-md border border-blue-100 bg-blue-50 p-2.5 text-blue"><Icon className="size-5" aria-hidden="true" /></div><span className="text-xs font-bold uppercase tracking-[0.12em] text-slate-500">{tag}</span></div><h3 className="mt-7 text-lg font-semibold text-ink">{title}</h3><p className="mt-2 max-w-md text-sm leading-6 text-slate-600">{description}</p><span className="mt-5 inline-flex items-center gap-2 text-sm font-semibold text-blue">Open view <ArrowRight className="size-4 transition group-hover:translate-x-1" aria-hidden="true" /></span></Link>)}</div></section>

    <section className="rounded-lg border border-line bg-white p-6 shadow-sm sm:p-8" aria-labelledby="how-it-works"><div className="grid gap-8 lg:grid-cols-[minmax(0,0.7fr)_minmax(0,1.3fr)]"><div><p className="eyebrow">How to use this portal</p><h2 id="how-it-works" className="section-title mt-3 text-3xl font-semibold">Evidence before conclusions.</h2><p className="mt-4 leading-7 text-slate-600">The interface is designed for public understanding and programme teams: trace a result to the active release, examine its limits, and use protected workflows only when you are authorized.</p><Link className="button-secondary mt-6" to="/about">Read methodology &amp; limitations</Link></div><div className="grid gap-4 sm:grid-cols-2">{processSteps.map(([title, description, Icon], index) => <article key={title} className="relative border-l-2 border-blue-100 pl-5"><span className="absolute -left-[9px] top-0 grid size-4 place-items-center rounded-full bg-white text-[9px] font-bold text-blue ring-1 ring-blue-200">{index + 1}</span><Icon className="size-5 text-blue" aria-hidden="true" /><h3 className="mt-4 font-semibold text-ink">{title}</h3><p className="mt-2 text-sm leading-6 text-slate-600">{description}</p></article>)}</div></div>
    </section>
  </div>;
}
