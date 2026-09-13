import { Download, FileText, Printer } from "lucide-react";
import { useState } from "react";
import type { Filters } from "../api/types";
import { cleanSourceText } from "./SourceText";

export type ReportProvenance = {
  release_version?: string | null;
  batch_id?: string | null;
  service?: string | null;
  dataset_version?: string | null;
  tool_used?: string | null;
  generated_at?: string | null;
  model?: string | null;
};

export type ReportRow = Record<string, any>;

export type ReportKpi = {
  label: string;
  value: string | number;
  description?: string;
};

export type ReportSeries = {
  key: string;
  label: string;
  color?: string;
};

export type ReportEvidenceItem = {
  label: string;
  value: string | number;
};

export type ReportSection = {
  title: string;
  subtitle?: string;
  narrative?: string;
  kpis?: ReportKpi[];
  chartRows?: ReportRow[];
  chartType?: "BAR" | "DONUT" | "LINE" | "DISTRIBUTION" | "GROUPED";
  chartSeries?: ReportSeries[];
  rows?: ReportRow[];
  columns?: string[];
  evidenceItems?: ReportEvidenceItem[];
  emptyMessage?: string;
  customHtml?: string;
};

export type ReportProps = {
  title: string;
  summary: string;
  subtitle?: string;
  dataSource?: string;
  rows?: ReportRow[];
  chartRows?: ReportRow[];
  filters?: Filters | Record<string, unknown>;
  provenance?: ReportProvenance;
  disabled?: boolean;
  reportSelector?: string;
  narrative?: string;
  kpis?: ReportKpi[];
  chartType?: "BAR" | "DONUT" | "LINE" | "DISTRIBUTION" | "GROUPED";
  sections?: ReportSection[];
  hideCsv?: boolean;
};

function csvCell(value: unknown): string {
  if (value === null || value === undefined) return '""';
  const str = cleanSourceText(String(value));
  return `"${str.replaceAll('"', '""')}"`;
}

function escapeHtml(value: unknown): string {
  if (value === null || value === undefined) return "";
  const cleaned = cleanSourceText(String(value));
  return cleaned
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function safeFileStem(title: string): string {
  return title.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/(^-|-$)/g, "") || "mplads-report";
}

function reportDate(): string {
  return new Intl.DateTimeFormat("en-CA", { year: "numeric", month: "2-digit", day: "2-digit" }).format(new Date()).replaceAll("/", "-");
}

function numeric(value: unknown): number | undefined {
  if (typeof value === "number") return Number.isFinite(value) ? value : undefined;
  if (typeof value !== "string") return undefined;
  const parsed = Number(value.replace(/[^0-9.-]/g, ""));
  return Number.isFinite(parsed) ? parsed : undefined;
}

function formatDisplayValue(value: unknown): string {
  if (value === null || value === undefined || value === "") return "—";
  if (typeof value === "number") return value.toLocaleString("en-IN");
  return escapeHtml(value);
}

function tableMarkup(rows?: ReportRow[], columns?: string[], emptyMessage = "No reportable results are available for the current selection."): string {
  if (!rows || !rows.length) {
    return `<p class="report-empty">${escapeHtml(emptyMessage)}</p>`;
  }
  const cols = columns && columns.length ? columns : [...new Set(rows.flatMap((row) => Object.keys(row)))];
  if (!cols.length) {
    return `<p class="report-empty">${escapeHtml(emptyMessage)}</p>`;
  }

  const thead = `<thead><tr>${cols.map((col) => `<th>${escapeHtml(col.replaceAll("_", " "))}</th>`).join("")}</tr></thead>`;
  const tbody = `<tbody>${rows
    .map(
      (row) =>
        `<tr>${cols
          .map((col) => {
            const raw = row[col];
            return `<td>${formatDisplayValue(raw)}</td>`;
          })
          .join("")}</tr>`
    )
    .join("")}</tbody>`;

  return `<div class="table-wrap"><table>${thead}${tbody}</table></div>`;
}

