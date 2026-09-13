import { describe, expect, it, vi } from "vitest";
import { api, ApiError, setMonitoringCredentials } from "./client";

describe("API client", () => {
  it("passes non-empty filters as query parameters", async () => {
    const fetchMock = vi.fn().mockImplementation(() => Promise.resolve(new Response(JSON.stringify({ data: {}, provenance: {} }), { status: 200 })));
    vi.stubGlobal("fetch", fetchMock);
    await api.dashboardSummary({ house: "LOK_SABHA", state: "Generic State" });
    expect(String(fetchMock.mock.calls[0][0])).toContain("house=LOK_SABHA");
    expect(String(fetchMock.mock.calls[0][0])).toContain("state=Generic+State");
    vi.unstubAllGlobals();
  });

  it("surfaces API failure instead of returning a fallback", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(JSON.stringify({ detail: { code: "DATABASE_UNAVAILABLE", message: "Database is unavailable." } }), { status: 503 })));
    await expect(api.dashboardSummary()).rejects.toBeInstanceOf(ApiError);
    vi.unstubAllGlobals();
  });

  it("requests bounded filter options and server-selected visualizations", async () => {
    const fetchMock = vi.fn().mockImplementation(() => Promise.resolve(new Response(JSON.stringify({ data: {}, provenance: {} }), { status: 200 })));
    vi.stubGlobal("fetch", fetchMock);
    await api.filterOptions("district_or_ida", { house: "LOK_SABHA", state: "Test State" }, "test");
    await api.exploreVisualization("expenditure", "state", { state: "Test State" });
    expect(String(fetchMock.mock.calls[0][0])).toContain("filters/options");
    expect(String(fetchMock.mock.calls[0][0])).toContain("field=district_or_ida");
    expect(String(fetchMock.mock.calls[0][0])).toContain("state=Test+State");
    expect(String(fetchMock.mock.calls[1][0])).toContain("visualizations/explore");
    expect(String(fetchMock.mock.calls[1][0])).toContain("metric=expenditure");
    expect(String(fetchMock.mock.calls[1][0])).toContain("group_by=state");
    vi.unstubAllGlobals();
  });

  it("attaches authorized-monitoring headers to protected collection roots", async () => {
    const fetchMock = vi.fn().mockImplementation(() => Promise.resolve(new Response(JSON.stringify({ items: [], pagination: {}, provenance: {} }), { status: 200 })));
    vi.stubGlobal("fetch", fetchMock);
    setMonitoringCredentials({ role: "PLATFORM_ADMINISTRATOR", actor: "client-test" });

    await api.alerts();
    await api.recommendations();

    for (const [, init] of fetchMock.mock.calls) {
      expect(init.headers).toMatchObject({ "X-MPLADS-Role": "PLATFORM_ADMINISTRATOR", "X-MPLADS-Actor": "client-test" });
    }
  });
});
