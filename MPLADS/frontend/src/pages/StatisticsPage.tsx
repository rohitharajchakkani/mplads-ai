import { useCallback } from "react";
import { Banknote, FileCheck2, ReceiptText } from "lucide-react";
import { api } from "../api/client";
import { ExpenditureByHouseChart, ExpenditureTrendChart, StateChart } from "../components/Charts";
import { ErrorState, LoadingBlock } from "../components/DataState";
import { MetricCard } from "../components/MetricCard";
import { PageHeader } from "../components/PageHeader";
import { Panel } from "../components/Panel";
import { ReportActions } from "../components/ReportActions";
import { SourceIndicator } from "../components/SourceIndicator";
import { useApi } from "../hooks/useApi";
import { formatCompactCurrency, formatCurrency, formatInteger } from "../lib/format";

export default function StatisticsPage() {
  const financialRequest = useCallback((signal: AbortSignal) => api.financialSummary({}, signal), []);
  const houseRequest = useCallback((signal: AbortSignal) => api.financialByHouse({}, signal), []);
  const stateRequest = useCallback((signal: AbortSignal) => api.stateSummary({}, signal), []);
  const trendRequest = useCallback((signal: AbortSignal) => api.expenditureTrend({}, signal), []);
  const financial = useApi(financialRequest, [financialRequest]);
  const houses = useApi(houseRequest, [houseRequest]);
  const states = useApi(stateRequest, [stateRequest]);
  const trend = useApi(trendRequest, [trendRequest]);
  const reportRows = financial.data ? [{ label: "Total expenditure", value: financial.data.data.total_expenditure }, { label: "Expenditure transactions", value: financial.data.data.transaction_count }, { label: "Unmatched expenditure transactions", value: financial.data.data.unmatched_expenditure_transactions }] : [];
  return <div><PageHeader eyebrow="Public analytical overview" title="Statistics" description="Backend-produced financial, geographic and trend statistics from the active dataset release." /><section id="statistics-report">{financial.data ? <div className="mb-6 flex flex-wrap items-center justify-between gap-3 rounded-lg border border-line bg-white px-4 py-3 shadow-sm"><div><p className="text-sm font-semibold text-ink">Current statistics report</p><p className="mt-1 text-xs text-slate-500">Export the current financial summary or generate a print-safe analytical report.</p></div><ReportActions title="MPLADS Statistics Report" summary="Current active-release financial and analytical statistics." rows={reportRows} provenance={financial.data.provenance} reportSelector="#statistics-report" /></div> : null}<section className="grid gap-4 md:grid-cols-3">{financial.loading && !financial.data ? <LoadingBlock /> : financial.error && !financial.data ? <ErrorState error={financial.error} onRetry={financial.reload} /> : financial.data ? <><MetricCard label="Total expenditure" value={formatCompactCurrency(financial.data.data.total_expenditure)} exactValue={formatCurrency(financial.data.data.total_expenditure)} description="Sum of active source expenditure transactions." icon={Banknote} /><MetricCard label="Expenditure transactions" value={formatInteger(financial.data.data.transaction_count)} description="Linked transaction-grain records in the active dataset." icon={ReceiptText} /><MetricCard label="Unmatched expenditure transactions" value={formatInteger(financial.data.data.unmatched_expenditure_transactions)} description="Transactions without a canonical work link; this is a source quality metric, not a monitoring finding." icon={FileCheck2} /></> : null}</section><div className="mt-6 grid gap-6 xl:grid-cols-2"><Panel title="Expenditure trend" description="Date-backed monthly expenditure from the active source.">{trend.loading && !trend.data ? <LoadingBlock /> : trend.error && !trend.data ? <ErrorState error={trend.error} onRetry={trend.reload} /> : trend.data?.data.data_available ? <ExpenditureTrendChart rows={trend.data.data.rows} /> : <p className="text-sm text-slate-600">{trend.data?.data.message ?? "No expenditure data is available for this selection."}</p>}</Panel><Panel title="Expenditure by House" description="Total expenditure amounts grouped by House.">{houses.loading && !houses.data ? <LoadingBlock /> : houses.error && !houses.data ? <ErrorState error={houses.error} onRetry={houses.reload} /> : houses.data ? <ExpenditureByHouseChart rows={houses.data.data.rows} /> : null}</Panel><Panel title="State comparison" description="Canonical work counts by State / UT source value." className="xl:col-span-2">{states.loading && !states.data ? <LoadingBlock /> : states.error && !states.data ? <ErrorState error={states.error} onRetry={states.reload} /> : states.data ? <StateChart rows={states.data.data.rows} /> : null}</Panel></div>{financial.data && <div className="mt-6"><SourceIndicator provenance={financial.data.provenance} /></div>}</section></div>;
}