function donutChartMarkup(rows: ReportRow[], width = 680, height = 240): string {
  const values = rows
    .map((row) => ({
      label: String(row.label ?? row.name ?? row.category ?? row.status ?? "Item"),
      value: numeric(row.value ?? row.count ?? row.amount ?? row.works),
    }))
    .filter((row): row is { label: string; value: number } => row.value !== undefined && row.value > 0)
    .slice(0, 8);

  const total = values.reduce((sum, v) => sum + v.value, 0);
  if (!values.length || total <= 0) return '<p class="report-empty">No categorical distribution data available.</p>';

  const colors = ["#1769aa", "#2e7d32", "#ed6c02", "#9c27b0", "#0288d1", "#d32f2f", "#00897b", "#795548"];
  const radius = 70;
  const innerRadius = 42;
  const cx = 130;
  const cy = 110;
  let currentAngle = 0;

  const slices = values
    .map((v, i) => {
      const angle = (v.value / total) * 360;
      const startAngle = currentAngle;
      const endAngle = currentAngle + angle;
      currentAngle += angle;

      const startRad = (startAngle - 90) * (Math.PI / 180);
      const endRad = (endAngle - 90) * (Math.PI / 180);
      const x1 = cx + radius * Math.cos(startRad);
      const y1 = cy + radius * Math.sin(startRad);
      const x2 = cx + radius * Math.cos(endRad);
      const y2 = cy + radius * Math.sin(endRad);
      const ix1 = cx + innerRadius * Math.cos(startRad);
      const iy1 = cy + innerRadius * Math.sin(startRad);
      const ix2 = cx + innerRadius * Math.cos(endRad);
      const iy2 = cy + innerRadius * Math.sin(endRad);
      const largeArc = angle > 180 ? 1 : 0;

      const path = `M ${x1} ${y1} A ${radius} ${radius} 0 ${largeArc} 1 ${x2} ${y2} L ${ix2} ${iy2} A ${innerRadius} ${innerRadius} 0 ${largeArc} 0 ${ix1} ${iy1} Z`;
      return `<path d="${path}" fill="${colors[i % colors.length]}" stroke="#ffffff" stroke-width="1.5"><title>${escapeHtml(v.label)}: ${v.value.toLocaleString("en-IN")}</title></path>`;
    })
    .join("");

  const legend = values
    .map((v, i) => {
      const pct = ((v.value / total) * 100).toFixed(1);
      return `<g transform="translate(260, ${18 + i * 26})"><rect width="12" height="12" rx="2" fill="${colors[i % colors.length]}"/><text x="20" y="10" font-size="11" fill="#1e293b">${escapeHtml(v.label)}: <strong>${v.value.toLocaleString("en-IN")}</strong> (${pct}%)</text></g>`;
    })
    .join("");

  return `<div class="report-chart-wrap"><svg viewBox="0 0 ${width} ${height}" role="img" aria-label="Distribution chart">${slices}${legend}</svg></div>`;
}

function lineChartMarkup(rows: ReportRow[], width = 680, height = 240): string {
  const points = rows
    .map((row) => ({
      label: String(row.label ?? row.period ?? row.date ?? row.month ?? row.year ?? ""),
      value: numeric(row.value ?? row.amount ?? row.expenditure ?? row.count),
    }))
    .filter((pt): pt is { label: string; value: number } => pt.value !== undefined)
    .slice(0, 24);

  if (points.length < 2) {
    return '<p class="report-empty">Trend unavailable for the selected data.</p>';
  }

  const padding = { top: 24, right: 30, bottom: 50, left: 60 };
  const areaWidth = width - padding.left - padding.right;
  const areaHeight = height - padding.top - padding.bottom;
  const maxVal = Math.max(...points.map((p) => p.value));
  const minVal = Math.min(0, ...points.map((p) => p.value));
  const range = maxVal - minVal || 1;

  const stepX = areaWidth / (points.length - 1);
  const coords = points.map((pt, i) => ({
    x: padding.left + i * stepX,
    y: padding.top + areaHeight - ((pt.value - minVal) / range) * areaHeight,
    label: pt.label,
    value: pt.value,
  }));

  const pathD = coords.reduce((acc, pt, i) => `${acc} ${i === 0 ? "M" : "L"} ${pt.x} ${pt.y}`, "");

  const dots = coords
    .map((pt) => {
      const displayVal = pt.value >= 1000000 ? `${(pt.value / 1000000).toFixed(1)}M` : pt.value >= 1000 ? `${(pt.value / 1000).toFixed(1)}k` : String(Number(pt.value.toFixed(1)));
      return `<circle cx="${pt.x}" cy="${pt.y}" r="3.5" fill="#1769aa" stroke="#ffffff" stroke-width="1.5"><title>${escapeHtml(`${pt.label}: ${pt.value.toLocaleString("en-IN")}`)}</title></circle><text x="${pt.x}" y="${pt.y - 6}" text-anchor="middle" font-size="8.5" font-weight="600" fill="#12355b">${displayVal}</text><text x="${pt.x}" y="${height - padding.bottom + 14}" text-anchor="end" font-size="8.5" fill="#64748b" transform="rotate(-35 ${pt.x} ${height - padding.bottom + 14})">${escapeHtml(pt.label.slice(0, 10))}</text>`;
    })
    .join("");

  return `<div class="report-chart-wrap"><svg viewBox="0 0 ${width} ${height}" role="img" aria-label="Trend chart"><line x1="${padding.left}" y1="${height - padding.bottom}" x2="${width - padding.right}" y2="${height - padding.bottom}" stroke="#cbd5e1" stroke-width="1.5"/><line x1="${padding.left}" y1="${padding.top}" x2="${padding.left}" y2="${height - padding.bottom}" stroke="#cbd5e1" stroke-width="1.5"/><path d="${pathD}" fill="none" stroke="#1769aa" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/>${dots}</svg></div>`;
}

