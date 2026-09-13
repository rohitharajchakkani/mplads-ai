import { Area, AreaChart, Bar, BarChart, CartesianGrid, Cell, Legend, Line, LineChart, Pie, PieChart, ResponsiveContainer, Scatter, ScatterChart, Tooltip, XAxis, YAxis } from "recharts";
import type { VisualizationSpec } from "../api/types";
import { formatCompactCurrency, formatInteger } from "../lib/format";
import { EmptyState } from "./DataState";

const palette = ["#1a5a96", "#23755d", "#b16b18", "#7a4c97", "#0f766e", "#b14242", "#56677d", "#b45309", "#0e7490", "#7c3a8a", "#4d7c0f", "#9f1239"];

function numeric(value: string | number | null | undefined) { return typeof value === "number" ? value : Number(value ?? 0); }
function label(value: string | number | null | undefined) { return value == null || value === "" ? "Not available" : String(value); }
function valueFormatter(unit?: string | null) { return (value: string | number) => unit?.toLowerCase().includes("expenditure") ? formatCompactCurrency(value) : formatInteger(value); }

function SupportingTable({ rows }: { rows: VisualizationSpec["rows"] }) {
  if (!rows.length) return null;
  const columns = [...new Set(rows.flatMap((row) => Object.keys(row)))];
  return <details className="mt-4 rounded-lg border border-line bg-slate-50 p-3"><summary className="cursor-pointer text-sm font-medium text-ink">Inspect supporting table</summary><div className="mt-3 overflow-x-auto"><table className="min-w-full text-left text-xs"><thead><tr className="border-b border-line text-slate-500">{columns.map((column) => <th key={column} className="px-2 py-2 font-medium">{column.replaceAll("_", " ")}</th>)}</tr></thead><tbody>{rows.map((row, index) => <tr key={`${row.label ?? "row"}-${index}`} className="border-b border-slate-100 last:border-0">{columns.map((column) => <td key={column} className="px-2 py-2 text-slate-700">{label(row[column])}</td>)}</tr>)}</tbody></table></div></details>;
}

function Heatmap({ spec, data, formatValue }: { spec: VisualizationSpec; data: Array<Record<string, string | number | null>>; formatValue: (value: string | number) => string }) {
  const maximum = Math.max(0, ...data.flatMap((row) => spec.series.map((series) => numeric(row[series.key]))));
  return <div className="overflow-x-auto" role="img" aria-label={`${spec.title} heatmap`}><div className="min-w-[640px] space-y-1"><div className="grid gap-1 text-[10px] text-slate-600" style={{ gridTemplateColumns: `minmax(9rem, 1.5fr) repeat(${spec.series.length}, minmax(4.5rem, 1fr))` }}><span>{spec.y_axis ?? "Group"}</span>{spec.series.map((series) => <span key={series.key} className="truncate text-center" title={series.label}>{series.label}</span>)}</div>{data.map((row) => <div key={label(row.label)} className="grid gap-1" style={{ gridTemplateColumns: `minmax(9rem, 1.5fr) repeat(${spec.series.length}, minmax(4.5rem, 1fr))` }}><span className="truncate py-2 text-xs text-slate-700" title={label(row.label)}>{label(row.label)}</span>{spec.series.map((series) => { const value = numeric(row[series.key]); const opacity = maximum ? 0.12 + (0.78 * value) / maximum : 0.08; return <span key={series.key} className="rounded px-1 py-2 text-center text-xs font-medium text-slate-900" style={{ backgroundColor: `rgb(26 90 150 / ${opacity})` }} title={`${label(row.label)} · ${series.label}: ${formatValue(value)}`}>{formatValue(value)}</span>; })}</div>)}</div></div>;
}

