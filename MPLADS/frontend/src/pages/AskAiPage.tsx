import { useMemo, useState } from "react";
import { Bot, Send, Sparkles } from "lucide-react";
import { Link } from "react-router-dom";
import { api, ApiError } from "../api/client";
import type { AskAiResponse, VisualizationSpec } from "../api/types";
import { EmptyState, ErrorState } from "../components/DataState";
import { PageHeader } from "../components/PageHeader";
import { Panel } from "../components/Panel";
import { ReportActions } from "../components/ReportActions";
import { SmartVisualization } from "../components/SmartVisualization";
import { formatDateTime } from "../lib/format";

const examples = [
  "Which states have the highest expenditure?",
  "Show work status by House.",
  "Compare Lok Sabha and Rajya Sabha expenditure.",
  "How many works are completed in Telangana?",
  "What is the review backlog?",
  "Show risk distribution.",
  "How many potential duplicate candidates are there?",
];

type ResultRow = VisualizationSpec["rows"][number];

function errorTitle(error: Error) {
  if (error instanceof ApiError && error.status === 429) return "Ask AI rate limit reached.";
  if (error instanceof ApiError && (error.status === 401 || error.status === 403)) return "Your protected Ask AI session is not authorized.";
  return "Unable to retrieve a verified result.";
}

function primitive(value: unknown): string | number | null | undefined { return typeof value === "string" || typeof value === "number" || value === null ? value : undefined; }

function supportingRows(result?: AskAiResponse): ResultRow[] {
  if (!result) return [];
  if (result.visualization?.rows.length) return result.visualization.rows;
  const data = result.tool_result?.data ?? result.tool_results_summary;
  for (const [key, value] of Object.entries(data ?? {})) {
    if (Array.isArray(value) && value.length && value.every((item) => item && typeof item === "object" && !Array.isArray(item))) {
      return value.slice(0, 100).map((item, index) => {
        const record: ResultRow = { label: String((item as Record<string, unknown>).label ?? (item as Record<string, unknown>).name ?? `${key} ${index + 1}`) };
        for (const [name, cell] of Object.entries(item as Record<string, unknown>)) { const safe = primitive(cell); if (safe !== undefined) record[name] = safe; }
        return record;
      });
    }
    if (value && typeof value === "object" && !Array.isArray(value)) {
      const pairs = Object.entries(value as Record<string, unknown>).filter(([, cell]) => primitive(cell) !== undefined);
      if (pairs.length) return pairs.map(([label, cell]) => ({ label, value: primitive(cell) ?? null }));
    }
  }
  return Object.entries(data ?? {}).filter(([, value]) => primitive(value) !== undefined).map(([label, value]) => ({ label, value: primitive(value) ?? null }));
}

function SupportingDataTable({ rows }: { rows: ResultRow[] }) {
  if (!rows.length) return <EmptyState title="No tabular supporting data" detail="The verified result does not contain a safe tabular representation." />;
  const columns = [...new Set(rows.flatMap((row) => Object.keys(row)))];
  return <div className="overflow-x-auto"><table className="min-w-full text-left text-sm" aria-label="Verified supporting data"><thead className="bg-slate-50 text-xs uppercase tracking-wide text-slate-500"><tr>{columns.map((column) => <th key={column} className="px-3 py-3 font-medium">{column.replaceAll("_", " ")}</th>)}</tr></thead><tbody>{rows.map((row, index) => <tr key={`${row.label ?? "row"}-${index}`} className="border-t border-line/70"><>{columns.map((column) => <td key={column} className="px-3 py-3 text-slate-700">{row[column] == null || row[column] === "" ? "Not available" : String(row[column])}</td>)}</></tr>)}</tbody></table></div>;
}