function barChartMarkup(rows: ReportRow[], width = 680, height = 250): string {
  const values = rows
    .map((row) => ({
      label: String(row.label ?? row.name ?? row.work ?? row.category ?? row.entity ?? row.state ?? "Record"),
      value: numeric(row.value ?? row.count ?? row.amount ?? row.expenditure ?? row.risk_score ?? row.similarity),
    }))
    .filter((row): row is { label: string; value: number } => row.value !== undefined)
    .slice(0, 14);

  const maximum = Math.max(0, ...values.map((row) => row.value));
  if (!values.length || !maximum) {
    return '<p class="report-empty">No visualization data available for current selection.</p>';
  }

  const padding = { top: 24, right: 20, bottom: 65, left: 52 };
  const areaWidth = width - padding.left - padding.right;
  const barWidth = Math.max(12, Math.min(38, (areaWidth / values.length) * 0.65));
  const step = areaWidth / values.length;

  const bars = values
    .map((row, index) => {
      const barHeight = ((height - padding.top - padding.bottom) * row.value) / maximum;
      const x = padding.left + step * index + (step - barWidth) / 2;
      const y = height - padding.bottom - barHeight;
      const shortened = row.label.length > 14 ? `${row.label.slice(0, 13)}…` : row.label;
      const displayVal =
        row.value >= 1000000 ? `${(row.value / 1000000).toFixed(1)}M` : row.value >= 1000 ? `${(row.value / 1000).toFixed(1)}k` : String(Number(row.value.toFixed(1)));
      return `<g><title>${escapeHtml(`${row.label}: ${row.value.toLocaleString("en-IN")}`)}</title><rect x="${x}" y="${y}" width="${barWidth}" height="${barHeight}" rx="2" fill="#1769aa"/><text x="${x + barWidth / 2}" y="${y - 4}" text-anchor="middle" font-size="9" font-weight="600" fill="#12355b">${displayVal}</text><text x="${x + barWidth / 2}" y="${height - padding.bottom + 14}" text-anchor="end" font-size="8.5" fill="#475569" transform="rotate(-35 ${x + barWidth / 2} ${height - padding.bottom + 14})">${escapeHtml(shortened)}</text></g>`;
    })
    .join("");

  return `<div class="report-chart-wrap"><svg viewBox="0 0 ${width} ${height}" role="img" aria-label="Bar chart"><line x1="${padding.left}" y1="${height - padding.bottom}" x2="${width - padding.right}" y2="${height - padding.bottom}" stroke="#cbd5e1" stroke-width="1.5"/><line x1="${padding.left}" y1="${padding.top}" x2="${padding.left}" y2="${height - padding.bottom}" stroke="#cbd5e1" stroke-width="1.5"/>${bars}</svg></div>`;
}

