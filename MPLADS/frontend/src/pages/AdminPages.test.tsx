import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { setMonitoringCredentials } from "../api/client";
import { AccessRequestsPage, SystemHealthPage } from "./AdminPages";

const response = (body: unknown, status = 200) => new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });
const page = (items: unknown[]) => ({ items, pagination: { total: items.length, page: 1, page_size: 25, total_pages: items.length ? 1 : 0 } });

afterEach(() => { cleanup(); vi.unstubAllGlobals(); setMonitoringCredentials(undefined); });

describe("administration frontend", () => {
  it("renders only backend-supplied access requests and sends an explicit approval", async () => {
    setMonitoringCredentials({ role: "PLATFORM_ADMINISTRATOR", actor: "admin-test" });
    const request = { request_id: "request-1", name: "Test applicant", designation: "Officer", office: "Test office", state_name: "Test State", district_or_ida: "Test District", reason: "Test request", status: "PENDING", created_at: "2026-01-01T00:00:00Z", decided_at: null, decided_by: null, decision_note: null, approved_user_id: null };
    const fetchMock = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      void init;
      if (String(input).includes("/approve")) return Promise.resolve(response({ user_id: "user-1", display_name: "Test applicant", designation: "Officer", office: "Test office", role: "STATE_NODAL_AUTHORITY", state_scope: "Test State", district_scope: null, mp_scope: null, status: "ACTIVE", source_access_request_id: "request-1", version: 1, created_at: request.created_at, updated_at: request.created_at, changed_by: "admin-test", disabled_at: null }));
      return Promise.resolve(response(page([request])));
    });
    vi.stubGlobal("fetch", fetchMock);
    render(<MemoryRouter><AccessRequestsPage /></MemoryRouter>);
    expect(await screen.findByText("Test applicant")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Review" }));
    fireEvent.click(screen.getByRole("checkbox"));
    fireEvent.click(screen.getByRole("button", { name: "Approve request" }));
    await waitFor(() => expect(fetchMock.mock.calls.some(([url]) => String(url).includes("/admin/access-requests/request-1/approve"))).toBe(true));
    const call = fetchMock.mock.calls.find(([url]) => String(url).includes("/approve"));
    expect(call?.[1]?.headers).toMatchObject({ "X-MPLADS-Role": "PLATFORM_ADMINISTRATOR", "X-MPLADS-Actor": "admin-test" });
    expect(String(call?.[1]?.body)).toContain("STATE_NODAL_AUTHORITY");
  });

  it("renders safe live system and configuration status without values", async () => {
    setMonitoringCredentials({ role: "PLATFORM_ADMINISTRATOR", actor: "admin-test" });
    vi.stubGlobal("fetch", vi.fn((input: RequestInfo | URL) => {
      const url = String(input);
      if (url.includes("admin/configuration")) return Promise.resolve(response({ database: "CONFIGURED", gemini: "CONFIGURED", cors: "CONFIGURED", active_dataset: "AVAILABLE", environment: "development", migration: "CURRENT", checked_at: "2026-01-01T00:00:00Z" }));
      return Promise.resolve(response({ api_status: "OK", database_status: "OK", active_dataset_status: "AVAILABLE", active_release_version: "test-release", migration_version: "20260911_08", application_version: "0.1.0", app_environment: "development", cors_status: "CONFIGURED", gemini_status: "CONFIGURED", gemini_model: "gemini-test", latest_analytics_run: null, checked_at: "2026-01-01T00:00:00Z" }));
    }));
    render(<MemoryRouter><SystemHealthPage /></MemoryRouter>);
    expect(await screen.findByText("System health")).toBeInTheDocument();
    expect(screen.getByText("Safe production configuration")).toBeInTheDocument();
    expect(screen.queryByText(/AIza/)).not.toBeInTheDocument();
    expect(screen.queryByText(/sqlite:\/\//i)).not.toBeInTheDocument();
  });
});