export function SmartVisualization({ spec }: { spec: VisualizationSpec }) {
  if (!spec.data_available) return <EmptyState title={spec.title} detail={spec.message ?? spec.description} />;
  const data = spec.rows.map((row) => ({ ...row, label: label(row.label), value: numeric(row.value) }));
  const formatValue = valueFormatter(spec.unit);
  const tooltip = <Tooltip formatter={(value: unknown) => formatValue(numeric(Array.isArray(value) ? value[0] : value as string | number | null))} />;
  const categorySeries = spec.series.length ? spec.series : [{ key: "value", label: spec.unit ?? "Value" }];
  let visual: React.ReactNode;
  if (spec.chart_type === "KPI") {
    const first = data[0];
    visual = <div className="rounded-lg bg-blue-50 p-5"><p className="text-xs font-medium uppercase tracking-wide text-slate-600">{first?.label ?? spec.unit}</p><p className="mt-2 text-3xl font-semibold text-ink">{formatValue(first?.value ?? 0)}</p></div>;
  } else if (spec.chart_type === "TABLE") {
    visual = <p className="rounded-lg bg-slate-50 p-4 text-sm text-slate-700" role="img" aria-label={`${spec.title} table visualization`}>The selected result is best understood as a detailed supporting table.</p>;
  } else if (spec.chart_type === "PIE" || spec.chart_type === "DONUT" || spec.chart_type === "DISTRIBUTION") {
    const donut = spec.chart_type !== "PIE";
    visual = <div className="h-80" role="img" aria-label={`${spec.title} ${donut ? "donut" : "pie"} chart`}><ResponsiveContainer width="100%" height="100%"><PieChart><Pie data={data} dataKey="value" nameKey="label" outerRadius={104} innerRadius={donut ? 58 : 0} label={({ name, value }) => `${name}: ${formatValue(numeric(value))}`}>{data.map((row, index) => <Cell key={`${row.label}-${index}`} fill={palette[index % palette.length]} />)}</Pie>{tooltip}<Legend /></PieChart></ResponsiveContainer></div>;
  } else if (spec.chart_type === "LINE") {
    visual = <div className="h-80" role="img" aria-label={`${spec.title} line chart`}><ResponsiveContainer width="100%" height="100%"><LineChart data={data} margin={{ left: 8, right: 16 }}><CartesianGrid stroke="#e7edf3" vertical={false} /><XAxis dataKey="label" tick={{ fontSize: 11 }} minTickGap={24} /><YAxis tickFormatter={formatValue} width={82} tick={{ fontSize: 11 }} />{tooltip}<Line type="monotone" dataKey="value" name={spec.unit ?? "Value"} stroke={palette[1]} strokeWidth={2.5} dot={false} activeDot={{ r: 4 }} /></LineChart></ResponsiveContainer></div>;
  } else if (spec.chart_type === "AREA") {
    visual = <div className="h-80" role="img" aria-label={`${spec.title} area chart`}><ResponsiveContainer width="100%" height="100%"><AreaChart data={data} margin={{ left: 8, right: 16 }}><CartesianGrid stroke="#e7edf3" vertical={false} /><XAxis dataKey="label" tick={{ fontSize: 11 }} minTickGap={24} /><YAxis tickFormatter={formatValue} width={82} tick={{ fontSize: 11 }} />{tooltip}<Area type="monotone" dataKey="value" name={spec.unit ?? "Value"} stroke={palette[1]} fill={palette[1]} fillOpacity={0.24} strokeWidth={2.5} /></AreaChart></ResponsiveContainer></div>;
  } else if (spec.chart_type === "SCATTER") {
    visual = <div className="h-80" role="img" aria-label={`${spec.title} scatter plot`}><ResponsiveContainer width="100%" height="100%"><ScatterChart margin={{ left: 8, right: 16 }}><CartesianGrid stroke="#e7edf3" /><XAxis type="number" dataKey="x" name={spec.x_axis ?? "X"} tickFormatter={formatInteger} width={82} tick={{ fontSize: 11 }} /><YAxis type="number" dataKey="y" name={spec.y_axis ?? "Y"} tickFormatter={formatValue} width={92} tick={{ fontSize: 11 }} />{tooltip}<Scatter data={data} name={spec.y_axis ?? "Value"} fill={palette[0]} /></ScatterChart></ResponsiveContainer></div>;
  } else if (spec.chart_type === "HEATMAP") {
    visual = <Heatmap spec={spec} data={data} formatValue={formatValue} />;
  } else if (spec.chart_type === "HISTOGRAM") {
    visual = <div className="h-80" role="img" aria-label={`${spec.title} histogram`}><ResponsiveContainer width="100%" height="100%"><BarChart data={data} margin={{ left: 2, right: 16 }} barCategoryGap={1}><CartesianGrid stroke="#e7edf3" vertical={false} /><XAxis dataKey="label" tick={{ fontSize: 10 }} interval="preserveStartEnd" /><YAxis tickFormatter={formatInteger} width={58} tick={{ fontSize: 11 }} />{tooltip}<Bar dataKey="value" name={spec.unit ?? "Frequency"} fill={palette[3]} radius={[2, 2, 0, 0]} /></BarChart></ResponsiveContainer></div>;
  } else if (spec.chart_type === "HORIZONTAL_BAR") {
    visual = <div className="h-96" role="img" aria-label={`${spec.title} ranked bar chart`}><ResponsiveContainer width="100%" height="100%"><BarChart data={data.slice(0, 30)} layout="vertical" margin={{ left: 4, right: 24 }}><CartesianGrid stroke="#e7edf3" horizontal={false} /><XAxis type="number" tickFormatter={formatValue} tick={{ fontSize: 11 }} /><YAxis dataKey="label" type="category" width={145} tick={{ fontSize: 11 }} />{tooltip}<Bar dataKey="value" name={spec.unit ?? "Value"} fill={palette[0]} radius={[0, 4, 4, 0]} /></BarChart></ResponsiveContainer></div>;
  } else if (spec.chart_type === "GROUPED_BAR" || spec.chart_type === "STACKED_BAR") {
    const stacked = spec.chart_type === "STACKED_BAR";
    visual = <div className="h-96" role="img" aria-label={`${spec.title} ${stacked ? "stacked" : "grouped"} bar chart`}><ResponsiveContainer width="100%" height="100%"><BarChart data={data.slice(0, 30)} margin={{ left: 2, right: 16 }}><CartesianGrid stroke="#e7edf3" vertical={false} /><XAxis dataKey="label" tick={{ fontSize: 11 }} interval="preserveStartEnd" /><YAxis tickFormatter={formatValue} width={82} tick={{ fontSize: 11 }} />{tooltip}<Legend />{categorySeries.map((series, index) => <Bar key={series.key} dataKey={series.key} name={series.label} stackId={stacked ? "composition" : undefined} fill={palette[index % palette.length]} radius={stacked ? undefined : [4, 4, 0, 0]} />)}</BarChart></ResponsiveContainer></div>;
  } else {
    visual = <div className="h-80" role="img" aria-label={`${spec.title} bar chart`}><ResponsiveContainer width="100%" height="100%"><BarChart data={data.slice(0, 30)} margin={{ left: 2, right: 16 }}><CartesianGrid stroke="#e7edf3" vertical={false} /><XAxis dataKey="label" tick={{ fontSize: 11 }} interval="preserveStartEnd" /><YAxis tickFormatter={formatValue} width={82} tick={{ fontSize: 11 }} />{tooltip}<Bar dataKey="value" name={spec.unit ?? "Value"} fill={palette[0]} radius={[4, 4, 0, 0]} /></BarChart></ResponsiveContainer></div>;
  }
  return <figure aria-label={spec.title}><figcaption className="mb-3"><h3 className="font-semibold text-ink">{spec.title}</h3><p className="mt-1 text-sm text-slate-600">{spec.description}</p><p className="mt-1 text-xs text-slate-500">{spec.record_count} displayed record{spec.record_count === 1 ? "" : "s"}{spec.unit ? ` · Unit: ${spec.unit}` : ""}</p>{spec.selection ? <p className="mt-1 text-xs text-slate-500">Chart selection: {spec.selection.rationale}</p> : null}</figcaption>{visual}<SupportingTable rows={spec.rows} /></figure>;
}