export function AskAiPage() {
  const [question, setQuestion] = useState("");
  const [result, setResult] = useState<AskAiResponse>();
  const [error, setError] = useState<Error>();
  const [loading, setLoading] = useState(false);
  const rows = useMemo(() => supportingRows(result), [result]);

  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    const cleanQuestion = question.trim().replace(/\s+/g, " ");
    if (!cleanQuestion) return;
    setLoading(true); setError(undefined);
    try { setResult(await api.askAi(cleanQuestion)); } catch (caught) { setError(caught instanceof Error ? caught : new Error("Unable to ask AI.")); } finally { setLoading(false); }
  };

  return <div>
    <PageHeader eyebrow="Authorized monitoring" title="MPLADS AI Assistant" description="Ask questions about MPLADS data and monitoring evidence. The backend retrieves verified facts first; Gemini can only explain the bounded authorized result." />
    <section className="rounded-lg border border-blue-100 bg-blue-50/70 p-4 text-sm text-slate-700"><div className="flex gap-3"><Sparkles className="mt-0.5 size-5 shrink-0 text-blue" aria-hidden="true" /><div><strong className="text-ink">Read-only, scope-aware assistance.</strong><p className="mt-1 leading-6">Ask AI cannot change records, widen your authorization, access files, run SQL, or reveal secrets. A visualization is only shown when the verified result supports it.</p></div></div></section>
    <section className="mt-6 grid gap-6 xl:grid-cols-[minmax(0,1.3fr)_minmax(17rem,0.7fr)]">
      <Panel title="Ask a question" description="Use a natural question about the active MPLADS dataset or monitoring evidence."><form className="space-y-4" onSubmit={submit}><label className="field-label">Ask about MPLADS data or monitoring evidence<textarea className="field-control min-h-36 resize-y leading-6" value={question} maxLength={1000} onChange={(event) => setQuestion(event.target.value)} placeholder="Ask about MPLADS data or monitoring evidence…" /></label><div className="flex flex-wrap items-center justify-between gap-3"><p className="text-xs text-slate-500">{question.length}/1000 characters</p><button className="button-primary" disabled={loading || !question.trim()} type="submit"><Send className="size-4" />{loading ? "Retrieving verified result…" : "Ask AI"}</button></div></form></Panel>
      <Panel title="Try a verified question" description="Selecting an example only fills the question box. It does not call the provider or preload an answer."><ul className="space-y-1">{examples.map((item) => <li key={item}><button type="button" className="w-full rounded-md px-2 py-2 text-left text-sm text-blue transition hover:bg-blue-50 hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue" onClick={() => setQuestion(item)}>{item}</button></li>)}</ul></Panel>
    </section>
    {error && <div className="mt-6"><ErrorState title={errorTitle(error)} error={error} /></div>}
    {result && <section id="ask-ai-report" className="mt-6 space-y-6">
      <Panel title="Answer" description={`Intent: ${result.intent.replaceAll("_", " ")}`}><div className="flex gap-3"><div className="grid size-9 shrink-0 place-items-center rounded-md bg-blue-50 text-blue"><Bot className="size-5" /></div><p className="whitespace-pre-wrap text-sm leading-7 text-slate-800">{result.answer}</p></div>{result.warnings.length ? <p className="mt-4 rounded-md border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900">{result.warnings.join(" ")}</p> : null}{result.tool_result?.success ? (
        <div className="mt-5 border-t border-line pt-4">
          <ReportActions
            title="MPLADS Ask AI Analysis Report"
            summary={`Verified query analysis for: "${question.trim()}"`}
            sections={[
              {
                title: "Question & Verified Finding",
                subtitle: `Query Intent: ${result.intent.replaceAll("_", " ")}`,
                narrative: result.answer,
                evidenceItems: [
                  { label: "Exact Question", value: question.trim() },
                  { label: "Intent", value: result.intent.replaceAll("_", " ") },
                  { label: "Backend Tool Executed", value: result.provenance.tool_used ?? "Verified database analytics" },
                  { label: "Query Scope", value: Object.entries(result.provenance.filters_applied).map(([k, v]) => `${k}: ${v}`).join(", ") || "National / Unfiltered" },
                ],
              },
              ...(result.visualization ? [{
                title: "Verified Analytical Visual",
                subtitle: result.visualization.description || "Visual representation of verified backend query data",
                chartRows: result.visualization.rows,
                chartType: (result.visualization.chart_type === "PIE" || result.visualization.chart_type === "DISTRIBUTION" ? "DONUT" : result.visualization.chart_type === "LINE" ? "LINE" : "BAR") as any,
                rows: result.visualization.rows,
              }] : []),
              ...(rows.length && (!result.visualization || result.visualization.rows !== rows) ? [{
                title: "Supporting Result Data",
                subtitle: "Complete verified tabular response records",
                rows: rows,
              }] : []),
            ]}
            rows={result.visualization?.rows?.length ? result.visualization.rows : rows}
            chartRows={result.visualization?.rows?.length ? result.visualization.rows : rows}
            filters={result.provenance.filters_applied}
            provenance={result.provenance}
            disabled={Boolean(result.clarification_required)}
            reportSelector="#ask-ai-report"
          />
        </div>
      ) : null}</Panel>
      {result.clarification_required ? <Panel title="Clarification needed" description="This is a valid question, but the current scope has multiple matching entities."><p className="text-sm text-slate-700">Refine your question with one of the matching entities below.</p><ul className="mt-3 space-y-2 text-sm">{result.clarification_options?.map((choice) => <li key={`${choice.entity_type}-${choice.label}`} className="rounded-md border border-line bg-slate-50 p-3"><span className="font-medium text-ink">{choice.label}</span><span className="ml-2 text-slate-500">{choice.entity_type}</span>{choice.navigation_link ? <Link className="ml-3 text-blue hover:underline" to={choice.navigation_link.href}>{choice.navigation_link.label}</Link> : null}</li>)}</ul></Panel> : null}
      {result.tool_result && !result.tool_result.success ? <Panel title="No verified records" description="The query ran inside the active authorized scope, but it returned no substantive data."><p className="text-sm text-slate-700">Use a broader authorized question or continue in the linked monitoring page when available.</p></Panel> : null}
      {result.visualization ? <Panel title="Verified visualization" description="The chart and accessible table are generated only from the same verified backend tool result."><SmartVisualization spec={result.visualization} /></Panel> : null}
      {rows.length && !result.clarification_required ? <Panel title="Verified supporting data" description="This table is the bounded backend result used for the response. Internal tool payloads are not exposed."><SupportingDataTable rows={rows} /></Panel> : null}
      <Panel title="Source and provenance"><dl className="grid gap-3 text-sm sm:grid-cols-2"><div><dt className="text-slate-500">Source</dt><dd className="font-medium">MPLADS active dataset</dd></div><div><dt className="text-slate-500">Release</dt><dd className="font-medium">{result.dataset_version ?? "Not available"}</dd></div><div><dt className="text-slate-500">Backend tool</dt><dd className="font-medium">{result.provenance.tool_used ?? "No tool executed"}</dd></div><div><dt className="text-slate-500">Generated</dt><dd className="font-medium">{formatDateTime(result.generated_at)}</dd></div></dl><p className="mt-4 text-xs leading-5 text-slate-500">{result.grounding.explanation}</p></Panel>
      {result.navigation_links.length ? <Panel title="Continue exploring"><div className="flex flex-wrap gap-2">{result.navigation_links.map((link) => <Link key={link.href} className="button-secondary" to={link.href}>{link.label}</Link>)}</div></Panel> : null}
    </section>}
  </div>;
}
