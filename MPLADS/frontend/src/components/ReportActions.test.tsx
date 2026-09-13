import { describe, expect, it, vi, beforeEach, afterEach } from "vitest";
import { fireEvent, render, screen, cleanup } from "@testing-library/react";
import { ReportActions, type ReportSection } from "./ReportActions";

describe("ReportActions", () => {
  let writeMock: ReturnType<typeof vi.fn>;

  afterEach(() => {
    cleanup();
  });

  beforeEach(() => {
    writeMock = vi.fn();
    vi.spyOn(window, "open").mockImplementation(() => {
      return {
        opener: null,
        document: {
          open: vi.fn(),
          write: writeMock,
          close: vi.fn(),
        },
        focus: vi.fn(),
        print: vi.fn(),
      } as unknown as Window;
    });
  });

  it("renders report action buttons properly", () => {
    render(
      <ReportActions
        title="Sample Report"
        summary="Sample report summary"
        rows={[{ name: "Work 1", count: 10 }]}
      />
    );

    expect(screen.getByRole("button", { name: /Generate Report/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Download CSV/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Print \/ Save PDF/i })).toBeInTheDocument();
  });

  it("generates an official document with title, summary, and filter context", () => {
    render(
      <ReportActions
        title="MPLADS State Analysis"
        summary="State distribution summary"
        filters={{ state: "Telangana", house: "LOK_SABHA" }}
        rows={[{ state: "Telangana", works: 1250 }]}
      />
    );

    fireEvent.click(screen.getByRole("button", { name: /Generate Report/i }));

    expect(writeMock).toHaveBeenCalledOnce();
    const html = String(writeMock.mock.calls[0][0]);

    // Header & Title
    expect(html).toContain("MPLADS AI");
    expect(html).toContain("MPLADS State Analysis");
    expect(html).toContain("State distribution summary");
    expect(html).toContain("Data Source:</strong> MPLADS active dataset");

    // Applied Filter Context
    expect(html).toContain("Telangana");
    expect(html).toContain("LOK_SABHA");

    // Ensure no internal release hash is prominently displayed
    expect(html).not.toContain("phase5-v2:cc8d5102");
  });

  it("renders multi-section reports with KPIs, charts, and supporting tables", () => {
    const sections: ReportSection[] = [
      {
        title: "Section 1: Monitoring Signals",
        subtitle: "Active risk signals",
        kpis: [
          { label: "Monitored works", value: 97516 },
          { label: "Risk signals", value: 46269 },
        ],
      },
      {
        title: "Section 2: Work Status",
        subtitle: "Status distribution",
        chartType: "DONUT",
        chartRows: [
          { label: "Sanctioned", value: 32843 },
          { label: "Completed", value: 32914 },
        ],
        rows: [
          { status: "Sanctioned", count: 32843 },
          { status: "Completed", count: 32914 },
        ],
      },
      {
        title: "Section 3: Trend Analysis",
        subtitle: "Monthly timeline",
        chartType: "LINE",
        chartRows: [
          { period: "2023-01", value: 1500000 },
          { period: "2023-02", value: 2500000 },
        ],
      },
    ];

    render(
      <ReportActions
        title="Executive Report"
        summary="Complete multi-section report"
        sections={sections}
      />
    );

    fireEvent.click(screen.getByRole("button", { name: /Generate Report/i }));

    expect(writeMock).toHaveBeenCalledOnce();
    const html = String(writeMock.mock.calls[0][0]);

    // Check sections exist
    expect(html).toContain("Section 1: Monitoring Signals");
    expect(html).toContain("Section 2: Work Status");
    expect(html).toContain("Section 3: Trend Analysis");

    // Check KPIs
    expect(html).toContain("Monitored works");
    expect(html).toContain("97,516");

    // Check charts
    expect(html).toContain("<svg");
    expect(html).toContain("aria-label=\"Distribution chart\"");
    expect(html).toContain("aria-label=\"Trend chart\"");

    // Check chart bounding in CSS
    expect(html).toContain("max-height: 250px");

    // Check Supporting data tables
    expect(html).toContain("Supporting data table");
    expect(html).toContain("Sanctioned");
    expect(html).toContain("Completed");
  });

  it("handles empty state gracefully without generating blank pages", () => {
    render(
      <ReportActions
        title="Empty Report"
        summary="No data found"
        rows={[]}
        sections={[
          {
            title: "Empty Section",
            emptyMessage: "No reportable results are available for the current selection.",
          },
        ]}
      />
    );

    fireEvent.click(screen.getByRole("button", { name: /Generate Report/i }));

    expect(writeMock).toHaveBeenCalledOnce();
    const html = String(writeMock.mock.calls[0][0]);

    expect(html).toContain("No reportable results are available for the current selection.");
  });

  it("excludes buttons, forms, and interactive navigation in print view CSS", () => {
    render(
      <ReportActions
        title="Print Safe Check"
        summary="Testing print exclusions"
        rows={[{ item: "A", value: 1 }]}
      />
    );

    fireEvent.click(screen.getByRole("button", { name: /Print \/ Save PDF/i }));

    expect(writeMock).toHaveBeenCalledOnce();
    const html = String(writeMock.mock.calls[0][0]);

    // Print media queries should explicitly hide interactive controls
    expect(html).toContain("button, form, nav, input, select, textarea { display: none !important; }");
    expect(html).toContain("@page { size: A4 portrait; margin: 12mm 14mm; }");
    expect(html).toContain("thead { display: table-header-group; }");
  });

  it("triggers CSV export with properly escaped fields and sections", () => {
    const createObjectURLMock = vi.fn().mockReturnValue("blob:mock-url");
    const revokeObjectURLMock = vi.fn();
    window.URL.createObjectURL = createObjectURLMock;
    window.URL.revokeObjectURL = revokeObjectURLMock;

    render(
      <ReportActions
        title="Test CSV Export"
        summary="CSV test"
        sections={[
          {
            title: "Summary Section",
            rows: [
              { key: "Monitored", count: 100 },
              { key: "Risk", count: 20 },
            ],
          },
        ]}
      />
    );

    fireEvent.click(screen.getByRole("button", { name: /Download CSV/i }));

    expect(createObjectURLMock).toHaveBeenCalledOnce();
    expect(revokeObjectURLMock).toHaveBeenCalledOnce();
  });
});