function groupedBarChartMarkup(rows: ReportRow[], series?: ReportSeries[], width = 680, height = 260): string {
  if (!series || !series.length) return barChartMarkup(rows, width, height);

  const padding = { top: 30, right: 20, bottom: 65, left: 55 };
  const areaWidth = width - padding.left - padding.right;
  const items = rows.slice(0, 10);
  if (!items.length) return '<p class="report-empty">No comparison data available.</p>';

  let maximum = 0;
  items.forEach((item) => {
    series.forEach((s) => {
      const val = numeric(item[s.key]) ?? 0;
      if (val > maximum) maximum = val;
    });
  });

  if (maximum <= 0) return '<p class="report-empty">No comparison metrics available.</p>';

  const groupStep = areaWidth / items.length;
  const barWidth = Math.max(8, Math.min(22, (groupStep * 0.7) / series.length));
  const defaultColors = ["#1769aa", "#2e7d32", "#ed6c02", "#9c27b0"];

  const legend = series
    .map(
      (s, idx) =>
        `<g transform="translate(${padding.left + idx * 130}, 10)"><rect width="10" height="10" rx="2" fill="${s.color ?? defaultColors[idx % defaultColors.length]}"/><text x="16" y="9" font-size="10" fill="#334155">${escapeHtml(s.label)}</text></g>`
    )
    .join("");

  const groups = items
    .map((item, gIdx) => {
      const groupX = padding.left + gIdx * groupStep;
      const groupLabel = String(item.label ?? item.name ?? item.house ?? item.category ?? `Group ${gIdx + 1}`);
      const shortened = groupLabel.length > 14 ? `${groupLabel.slice(0, 13)}…` : groupLabel;

      const groupBars = series
        .map((s, sIdx) => {
          const val = numeric(item[s.key]) ?? 0;
          const barH = ((height - padding.top - padding.bottom) * val) / maximum;
          const x = groupX + (groupStep - barWidth * series.length) / 2 + sIdx * barWidth;
          const y = height - padding.bottom - barH;
          const color = s.color ?? defaultColors[sIdx % defaultColors.length];
          return `<rect x="${x}" y="${y}" width="${barWidth - 1.5}" height="${barH}" rx="1.5" fill="${color}"><title>${escapeHtml(`${groupLabel} - ${s.label}: ${val.toLocaleString("en-IN")}`)}</title></rect>`;
        })
        .join("");

      return `<g>${groupBars}<text x="${groupX + groupStep / 2}" y="${height - padding.bottom + 14}" text-anchor="end" font-size="8.5" fill="#475569" transform="rotate(-35 ${groupX + groupStep / 2} ${height - padding.bottom + 14})">${escapeHtml(shortened)}</text></g>`;
    })
    .join("");

  return `<div class="report-chart-wrap"><svg viewBox="0 0 ${width} ${height}" role="img" aria-label="Grouped comparison chart"><line x1="${padding.left}" y1="${height - padding.bottom}" x2="${width - padding.right}" y2="${height - padding.bottom}" stroke="#cbd5e1" stroke-width="1.5"/><line x1="${padding.left}" y1="${padding.top}" x2="${padding.left}" y2="${height - padding.bottom}" stroke="#cbd5e1" stroke-width="1.5"/>${legend}${groups}</svg></div>`;
}

function renderChart(rows: ReportRow[], chartType?: string, chartSeries?: ReportSeries[]): string {
  if (chartType === "DONUT" || chartType === "DISTRIBUTION") {
    return donutChartMarkup(rows);
  }
  if (chartType === "LINE") {
    return lineChartMarkup(rows);
  }
  if (chartType === "GROUPED" || (chartSeries && chartSeries.length > 1)) {
    return groupedBarChartMarkup(rows, chartSeries);
  }
  return barChartMarkup(rows);
}

function kpiMarkup(kpis?: ReportKpi[]): string {
  if (!kpis || !kpis.length) return "";
  return `<div class="kpi-grid">${kpis
    .map(
      (k) =>
        `<div class="kpi-card"><p class="kpi-label">${escapeHtml(k.label)}</p><p class="kpi-value">${escapeHtml(typeof k.value === "number" ? k.value.toLocaleString("en-IN") : k.value)}</p>${k.description ? `<p class="kpi-desc">${escapeHtml(k.description)}</p>` : ""}</div>`
    )
    .join("")}</div>`;
}

