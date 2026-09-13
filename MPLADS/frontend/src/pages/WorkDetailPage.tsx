import { useCallback, useEffect, useState } from "react";
import { Check, CircleDollarSign, ClipboardList, Landmark, ReceiptText } from "lucide-react";
import { Link, useParams } from "react-router-dom";
import { api } from "../api/client";
import type { ReviewCase, RiskWork, WorkDetailData } from "../api/types";
import { ErrorState, LoadingBlock, EmptyState } from "../components/DataState";
import { MetricCard } from "../components/MetricCard";
import { PageHeader } from "../components/PageHeader";
import { Panel } from "../components/Panel";
import { ReportActions, type ReportKpi } from "../components/ReportActions";
import { SourceIndicator } from "../components/SourceIndicator";
import { SourceText, cleanSourceText } from "../components/SourceText";
import { StatusBadge } from "../components/StatusBadge";
import { useApi } from "../hooks/useApi";
import { displayHouse, formatCurrency, formatDate } from "../lib/format";

function Evidence({ title, count, description, children }: { title: string; count: number; description: string; children?: React.ReactNode }) {
  return <article className="relative pb-6 pl-9 last:pb-0"><span className="absolute left-0 top-0 grid size-6 place-items-center rounded-full bg-blue-50 text-blue"><Check className="size-3.5" aria-hidden="true" /></span><h3 className="font-medium text-ink">{title}</h3><p className="mt-1 text-sm text-slate-600">{count ? `${count} linked source record${count === 1 ? "" : "s"}.` : "Information not available in supplied source data."}</p>{count > 0 && <p className="mt-1 text-xs text-slate-500">{description}</p>}{children}</article>;
}

