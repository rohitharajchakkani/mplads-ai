import { Bar, BarChart, CartesianGrid, Cell, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { ExpenditureByDimension, GeographyRow, HouseRow, StatusRow, TrendRow } from "../api/types";
import { formatCompactCurrency, formatInteger } from "../lib/format";
import { EmptyState } from "./DataState";

const blue = "#1a5a96";
const green = "#23755d";
const palette = ["#1a5a96", "#23755d", "#b16b18", "#7a4c97", "#0f766e", "#b14242"];

const ChartTooltip = ({ active, payload, label, currency = false }: { active?: boolean; payload?: Array<{ value?: number | string; name?: string; color?: string }>; label?: string; currency?: boolean }) => active && payload?.length ? <div className="rounded-lg border border-line bg-white px-3 py-2 text-xs shadow-panel"><p className="mb-1 font-medium text-ink">{label}</p>{payload.map((item, index) => <p key={`${item.name}-${index}`} className="flex justify-between gap-6 text-slate-600"><span>{item.name}</span><span className="font-medium" style={{ color: item.color }}>{currency ? formatCompactCurrency(item.value) : formatInteger(item.value)}</span></p>)}</div> : null;

function ChartTable({ rows }: { rows: object[] }) {
  const records = rows as Array<Record<string, unknown>>;
  const columns = [...new Set(records.flatMap((row) => Object.keys(row)))];
  if (!columns.length) return null;
  return <details className="mt-4 rounded-md border border-line bg-slate-50 p-3"><summary className="cursor-pointer text-sm font-medium text-ink">Inspect supporting table</summary><div className="mt-3 overflow-x-auto"><table className="min-w-full text-left text-xs"><thead><tr className="border-b border-line text-slate-500">{columns.map((column) => <th key={column} className="px-2 py-2 font-medium">{column.replaceAll("_", " ")}</th>)}</tr></thead><tbody>{records.map((row, index) => <tr key={index} className="border-b border-slate-100 last:border-0">{columns.map((column) => <td key={column} className="px-2 py-2 text-slate-700">{row[column] == null || row[column] === "" ? "Not available" : String(row[column])}</td>)}</tr>)}</tbody></table></div></details>;
}

export function StatusChart({ rows }: { rows: StatusRow[] }) {
  if (!rows.length) return <EmptyState title="No work-status data" detail="No source status values are available for the selected filters." />;
  return <><div className="h-72" aria-label="Work counts by source status"><ResponsiveContainer width="100%" height="100%"><BarChart data={rows} layout="vertical" margin={{ left: 4, right: 20 }}><CartesianGrid stroke="#e7edf3" horizontal={false} /><XAxis type="number" tickFormatter={formatInteger} tick={{ fontSize: 12 }} /><YAxis dataKey="source_status" type="category" width={126} tick={{ fontSize: 11 }} /><Tooltip content={<ChartTooltip />} /><Bar dataKey="work_count" name="Works" fill={blue} radius={[0, 4, 4, 0]} /></BarChart></ResponsiveContainer></div><ChartTable rows={rows} /></>;
}

export function ExpenditureTrendChart({ rows }: { rows: TrendRow[] }) {
  if (!rows.length) return <EmptyState title="No expenditure trend available" detail="No expenditure data is available for this selection." />;
  const data = rows.map((row) => ({ ...row, amount: Number(row.amount ?? 0) }));
  return <><div className="h-72" aria-label="Expenditure by month"><ResponsiveContainer width="100%" height="100%"><LineChart data={data} margin={{ left: 6, right: 16 }}><CartesianGrid stroke="#e7edf3" vertical={false} /><XAxis dataKey="period" tick={{ fontSize: 11 }} minTickGap={26} /><YAxis tickFormatter={formatCompactCurrency} width={76} tick={{ fontSize: 11 }} /><Tooltip content={<ChartTooltip currency />} /><Line type="monotone" dataKey="amount" name="Expenditure" stroke={green} strokeWidth={2.5} dot={false} activeDot={{ r: 4 }} /></LineChart></ResponsiveContainer></div><ChartTable rows={rows} /></>;
}

export function StateChart({ rows }: { rows: GeographyRow[] }) {
  const data = rows.slice(0, 10);
  if (!data.length) return <EmptyState title="No state summary available" detail="No state records match the selected filters." />;
  return <><div className="h-80" aria-label="Leading states by work count"><ResponsiveContainer width="100%" height="100%"><BarChart data={data} layout="vertical" margin={{ left: 4, right: 20 }}><CartesianGrid stroke="#e7edf3" horizontal={false} /><XAxis type="number" tickFormatter={formatInteger} tick={{ fontSize: 12 }} /><YAxis dataKey="value" type="category" width={128} tick={{ fontSize: 11 }} /><Tooltip content={<ChartTooltip />} /><Bar dataKey="work_count" name="Works" fill={blue} radius={[0, 4, 4, 0]} /></BarChart></ResponsiveContainer></div><ChartTable rows={data} /></>;
}

export function HouseChart({ rows }: { rows: HouseRow[] }) {
  if (!rows.length) return <EmptyState title="No house comparison available" detail="Comparison data is unavailable for the selected filters." />;
  return <><div className="h-72" aria-label="Works by House"><ResponsiveContainer width="100%" height="100%"><BarChart data={rows} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}><CartesianGrid stroke="#e7edf3" vertical={false} /><XAxis dataKey="house" tickFormatter={(value) => value.replace("_", " ")} tick={{ fontSize: 11 }} /><YAxis tickFormatter={formatInteger} width={60} tick={{ fontSize: 11 }} /><Tooltip content={<ChartTooltip />} /><Bar dataKey="total_canonical_works" name="Canonical works" radius={[4, 4, 0, 0]}>{rows.map((row, index) => <Cell key={row.house} fill={palette[index % palette.length]} />)}</Bar></BarChart></ResponsiveContainer></div><ChartTable rows={rows} /></>;
}

export function ExpenditureByHouseChart({ rows }: { rows: ExpenditureByDimension["rows"] }) {
  if (!rows.length) return <EmptyState title="No House expenditure available" detail="No expenditure data is available for this selection." />;
  const data = rows.map((row) => ({ ...row, house: row.value ?? "Not available", expenditure: Number(row.expenditure) }));
  return <><div className="h-72" aria-label="Expenditure by House"><ResponsiveContainer width="100%" height="100%"><BarChart data={data} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}><CartesianGrid stroke="#e7edf3" vertical={false} /><XAxis dataKey="house" tickFormatter={(value) => String(value).replace("_", " ")} tick={{ fontSize: 11 }} /><YAxis tickFormatter={formatCompactCurrency} width={76} tick={{ fontSize: 11 }} /><Tooltip content={<ChartTooltip currency />} /><Bar dataKey="expenditure" name="Expenditure" radius={[4, 4, 0, 0]}>{data.map((row, index) => <Cell key={`${row.house}-${index}`} fill={palette[index % palette.length]} />)}</Bar></BarChart></ResponsiveContainer></div><ChartTable rows={data} /></>;
}