function evidenceItemsMarkup(items?: ReportEvidenceItem[]): string {
  if (!items || !items.length) return "";
  return `<div class="evidence-grid">${items
    .map(
      (item) =>
        `<div class="evidence-item"><dt class="evidence-label">${escapeHtml(item.label)}</dt><dd class="evidence-value">${formatDisplayValue(item.value)}</dd></div>`
    )
    .join("")}</div>`;
}

function renderSection(sec: ReportSection): string {
  const kpisHtml = sec.kpis?.length ? `<div class="section-kpis">${kpiMarkup(sec.kpis)}</div>` : "";
  const evidenceHtml = sec.evidenceItems?.length ? evidenceItemsMarkup(sec.evidenceItems) : "";
  const narrativeHtml = sec.narrative
    ? `<div class="report-narrative"><p class="narrative-text">${escapeHtml(sec.narrative)}</p></div>`
    : "";

  let chartHtml = "";
  if (sec.chartRows && sec.chartRows.length > 0) {
    chartHtml = `<div class="report-chart"><div class="chart-header"><h4>Visual analysis</h4><p class="chart-caption">Rendered from verified database query results.</p></div>${renderChart(sec.chartRows, sec.chartType, sec.chartSeries)}</div>`;
  }

  // Supporting table: if `rows` provided, render them; otherwise if `chartRows` provided and no `rows`, render `chartRows` as supporting table!
  let tableHtml = "";
  const tableData = sec.rows && sec.rows.length ? sec.rows : sec.chartRows && sec.chartRows.length ? sec.chartRows : undefined;
  if (tableData && tableData.length > 0) {
    tableHtml = `<div class="section-table"><h4>Supporting data table</h4>${tableMarkup(tableData, sec.columns, sec.emptyMessage)}</div>`;
  } else if (sec.emptyMessage && !kpisHtml && !evidenceHtml && !narrativeHtml && !chartHtml) {
    tableHtml = `<p class="report-empty">${escapeHtml(sec.emptyMessage)}</p>`;
  }

  const customHtml = sec.customHtml ?? "";

  return `<section class="report-section">
    <div class="section-header">
      <h3>${escapeHtml(sec.title)}</h3>
      ${sec.subtitle ? `<p class="section-subtitle">${escapeHtml(sec.subtitle)}</p>` : ""}
    </div>
    ${kpisHtml}
    ${narrativeHtml}
    ${evidenceHtml}
    ${chartHtml}
    ${tableHtml}
    ${customHtml}
  </section>`;
}

function snapshotMarkup(selector?: string): string | undefined {
  if (!selector) return undefined;
  const source = document.querySelector(selector);
  if (!source) return undefined;
  const clone = source.cloneNode(true) as HTMLElement;
  // Remove interactive elements, buttons, nav, forms, inputs, and controls
  clone.querySelectorAll("button, form, nav, input, select, textarea, [data-report-exclude], .skip-link, [role='navigation'], [aria-label*='report actions']").forEach((element) => element.remove());
  clone.querySelectorAll("details").forEach((element) => element.setAttribute("open", ""));
  clone.querySelectorAll("table:not([data-report-table]), svg, .table-wrap, .report-chart").forEach((el) => el.remove());
  const trimmed = clone.innerHTML.trim();
  return trimmed.length > 20 ? `<section class="snapshot">${trimmed}</section>` : undefined;
}