function WorkContent({ data }: { data: WorkDetailData }) {
  const work = data.work;
  const sanctionAmounts = data.sanctions.map((sanction) => Number(sanction.amount)).filter(Number.isFinite);
  const sanctionTotal = sanctionAmounts.length ? sanctionAmounts.reduce((total, amount) => total + amount, 0) : undefined;
  
  const [riskData, setRiskData] = useState<RiskWork | null>(null);
  const [reviewCase, setReviewCase] = useState<ReviewCase | null>(null);

  useEffect(() => {
    let active = true;
    api.riskWork(work.canonical_work_key)
      .then((res) => { if (active) setRiskData(res); })
      .catch(() => { /* silent catch when unauthenticated or unassessed */ });

    api.reviewCases({ search: work.canonical_work_key })
      .then((res) => {
        if (active && res?.items?.length) {
          const match = res.items.find((item) => item.canonical_work_key === work.canonical_work_key) ?? res.items[0];
          setReviewCase(match);
        }
      })
      .catch(() => { /* silent catch when unauthenticated */ });

    return () => { active = false; };
  }, [work.canonical_work_key]);

  const observedStatus = data.completions.length
    ? "Completed"
    : data.expenditure.transaction_count > 0
    ? "In Progress / Underway"
    : data.sanctions.length
    ? "Sanctioned"
    : data.recommendations.length
    ? "Recommended"
    : "Registered in Source";

  const narrative = `Official dossier for Work ID ${work.work_id ?? work.canonical_work_key} (${displayHouse(work.house)} - ${work.state ?? "State unassigned"}). Observed lifecycle status is "${observedStatus}". Sanction amount is ${sanctionTotal !== undefined ? formatCurrency(sanctionTotal) : "not available in source records"}; total expenditure disbursed is ${formatCurrency(data.expenditure.total)} across ${data.expenditure.transaction_count} transaction${data.expenditure.transaction_count === 1 ? "" : "s"}.`;

  const reportRows = [
    { attribute: "Work ID", value: work.work_id ?? work.canonical_work_key },
    { attribute: "Canonical Work Key", value: work.canonical_work_key },
    { attribute: "Work Description", value: work.work_description ?? "Description not available in source record." },
    { attribute: "House", value: displayHouse(work.house) },
    { attribute: "Member of Parliament (MP)", value: work.mp ?? "Not available in source record" },
    { attribute: "State / UT", value: work.state ?? "Not available in source record" },
    { attribute: "District / Implementing Authority", value: work.district_or_ida ?? "Not available in source record" },
    { attribute: "Constituency", value: work.constituency ?? "Not available in source record" },
    { attribute: "Observed Lifecycle Status", value: observedStatus },
    { attribute: "Financial Year", value: work.financial_year ?? "Not available in source record" },
    { attribute: "Source Work Category", value: work.source_work_category ?? "Not available in source record" },
    { attribute: "Total Sanction Amount", value: sanctionTotal !== undefined ? formatCurrency(sanctionTotal) : "Not available" },
    { attribute: "Total Expenditure Disbursed", value: formatCurrency(data.expenditure.total) },
    { attribute: "Expenditure Transactions", value: String(data.expenditure.transaction_count) },
    { attribute: "Linked Recommendations", value: String(data.recommendations.length) },
    { attribute: "Earliest Recommendation Date", value: data.recommendations[0]?.date ? formatDate(data.recommendations[0].date) : "None recorded" },
    { attribute: "Sanction Date", value: data.sanctions[0]?.sanction_date ? formatDate(data.sanctions[0].sanction_date) : "None recorded" },
    { attribute: "First Expenditure Date", value: data.expenditure.first_expenditure_date ? formatDate(data.expenditure.first_expenditure_date) : "None recorded" },
    { attribute: "Latest Expenditure Date", value: data.expenditure.latest_expenditure_date ? formatDate(data.expenditure.latest_expenditure_date) : "None recorded" },
    { attribute: "Completion Date", value: data.completions[0]?.completion_date ? formatDate(data.completions[0].completion_date) : "None recorded" },
    ...(riskData ? [
      { attribute: "Monitoring Priority Band", value: riskData.risk_band },
      { attribute: "Monitoring Priority Score", value: `${riskData.normalized_score.toFixed(1)} / 100` },
    ] : [
      { attribute: "Monitoring Assessment", value: "Standard monitoring; no priority alerts generated in authorized scope" }
    ]),
    ...(reviewCase ? [
      { attribute: "Linked Review Case", value: `${reviewCase.case_id} (${reviewCase.status.replaceAll("_", " ")}, Priority: ${reviewCase.priority})` },
      { attribute: "Review Case Assignee", value: reviewCase.assignee ?? "Unassigned" },
    ] : []),
    { attribute: "Data Source", value: "MPLADS active dataset" },
  ];

  const kpis: ReportKpi[] = [
    { label: "Status", value: observedStatus },
    { label: "Sanction Amount", value: sanctionTotal !== undefined ? formatCurrency(sanctionTotal) : "Not available" },
    { label: "Total Expenditure", value: formatCurrency(data.expenditure.total) },
    { label: "Transactions", value: String(data.expenditure.transaction_count) },
    { label: "Recommendations", value: String(data.recommendations.length) },
    ...(riskData ? [{ label: "Monitoring Risk", value: riskData.risk_band, description: `Score: ${riskData.normalized_score.toFixed(1)} / 100` }] : []),
  ];

  const chartRows = [
    ...(sanctionTotal !== undefined ? [{ label: "Sanction amount", value: sanctionTotal }] : []),
    { label: "Expenditure disbursed", value: Number(data.expenditure.total) || 0 },
    ...data.expenditure.transactions.slice(0, 4).map((tx, idx) => ({
      label: tx.vendor_name ? (tx.vendor_name.length > 14 ? `${tx.vendor_name.slice(0, 13)}…` : tx.vendor_name) : `Transaction ${idx + 1}`,
      value: Number(tx.amount) || 0,
    })),
  ];

  const workSections = [
    {
      title: "Administrative & Lifecycle Overview",
      subtitle: `Canonical work: ${work.canonical_work_key}`,
      kpis: kpis,
      evidenceItems: [
        { label: "Work ID", value: work.work_id ?? work.canonical_work_key },
        { label: "Canonical Key", value: work.canonical_work_key },
        { label: "House", value: displayHouse(work.house) },
        { label: "MP", value: work.mp ?? "Not available" },
        { label: "State", value: work.state ?? "Not available" },
        { label: "District / IDA", value: work.district_or_ida ?? "Not available" },
        { label: "Constituency", value: work.constituency ?? "Not available" },
        { label: "Financial Year", value: work.financial_year ?? "Not available" },
        { label: "Observed Status", value: observedStatus },
        { label: "Work Description", value: cleanSourceText(work.work_description) },
      ],
      narrative: narrative,
    },
    {
      title: "Lifecycle Milestones & Evidence",
      subtitle: "Verified chronological stages linked from source records",
      evidenceItems: [
        { label: "Recommended Stage", value: `${data.recommendations.length} records (${data.recommendations[0]?.date ? formatDate(data.recommendations[0].date) : "Undated"})` },
        { label: "Sanctioned Stage", value: `${data.sanctions.length} records (${data.sanctions[0]?.sanction_date ? formatDate(data.sanctions[0].sanction_date) : "Undated"})` },
        { label: "Expenditure Disbursed", value: `${data.expenditure.transaction_count} transaction(s)` },
        { label: "Completion Stage", value: `${data.completions.length} records (${data.completions[0]?.completion_date ? formatDate(data.completions[0].completion_date) : "Undated"})` },
      ],
    },
    {
      title: "Financial Transactions",
      subtitle: "Linked expenditure transactions from source records",
      chartType: "BAR" as const,
      chartRows: chartRows,
      rows: data.expenditure.transactions.length
        ? data.expenditure.transactions.map((tx) => ({
            date: formatDate(tx.date),
            vendor: cleanSourceText(tx.vendor_name),
            status: tx.payment_status ?? "—",
            amount: formatCurrency(tx.amount),
          }))
        : [{ date: "—", vendor: "No linked expenditure records", status: "—", amount: "—" }],
      columns: ["date", "vendor", "status", "amount"],
    },
    ...(riskData
      ? [
          {
            title: "Authorized Monitoring & Risk Intelligence",
            subtitle: "Protected monitoring signals for authorized officials",
            kpis: [
              { label: "Priority Score", value: `${riskData.normalized_score.toFixed(1)} / 100`, description: "Overall risk index" },
              { label: "Risk Band", value: riskData.risk_band, description: "Evaluated severity" },
              { label: "Review Case", value: reviewCase ? reviewCase.case_id : "None linked", description: reviewCase ? reviewCase.status : "No case" },
            ],
          },
        ]
      : []),
  ];

  return (
    <div id="work-detail-report">
      <PageHeader
        eyebrow="Canonical work record"
        title={work.work_id ?? work.canonical_work_key}
        description={
          <SourceText
            text={work.work_description}
            showRawToggle
            className="text-base leading-7 text-slate-600"
          />
        }
        actions={
          <div className="shrink-0 pt-2 sm:pt-0" aria-label="Work report actions">
            <ReportActions
              title={`MPLADS Work Detail Report — ${work.work_id ?? work.canonical_work_key}`}
              summary={`Official administrative, financial, and monitoring dossier for Work ID ${work.work_id ?? work.canonical_work_key}.`}
              narrative={narrative}
              rows={reportRows}
              chartRows={chartRows}
              kpis={kpis}
              sections={workSections}
              filters={{
                house: displayHouse(work.house),
                state: work.state ?? undefined,
                district_or_ida: work.district_or_ida ?? undefined,
                financial_year: work.financial_year ?? undefined,
                status: observedStatus,
              }}
              provenance={data.provenance}
              reportSelector="#work-detail-report"
              hideCsv
            />
          </div>
        }
      />
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <MetricCard label="Sanction amount" value={sanctionTotal === undefined ? "Not available" : formatCurrency(sanctionTotal)} description="Sum of linked sanction amounts where a source amount is available for this canonical work." icon={Landmark} />
        <MetricCard label="Expenditure" value={formatCurrency(data.expenditure.total)} description="Sum of linked expenditure transactions for this canonical work." icon={CircleDollarSign} />
        <MetricCard label="Transactions" value={String(data.expenditure.transaction_count)} description="Number of linked source expenditure transactions." icon={ReceiptText} />
        <MetricCard label="Recommendations" value={String(data.recommendations.length)} description="Number of linked recommendation records available for this work." icon={ClipboardList} />
      </div>
      <div className="mt-6 grid gap-6 xl:grid-cols-[1.1fr_0.9fr]">
        <Panel title="Work overview" description="Administrative context supplied by the canonical work record.">
          <dl className="grid gap-x-6 gap-y-4 sm:grid-cols-2">
            {[["Canonical work key", work.canonical_work_key], ["House", displayHouse(work.house)], ["MP", work.mp], ["State", work.state], ["District / Implementing Authority", work.district_or_ida], ["Constituency", work.constituency], ["Financial year", work.financial_year], ["Source work category", work.source_work_category]].map(([label, value]) => (
              <div key={label as string}>
                <dt className="text-xs font-medium uppercase tracking-wide text-slate-500">{label}</dt>
                <dd className="mt-1 text-sm font-medium leading-6 text-ink">{typeof value === "string" && value ? value : "Information not available in supplied source data."}</dd>
              </div>
            ))}
          </dl>
        </Panel>
        <Panel title="Lifecycle evidence" description="Stages appear only when linked source records support them.">
          <div className="border-l border-blue-200">
            <Evidence title="Recommended" count={data.recommendations.length} description={data.recommendations[0]?.date ? `Earliest available date: ${formatDate(data.recommendations[0].date)}` : "No recommendation date is available."} />
            <Evidence title="Sanctioned" count={data.sanctions.length} description={data.sanctions[0]?.sanction_date ? `Available sanction date: ${formatDate(data.sanctions[0].sanction_date)}` : "No sanction date is available."} />
            <Evidence title="Payments / expenditure" count={data.expenditure.transaction_count} description={data.expenditure.first_expenditure_date ? `From ${formatDate(data.expenditure.first_expenditure_date)} to ${formatDate(data.expenditure.latest_expenditure_date)}.` : "No expenditure date is available."} />
            <Evidence title="Completed" count={data.completions.length} description={data.completions[0]?.completion_date ? `Available completion date: ${formatDate(data.completions[0].completion_date)}` : "No completion date is available."} />
          </div>
        </Panel>
      </div>
      <div className="mt-6 grid gap-6 xl:grid-cols-2">
        <Panel title="Financial information" description="Linked expenditure transactions, up to the API’s source-record limit.">
          {data.expenditure.transactions.length ? (
            <div className="overflow-x-auto">
              <table className="min-w-[560px] w-full text-left text-sm" data-report-table="true">
                <thead>
                  <tr className="border-b border-line text-xs uppercase tracking-wide text-slate-500">
                    <th className="pb-3 pr-4 font-medium">Date</th>
                    <th className="pb-3 pr-4 font-medium">Vendor</th>
                    <th className="pb-3 pr-4 font-medium">Source payment status</th>
                    <th className="pb-3 text-right font-medium">Amount</th>
                  </tr>
                </thead>
                <tbody>
                  {data.expenditure.transactions.map((item, index) => (
                    <tr key={`${item.date ?? "undated"}-${index}`} className="border-b border-line/70 last:border-0">
                      <td className="py-3 pr-4">{formatDate(item.date)}</td>
                      <td className="py-3 pr-4">{item.vendor_name ?? "Not available"}</td>
                      <td className="py-3 pr-4"><StatusBadge value={item.payment_status} /></td>
                      <td className="py-3 text-right font-medium">{formatCurrency(item.amount)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <EmptyState title="No linked expenditure records" detail="Information not available in supplied source data." />
          )}
          {data.expenditure.transactions_truncated && <p className="mt-3 text-xs text-slate-500">The API limited this display to the first available transaction records.</p>}
        </Panel>
        <Panel title="Authorized investigation" description="Risk, alert, duplicate, and review evidence remains protected and is only available after server authorization.">
          {riskData ? (
            <div className="mb-4 rounded-lg border border-line bg-slate-50 p-4">
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold uppercase tracking-wider text-slate-500">Monitoring Assessment</span>
                <StatusBadge value={riskData.risk_band} />
              </div>
              <p className="mt-2 text-sm font-semibold text-ink">
                Priority score: {riskData.normalized_score.toFixed(1)} / 100
              </p>
              {reviewCase && (
                <p className="mt-1 text-xs text-slate-600">
                  Linked Review Case: <strong className="text-ink">{reviewCase.case_id}</strong> ({reviewCase.status.replaceAll("_", " ")}, Priority: {reviewCase.priority})
                </p>
              )}
            </div>
          ) : (
            <p className="text-sm leading-6 text-slate-700">Use the protected workspace to examine source-backed monitoring signals for records within your authorized scope.</p>
          )}
          <Link className="mt-4 inline-block text-sm font-semibold text-blue hover:underline" to="/monitoring" data-report-exclude="true">Open authorized monitoring</Link>
        </Panel>
        <Panel title="Data quality & provenance" description="Traceability information for this canonical work.">
          <p className="text-sm leading-6 text-slate-700">Some source records cannot be linked to a canonical work because the supplied source does not contain a resolvable Work ID. This work detail only presents records linked to the canonical key.</p>
          <dl className="mt-5 grid gap-3 text-sm">
            <div>
              <dt className="text-xs font-medium uppercase tracking-wide text-slate-500">Data source</dt>
              <dd className="mt-1 font-medium text-ink">MPLADS active dataset</dd>
            </div>
            <div data-report-exclude="true">
              <dt className="text-xs font-medium uppercase tracking-wide text-slate-500">Traceability details</dt>
              <dd className="mt-1">
                <details className="text-xs text-slate-500">
                  <summary className="cursor-pointer hover:underline text-blue">View technical release identifier</summary>
                  <p className="mt-1 font-mono text-[11px] bg-slate-50 p-2 rounded border border-line">Release: {data.provenance.release_version}<br/>Active batch: {data.provenance.batch_id}</p>
                </details>
              </dd>
            </div>
          </dl>
        </Panel>
      </div>
    </div>
  );
}

export default function WorkDetailPage() {
  const params = useParams();
  const key = decodeURIComponent(params["*"] ?? "");
  const request = useCallback((signal: AbortSignal) => api.work(key, signal), [key]);
  const result = useApi(request, [request]);
  if (result.loading && !result.data) return <LoadingBlock label="Loading work detail…" />;
  if (result.error && !result.data) return <ErrorState error={result.error} onRetry={result.reload} title={result.error.message.includes("not found") ? "Work not found." : undefined} />;
  return result.data ? <div><WorkContent data={result.data.data} /><div className="mt-6"><SourceIndicator provenance={result.data.provenance} /></div></div> : null;
}
