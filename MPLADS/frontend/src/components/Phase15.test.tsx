import { useState } from "react";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { FilterBar } from "./FilterBar";
import { ReportActions } from "./ReportActions";
import { SmartVisualization } from "./SmartVisualization";
import { ViewToggle, type CollectionView } from "./ViewToggle";
import type { Filters, VisualizationSpec } from "../api/types";

const provenance = { service: "test", release_version: "release-test", batch_id: "batch-test", filters: {}, generated_at: "2026-01-01T00:00:00Z" };

function FilterHarness() {
  const [filters, setFilters] = useState<Filters>({ house: "LOK_SABHA", state: "Test State", district_or_ida: "Test District", mp: "Test MP" });
  return <><FilterBar filters={filters} onChange={setFilters} onReset={() => setFilters({})} /><output data-testid="filters">{JSON.stringify(filters)}</output></>;
}

function ViewHarness() {
  const [view, setView] = useState<CollectionView>("list");
  return <ViewToggle value={view} onChange={setView} label="Test collection view" />;
}

afterEach(() => { cleanup(); vi.unstubAllGlobals(); vi.useRealTimers(); });

describe("Phase 15 public data exploration components", () => {
  it("loads backend option controls and clears dependent filters when House changes", async () => {
    const fetchMock = vi.fn((input: RequestInfo | URL) => {
      const url = new URL(String(input));
      const field = url.searchParams.get("field") ?? "state";
      return Promise.resolve(new Response(JSON.stringify({ data: { field, options: [{ value: "Test State", label: "Test State", count: 3 }], limited: false }, provenance }), { status: 200, headers: { "Content-Type": "application/json" } }));
    });
    vi.stubGlobal("fetch", fetchMock);
    render(<FilterHarness />);
    await waitFor(() => expect(fetchMock).toHaveBeenCalled());
    expect(screen.getByLabelText("State")).toHaveValue("Test State");
    fireEvent.change(screen.getByLabelText("House"), { target: { value: "RAJYA_SABHA" } });
    expect(screen.getByLabelText("State")).toHaveValue("");
    expect(screen.getByLabelText("District / IDA")).toHaveValue("");
    expect(screen.getByLabelText("MP")).toHaveValue("");
    expect(screen.getByTestId("filters")).toHaveTextContent("RAJYA_SABHA");
    expect(screen.getByTestId("filters")).not.toHaveTextContent("Test District");
    expect(String(fetchMock.mock.calls.at(-1)?.[0])).toContain("filters/options");
  });

  it("renders a deterministic visual with an accessible supporting table", () => {
    const spec: VisualizationSpec = { title: "Recorded expenditure by state", description: "Active release aggregation.", chart_type: "HORIZONTAL_BAR", x_axis: "Expenditure", y_axis: "State", unit: "Expenditure", series: [{ key: "value", label: "Expenditure" }], rows: [{ label: "Test State", value: 1250 }], record_count: 1, data_available: true, selection: { rule: "ranked_categories", rationale: "Observed categories are ranked.", source: "active_release_aggregate" } };
    render(<SmartVisualization spec={spec} />);
    expect(screen.getByRole("figure")).toHaveAccessibleName("Recorded expenditure by state");
    expect(screen.getByText("1 displayed record · Unit: Expenditure")).toBeInTheDocument();
    expect(screen.getByText("Chart selection: Observed categories are ranked.")).toBeInTheDocument();
    expect(screen.getByText("Inspect supporting table")).toBeInTheDocument();
    expect(screen.getByRole("table")).toBeInTheDocument();
  });

  it("renders every supported chart type with an accessible table", () => {
    const shared = { description: "Verified active-release aggregate.", x_axis: "Category", y_axis: "Value", unit: "Works", record_count: 2, data_available: true, selection: { rule: "test_rule", rationale: "A deterministic test rule.", source: "active_release_aggregate" as const } };
    const charts: Array<[VisualizationSpec, RegExp | null]> = [
      [{ ...shared, title: "Pie", chart_type: "PIE", series: [{ key: "value", label: "Works" }], rows: [{ label: "A", value: 2 }, { label: "B", value: 1 }] }, /Pie pie chart/],
      [{ ...shared, title: "Donut", chart_type: "DONUT", series: [{ key: "value", label: "Works" }], rows: [{ label: "A", value: 2 }, { label: "B", value: 1 }] }, /Donut donut chart/],
      [{ ...shared, title: "Grouped", chart_type: "GROUPED_BAR", series: [{ key: "sanctioned", label: "Sanctioned" }, { key: "completed", label: "Completed" }], rows: [{ label: "A", sanctioned: 2, completed: 1 }, { label: "B", sanctioned: 3, completed: 2 }] }, /Grouped grouped bar chart/],
      [{ ...shared, title: "Stacked", chart_type: "STACKED_BAR", series: [{ key: "open", label: "Open" }, { key: "closed", label: "Closed" }], rows: [{ label: "A", open: 2, closed: 1 }, { label: "B", open: 3, closed: 2 }] }, /Stacked stacked bar chart/],
      [{ ...shared, title: "Histogram", chart_type: "HISTOGRAM", series: [{ key: "value", label: "Works" }], rows: [{ label: "0–10 days", value: 2 }, { label: "10–20 days", value: 1 }] }, /Histogram histogram/],
      [{ ...shared, title: "Area", chart_type: "AREA", series: [{ key: "value", label: "Works" }], rows: [{ label: "2024-01", value: 2 }, { label: "2024-02", value: 3 }] }, /Area area chart/],
      [{ ...shared, title: "Scatter", chart_type: "SCATTER", series: [{ key: "y", label: "Expenditure" }], rows: [{ label: "A", x: 2, y: 20 }, { label: "B", x: 3, y: 30 }] }, /Scatter scatter plot/],
      [{ ...shared, title: "Heatmap", chart_type: "HEATMAP", series: [{ key: "roads", label: "Roads" }, { key: "water", label: "Water" }], rows: [{ label: "A", roads: 2, water: 1 }, { label: "B", roads: 3, water: 2 }] }, /Heatmap heatmap/],
      [{ ...shared, title: "Line", chart_type: "LINE", series: [{ key: "value", label: "Works" }], rows: [{ label: "2024-01", value: 2 }, { label: "2024-02", value: 3 }] }, /Line line chart/],
      [{ ...shared, title: "Bar", chart_type: "BAR", series: [{ key: "value", label: "Works" }], rows: [{ label: "A", value: 2 }, { label: "B", value: 3 }] }, /Bar bar chart/],
      [{ ...shared, title: "Horizontal", chart_type: "HORIZONTAL_BAR", series: [{ key: "value", label: "Works" }], rows: [{ label: "A", value: 2 }, { label: "B", value: 3 }] }, /Horizontal ranked bar chart/],
      [{ ...shared, title: "Table", chart_type: "TABLE", series: [], rows: [{ label: "A", value: 2 }, { label: "B", value: 3 }] }, /Table table visualization/],
      [{ ...shared, title: "KPI", chart_type: "KPI", series: [], rows: [{ label: "Verified value", value: 2 }], record_count: 1 }, null],
    ];
    for (const [spec, visualName] of charts) {
      render(<SmartVisualization spec={spec} />);
      expect(screen.getByRole("figure")).toHaveAccessibleName(spec.title);
      expect(screen.getByRole("table")).toBeInTheDocument();
      if (visualName) expect(screen.getByRole("img", { name: visualName })).toBeInTheDocument();
      cleanup();
    }
  });

  it("exports only the supplied current result as CSV", () => {
    const createObjectURL = vi.fn(() => "blob:test");
    vi.stubGlobal("URL", { createObjectURL, revokeObjectURL: vi.fn() });
    const click = vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => undefined);
    render(<ReportActions title="Current result" summary="Verified result" rows={[{ label: "Count", value: 3 }]} filters={{ state: "Test State" }} provenance={provenance} />);
    fireEvent.click(screen.getByRole("button", { name: "Download CSV" }));
    expect(createObjectURL).toHaveBeenCalledOnce();
    expect(click).toHaveBeenCalledOnce();
    click.mockRestore();
  });

  it("keeps the selected collection view accessible and controlled", () => {
    render(<ViewHarness />);
    expect(screen.getByRole("button", { name: "List" })).toHaveAttribute("aria-pressed", "true");
    fireEvent.click(screen.getByRole("button", { name: "Grid" }));
    expect(screen.getByRole("button", { name: "Grid" })).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByRole("group", { name: "Test collection view" })).toBeInTheDocument();
  });

  it("generates a self-contained report from only the current result", () => {
    const write = vi.fn();
    const reportWindow = { opener: null, document: { open: vi.fn(), write, close: vi.fn() }, focus: vi.fn(), print: vi.fn() };
    vi.spyOn(window, "open").mockReturnValue(reportWindow as unknown as Window);
    render(<ReportActions title="Verified report" summary="A current analytical result." rows={[{ label: "Verified count", value: 3 }]} filters={{ state: "Test State" }} provenance={provenance} />);
    fireEvent.click(screen.getByRole("button", { name: "Generate Report" }));
    expect(write).toHaveBeenCalledOnce();
    const documentMarkup = String(write.mock.calls[0][0]);
    expect(documentMarkup).toContain("Verified report");
    expect(documentMarkup).toContain("Supporting data");
    expect(documentMarkup).toContain("Verified count");
    expect(documentMarkup).toContain("Test State");
    expect(screen.getByRole("status")).toHaveTextContent("Report ready in a new tab.");
  });

  it("uses the same complete report document for Print / Save PDF", () => {
    vi.useFakeTimers();
    const write = vi.fn();
    const print = vi.fn();
    const reportWindow = { opener: null, document: { open: vi.fn(), write, close: vi.fn() }, focus: vi.fn(), print };
    vi.spyOn(window, "open").mockReturnValue(reportWindow as unknown as Window);
    render(<ReportActions title="Printable verified report" summary="Current report context." rows={[{ label: "Verified count", value: 3 }]} provenance={provenance} />);
    fireEvent.click(screen.getByRole("button", { name: "Print / Save PDF" }));
    expect(String(write.mock.calls[0][0])).toContain("Supporting data");
    vi.runAllTimers();
    expect(print).toHaveBeenCalledOnce();
    expect(screen.getByRole("status")).toHaveTextContent("Print-safe report ready");
  });
});