function reportDocument({
  title,
  summary,
  subtitle,
  dataSource,
  rows = [],
  chartRows,
  filters = {},
  provenance,
  snapshot,
  narrative,
  kpis,
  chartType,
  sections,
}: {
  title: string;
  summary: string;
  subtitle?: string;
  dataSource?: string;
  rows?: ReportRow[];
  chartRows?: ReportRow[];
  filters: Filters | Record<string, unknown>;
  provenance?: ReportProvenance;
  snapshot?: string;
  narrative?: string;
  kpis?: ReportKpi[];
  chartType?: string;
  sections?: ReportSection[];
}): string {
  const filterRows =
    Object.entries(filters)
      .filter(([, value]) => value != null && value !== "")
      .map(([name, value]) => `<li><strong>${escapeHtml(name.replaceAll("_", " "))}:</strong> ${escapeHtml(value)}</li>`)
      .join("") || "<li>None (National / Unfiltered)</li>";

  const sourceTool = provenance?.tool_used ?? provenance?.service ?? "Verified MPLADS Active Dataset Analytics";

  let bodyContent = "";

  if (sections && sections.length > 0) {
    bodyContent = sections.map(renderSection).join("");
  } else {
    // Single section fallback for standard simple reports
    const topKpisHtml = kpiMarkup(kpis);
    const topNarrativeHtml = narrative
      ? `<section class="report-narrative"><h3>Verified finding</h3><p class="narrative-text">${escapeHtml(narrative)}</p></section>`
      : "";
    const activeChartRows = chartRows ?? rows;
    const chartHtml =
      activeChartRows && activeChartRows.length > 0
        ? `<section class="report-chart"><div class="chart-header"><h3>Visual analysis</h3><p class="chart-caption">Visualized directly from verified active-release records.</p></div>${renderChart(activeChartRows, chartType)}</section>`
        : "";
    const tableHtml = `<section class="report-section"><h3>Supporting data</h3>${tableMarkup(rows)}</section>`;
    const snapshotHtml = snapshot ? `<section class="report-section"><h3>Contextual evidence</h3>${snapshot}</section>` : "";

    bodyContent = `${topKpisHtml}${topNarrativeHtml}${chartHtml}${tableHtml}${snapshotHtml}`;
  }

  return `<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width,initial-scale=1"/>
  <title>${escapeHtml(title)}</title>
  <style>
    @page { size: A4 portrait; margin: 12mm 14mm; }
    * { box-sizing: border-box; }
    body { margin: 0; background: #ffffff; color: #0f172a; font: 11px/1.5 -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Arial, sans-serif; }
    header { border-bottom: 2.5px solid #1769aa; padding-bottom: 8px; margin-bottom: 12px; }
    .gov-banner { font-size: 8.5px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.08em; color: #64748b; margin-bottom: 2px; }
    .header-brand { font-size: 13px; font-weight: 800; color: #1769aa; letter-spacing: -0.02em; margin-bottom: 3px; }
    h1 { font-size: 18px; font-weight: 700; color: #0f172a; margin: 0 0 3px; line-height: 1.25; }
    .report-summary { font-size: 11.5px; color: #334155; margin: 0; line-height: 1.4; }
    .report-meta { display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 4px; padding: 7px 12px; margin: 10px 0 12px; font-size: 9.5px; color: #475569; }
    .report-meta p { margin: 0; }
    .report-meta strong { color: #0f172a; }
    .filter-section { background: #fafafa; border: 1px solid #e2e8f0; border-radius: 4px; padding: 6px 10px; margin-bottom: 12px; break-inside: avoid; }
    .filter-section h4 { font-size: 9.5px; text-transform: uppercase; font-weight: 700; color: #64748b; margin: 0 0 4px; }
    .filter-list { list-style: none; padding: 0; margin: 0; display: flex; flex-wrap: wrap; gap: 5px; font-size: 9.5px; }
    .filter-list li { background: #ffffff; border: 1px solid #cbd5e1; border-radius: 3px; padding: 2px 6px; }
    
    h3 { font-size: 13px; font-weight: 700; color: #0f172a; margin: 0 0 2px; break-after: avoid; }
    h4 { font-size: 11px; font-weight: 600; color: #1e293b; margin: 8px 0 4px; break-after: avoid; }
    .section-header { margin-bottom: 8px; border-bottom: 1px solid #e2e8f0; padding-bottom: 4px; }
    .section-subtitle { font-size: 10px; color: #64748b; margin: 1px 0 0; }
    p { margin: 4px 0; }

    .report-section { break-inside: avoid; margin: 14px 0; }
    .report-narrative { background: #f0fdf4; border-left: 3.5px solid #16a34a; padding: 8px 12px; margin: 8px 0; border-radius: 0 4px 4px 0; }
    .narrative-text { font-size: 11px; line-height: 1.55; color: #166534; font-weight: 500; margin: 0; white-space: pre-wrap; }

    .kpi-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(110px, 1fr)); gap: 6px; margin: 8px 0; }
    .kpi-card { background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 4px; padding: 7px 9px; break-inside: avoid; }
    .kpi-label { font-size: 8.5px; text-transform: uppercase; font-weight: 700; color: #64748b; margin: 0; }
    .kpi-value { font-size: 15px; font-weight: 700; color: #0f172a; margin: 2px 0 0; }
    .kpi-desc { font-size: 8px; color: #64748b; margin: 1px 0 0; }

    .evidence-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 6px; margin: 8px 0; }
    .evidence-item { background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 4px; padding: 6px 9px; }
    .evidence-label { font-size: 8.5px; text-transform: uppercase; font-weight: 600; color: #64748b; margin: 0; }
    .evidence-value { font-size: 11px; font-weight: 600; color: #0f172a; margin: 2px 0 0; word-break: break-word; }

    .report-chart { break-inside: avoid; margin: 10px 0; text-align: center; }
    .chart-header { text-align: left; margin-bottom: 4px; }
    .chart-caption { font-size: 9px; color: #64748b; margin: 0; }
    .report-chart-wrap { max-width: 100%; overflow: hidden; }
    .report-chart svg { max-width: 100%; max-height: 250px; height: auto; margin: 0 auto; display: block; }

    .table-wrap { overflow: visible; break-inside: auto; margin-top: 4px; }
    table { border-collapse: collapse; width: 100%; font-size: 9.5px; break-inside: auto; }
    thead { display: table-header-group; }
    tr { break-inside: avoid; }
    th, td { border: 1px solid #cbd5e1; padding: 4.5px 6.5px; text-align: left; vertical-align: top; word-break: break-word; }
    th { background: #f1f5f9; color: #1e293b; font-weight: 600; text-transform: capitalize; }
    tr:nth-child(even) { background: #f8fafc; }

    .snapshot { border: 1px solid #e2e8f0; border-radius: 4px; padding: 8px; margin: 8px 0; background: #fafafa; }
    .report-empty { padding: 8px 10px; background: #f8fafc; border: 1px solid #e2e8f0; font-size: 10.5px; color: #64748b; border-radius: 4px; margin: 6px 0; }

    .report-footer { margin-top: 20px; padding-top: 8px; border-top: 1px solid #e2e8f0; font-size: 8.5px; color: #64748b; break-inside: avoid; }
    .footer-top { display: flex; justify-content: space-between; }
    .footer-provenance { margin-top: 4px; font-family: monospace; font-size: 8px; color: #94a3b8; }

    @media print {
      body { font-size: 9.5px; }
      .snapshot { border-color: #cbd5e1; }
      .report-section { break-inside: avoid; }
      a { color: inherit; text-decoration: none; }
      button, form, nav, input, select, textarea { display: none !important; }
    }
  </style>
</head>
<body>
  <header>
    <div class="gov-banner">Government of India · Ministry of Statistics and Programme Implementation</div>
    <div class="header-brand">MPLADS AI</div>
    <h1>${escapeHtml(title)}</h1>
    <p class="report-summary">${escapeHtml(subtitle ? `${subtitle} — ${summary}` : summary)}</p>
  </header>
  <section class="report-meta">
    <p><strong>Generated:</strong> ${escapeHtml(new Date().toLocaleString("en-IN"))}</p>
    <p><strong>Data Source:</strong> ${escapeHtml(dataSource ?? "MPLADS active dataset")}</p>
    <p><strong>Scope / Tool:</strong> ${escapeHtml(sourceTool)}</p>
  </section>
  <section class="filter-section">
    <h4>Applied Filter Context</h4>
    <ul class="filter-list">${filterRows}</ul>
  </section>
  ${bodyContent}
  <footer class="report-footer">
    <div class="footer-top">
      <span>Verified analytics from MPLADS active dataset · Official Decision Support System</span>
      <span>Government of India · Ministry of Statistics and Programme Implementation</span>
    </div>
    ${provenance?.tool_used ? `<div class="footer-provenance">Analytical Processing Engine: ${escapeHtml(provenance.tool_used)}</div>` : ""}
  </footer>
</body>
</html>`;
}

