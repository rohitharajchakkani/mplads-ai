import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import WorkDetailPage from "./WorkDetailPage";
import { api } from "../api/client";

vi.mock("../api/client", () => ({
  api: {
    work: vi.fn(),
    riskWork: vi.fn(),
    reviewCases: vi.fn(),
  },
  endpoint: vi.fn(),
}));

const mockWorkData = {
  data: {
    work: {
      canonical_work_key: "LOK_SABHA_TEST_101",
      work_id: "WORK-101",
      house: "LOK_SABHA",
      financial_year: "2023-2024",
      mp: "Hon. Member Name",
      state: "Maharashtra",
      district_or_ida: "Pune",
      constituency: "Pune",
      work_description: "Construction of rural community center at village square",
      source_work_category: "Community Infrastructure",
      sector: null,
      subsector: null,
    },
    sanctions: [
      {
        sanction_date: "2023-06-15",
        amount: "500000",
      },
    ],
    completions: [
      {
        completion_date: "2024-01-20",
      },
    ],
    recommendations: [
      {
        date: "2023-04-10",
      },
    ],
    expenditure: {
      total: "480000",
      transaction_count: 2,
      first_expenditure_date: "2023-08-01",
      latest_expenditure_date: "2023-12-15",
      transactions: [
        {
          date: "2023-08-01",
          vendor_name: "Apex Builders",
          payment_status: "PAID",
          amount: "250000",
        },
        {
          date: "2023-12-15",
          vendor_name: "Apex Builders",
          payment_status: "PAID",
          amount: "230000",
        },
      ],
    },
    provenance: {
      release_version: "phase5-v2:cc8d5102",
      batch_id: "batch-789",
    },
  },
  provenance: {
    release_version: "phase5-v2:cc8d5102",
    batch_id: "batch-789",
  },
};

describe("WorkDetailPage Report Actions", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(api.work).mockResolvedValue(mockWorkData as any);
    vi.mocked(api.riskWork).mockRejectedValue(new Error("Unauthorized"));
    vi.mocked(api.reviewCases).mockRejectedValue(new Error("Unauthorized"));
  });

  it("renders Generate Report and Print / Save PDF actions near the top header", async () => {
    render(
      <MemoryRouter initialEntries={["/works/LOK_SABHA_TEST_101"]}>
        <Routes>
          <Route path="/works/*" element={<WorkDetailPage />} />
        </Routes>
      </MemoryRouter>
    );

    const workElements = await screen.findAllByText("WORK-101");
    expect(workElements.length).toBeGreaterThan(0);
    
    // Check report actions are visible
    const generateBtn = screen.getAllByRole("button", { name: /Generate Report/i })[0];
    const printBtn = screen.getAllByRole("button", { name: /Print \/ Save PDF/i })[0];
    expect(generateBtn).toBeInTheDocument();
    expect(printBtn).toBeInTheDocument();

    // Verify CSV button is hidden when hideCsv is specified
    expect(screen.queryByRole("button", { name: /Download CSV/i })).toBeNull();
  });

  it("generates a comprehensive work detail report with actual work information", async () => {
    const write = vi.fn();
    const close = vi.fn();
    const open = vi.fn();
    vi.spyOn(window, "open").mockReturnValue({
      document: { open, write, close },
      opener: null,
    } as unknown as Window);

    render(
      <MemoryRouter initialEntries={["/works/LOK_SABHA_TEST_101"]}>
        <Routes>
          <Route path="/works/*" element={<WorkDetailPage />} />
        </Routes>
      </MemoryRouter>
    );

    const workElements = await screen.findAllByText("WORK-101");
    expect(workElements.length).toBeGreaterThan(0);

    const generateBtn = screen.getAllByRole("button", { name: /Generate Report/i })[0];
    fireEvent.click(generateBtn);

    expect(write).toHaveBeenCalledOnce();
    const reportHtml = String(write.mock.calls[0][0]);

    // Verify required report sections and fields
    expect(reportHtml).toContain("MPLADS Work Detail Report");
    expect(reportHtml).toContain("WORK-101");
    expect(reportHtml).toContain("Lok Sabha");
    expect(reportHtml).toContain("Maharashtra");
    expect(reportHtml).toContain("Pune");
    expect(reportHtml).toContain("Completed");
    expect(reportHtml).toContain("2023-2024");
    expect(reportHtml).toContain("Data Source:</strong> MPLADS active dataset");
    
    // Verify no prominent internal release hashes in header/meta
    expect(reportHtml).not.toContain("phase5-v2:cc8d5102");
  });
});