export function ReportActions({
  title,
  summary,
  subtitle,
  dataSource,
  rows = [],
  filters = {},
  provenance,
  disabled = false,
  reportSelector,
  narrative,
  kpis,
  chartType,
  chartRows,
  sections,
  hideCsv = false,
}: ReportProps) {
  const [status, setStatus] = useState<string>();

  const hasContent =
    (sections && sections.length > 0) ||
    rows.length > 0 ||
    Boolean(reportSelector && document.querySelector(reportSelector)) ||
    Boolean(narrative) ||
    Boolean(kpis && kpis.length > 0);

  const canReport = !disabled && hasContent;

  const exportCsv = () => {
    let lines: string[] = [];

    if (sections && sections.length > 0) {
      sections.forEach((sec, idx) => {
        const secRows = sec.rows && sec.rows.length ? sec.rows : sec.chartRows && sec.chartRows.length ? sec.chartRows : [];
        if (secRows.length > 0) {
          if (idx > 0) lines.push("");
          lines.push(`"# Section: ${sec.title.replaceAll('"', '""')}"`);
          const cols = sec.columns && sec.columns.length ? sec.columns : [...new Set(secRows.flatMap((r) => Object.keys(r)))];
          lines.push(cols.map(csvCell).join(","));
          secRows.forEach((r) => {
            lines.push(cols.map((col) => csvCell(r[col])).join(","));
          });
        } else if (sec.evidenceItems && sec.evidenceItems.length > 0) {
          if (idx > 0) lines.push("");
          lines.push(`"# Section: ${sec.title.replaceAll('"', '""')}"`);
          lines.push('"Indicator","Value"');
          sec.evidenceItems.forEach((item) => {
            lines.push(`${csvCell(item.label)},${csvCell(item.value)}`);
          });
        } else if (sec.kpis && sec.kpis.length > 0) {
          if (idx > 0) lines.push("");
          lines.push(`"# Section: ${sec.title.replaceAll('"', '""')}"`);
          lines.push('"KPI","Value"');
          sec.kpis.forEach((k) => {
            lines.push(`${csvCell(k.label)},${csvCell(k.value)}`);
          });
        }
      });
    } else if (rows.length > 0) {
      const columns = [...new Set(rows.flatMap((row) => Object.keys(row)))];
      lines = [columns.map(csvCell).join(","), ...rows.map((row) => columns.map((column) => csvCell(row[column])).join(","))];
    } else if (kpis && kpis.length > 0) {
      lines = ['"KPI","Value"', ...kpis.map((k) => `${csvCell(k.label)},${csvCell(k.value)}`)];
    }

    if (!lines.length) {
      setStatus("No reportable results are available for the selected filters.");
      return;
    }

    const blob = new Blob([lines.join("\r\n")], { type: "text/csv;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `${safeFileStem(title)}-${reportDate()}.csv`;
    link.click();
    URL.revokeObjectURL(url);
    setStatus("CSV download prepared from the current result.");
  };

  const openReport = (print: boolean) => {
    const snapshot = snapshotMarkup(reportSelector);
    if (!hasContent && !snapshot) {
      setStatus("No reportable results are available for the selected filters.");
      return;
    }
    setStatus(print ? "Preparing print-safe report…" : "Generating report…");
    const report = window.open("", "_blank");
    if (!report) {
      setStatus("Unable to open the report window. Please allow pop-ups and try again.");
      return;
    }
    report.opener = null;
    report.document.open();
    report.document.write(
      reportDocument({
        title,
        summary,
        subtitle,
        dataSource,
        rows,
        filters,
        provenance,
        snapshot,
        narrative,
        kpis,
        chartType,
        chartRows,
        sections,
      })
    );
    report.document.close();
    if (print) {
      window.setTimeout(() => {
        report.focus();
        report.print();
      }, 150);
    }
    setStatus(print ? "Print-safe report ready. Use the browser dialog to Save as PDF." : "Report ready in a new tab.");
  };

  return (
    <div className="space-y-2">
      <div className="flex flex-wrap gap-2" aria-label="Current result report actions">
        <button className="button-secondary" type="button" disabled={!canReport} onClick={() => openReport(false)}>
          <FileText className="size-4" />Generate Report
        </button>
        {!hideCsv && (
          <button className="button-secondary" type="button" disabled={disabled || !canReport} onClick={exportCsv}>
            <Download className="size-4" />Download CSV
          </button>
        )}
        <button className="button-secondary" type="button" disabled={!canReport} onClick={() => openReport(true)}>
          <Printer className="size-4" />Print / Save PDF
        </button>
      </div>
      {status ? <p className="text-xs text-slate-600" role="status" aria-live="polite">{status}</p> : null}
    </div>
  );
}
