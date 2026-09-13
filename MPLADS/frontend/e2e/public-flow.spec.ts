import { expect, test } from "@playwright/test";

test("public exploration flows through the live FastAPI dataset", async ({ page, request }) => {
  const works = await request.get("http://127.0.0.1:8000/api/v1/works?page_size=1");
  expect(works.ok()).toBeTruthy();
  const workPayload = await works.json() as { items: Array<{ canonical_work_key: string; work_id: string | null }> };
  const work = workPayload.items[0];
  expect(work).toBeDefined();

  const states = await request.get("http://127.0.0.1:8000/api/v1/states?page_size=1");
  expect(states.ok()).toBeTruthy();
  const statePayload = await states.json() as { items: Array<{ name: string }> };
  const datasets = await request.get("http://127.0.0.1:8000/api/v1/datasets/active");
  expect(datasets.ok()).toBeTruthy();
  const datasetPayload = await datasets.json() as { data: { datasets: Array<{ house: string }> } };
  const house = datasetPayload.data.datasets[0].house;

  await page.goto("/");
  await expect(page.getByRole("heading", { name: "Evidence-led MPLADS anomaly and risk monitoring.", exact: true })).toBeVisible();
  await page.getByRole("link", { name: "View implementation context" }).click();
  await expect(page).toHaveURL(/\/dashboard/);
  await page.getByLabel("House", { exact: true }).fill(house);
  await expect(page).toHaveURL(new RegExp(`house=${house}`));
  await page.getByLabel("State", { exact: true }).fill(statePayload.items[0].name);
  await expect(page).toHaveURL(/state=/);
  await page.getByLabel("State", { exact: true }).fill("");

  await page.getByRole("button", { name: "Generate visualization" }).click();
  const expenditureByState = page.getByRole("figure", { name: "Expenditure by State" });
  await expect(expenditureByState).toBeVisible({ timeout: 90_000 });
  await expect(expenditureByState.getByText("Inspect supporting table")).toBeVisible();
  const download = page.waitForEvent("download");
  await page.getByRole("button", { name: "Download CSV" }).last().click();
  expect((await download).suggestedFilename()).toMatch(/\.csv$/);

  await page.getByLabel("Metric").selectOption("progress");
  await page.getByRole("button", { name: "Generate visualization" }).click();
  const progressByState = page.getByRole("figure", { name: "Sanctioned and completed works by State" });
  await expect(progressByState).toBeVisible({ timeout: 90_000 });
  await expect(progressByState.getByRole("img", { name: "Sanctioned and completed works by State grouped bar chart" })).toBeVisible();
  await expect(progressByState.getByText(/Chart selection: Two observed work-linkage counts/)).toBeVisible();

});

test("public explorers retain server-backed views, filtering, and grouped search", async ({ page, request }) => {
  const states = await request.get("http://127.0.0.1:8000/api/v1/states?page_size=1");
  expect(states.ok()).toBeTruthy();
  const statePayload = await states.json() as { items: Array<{ name: string }> };
  const state = statePayload.items[0]?.name;
  expect(state).toBeTruthy();

  for (const [path, heading] of [["/mps", "MP explorer"], ["/states", "State explorer"], ["/districts", "District / IDA explorer"], ["/statistics", "Statistics"]] as const) {
    await page.goto(path);
    await expect(page.getByRole("heading", { name: heading, exact: true })).toBeVisible();
  }

  await page.goto("/works");
  await expect(page.getByRole("table", { name: "Work results list" })).toBeVisible();
  await page.getByRole("button", { name: "Grid" }).click();
  await expect(page).toHaveURL(/view=grid/);
  await expect(page.getByLabel("Work results grid")).toBeVisible();
  await page.getByLabel("State", { exact: true }).fill(state!);
  await expect(page).toHaveURL(/state=/);
  await expect(page).toHaveURL(/view=grid/);
  await expect(page.getByLabel("Work results grid")).toBeVisible();

  await page.goto("/search");
  await page.getByLabel("Search the active dataset").fill(state!.toLowerCase());
  await page.getByRole("button", { name: "Search" }).click();
  await expect(page.getByRole("heading", { name: new RegExp(`Results for “${state}`, "i") })).toBeVisible({ timeout: 90_000 });
});

test("dashboard creates a complete print-safe report from current active-release content", async ({ page }) => {
  await page.goto("/dashboard");
  await expect(page.getByRole("button", { name: "Generate Report" }).first()).toBeVisible({ timeout: 90_000 });
  const popupReady = page.waitForEvent("popup");
  await page.getByRole("button", { name: "Generate Report" }).first().click();
  const report = await popupReady;
  await expect(report.getByRole("heading", { name: "MPLADS Dashboard Report" })).toBeVisible();
  await expect(report.getByRole("heading", { name: "Supporting data" })).toBeVisible();
  await expect(report.getByText("MPLADS active dataset", { exact: false }).first()).toBeVisible();
  await expect(report.getByRole("button")).toHaveCount(0);
});

test("work detail page creates a complete print-safe dossier report from current work data", async ({ page, request }) => {
  const res = await request.get("http://127.0.0.1:8001/api/v1/works?page_size=1").catch(() => null);
  const works = (res && res.ok()) ? res : await request.get("http://127.0.0.1:8000/api/v1/works?page_size=1");
  expect(works.ok()).toBeTruthy();
  const workPayload = await works.json() as { items: Array<{ canonical_work_key: string; work_id: string | null }> };
  const workKey = workPayload.items[0]?.canonical_work_key;
  expect(workKey).toBeTruthy();

  await page.goto(`/works/${workKey}`);
  await expect(page.getByRole("button", { name: "Generate Report" }).first()).toBeVisible({ timeout: 90_000 });
  await expect(page.getByRole("button", { name: "Print / Save PDF" }).first()).toBeVisible();

  const popupReady = page.waitForEvent("popup");
  await page.getByRole("button", { name: "Generate Report" }).first().click();
  const report = await popupReady;
  await expect(report.getByRole("heading", { name: /MPLADS Work Detail Report/ })).toBeVisible({ timeout: 90_000 });
  await expect(report.getByRole("heading", { name: "Supporting data" })).toBeVisible();
  await expect(report.getByText("MPLADS active dataset", { exact: false }).first()).toBeVisible();
  await expect(report.getByRole("button")).toHaveCount(0);
});


test("public Monitoring navigation opens the existing protected shell and preserves its development profile", async ({ page }) => {
  await page.goto("/");
  const primaryNavigation = page.getByRole("navigation", { name: "Primary navigation" });
  await expect(primaryNavigation.getByRole("link", { name: "Monitoring" })).toHaveAttribute("href", "/monitoring");
  for (const publicLabel of ["Home", "Dashboard", "Works", "Search", "Monitoring", "About"]) {
    await expect(primaryNavigation.getByRole("link", { name: publicLabel, exact: true })).toBeVisible();
  }
  for (const protectedLabel of ["Risk", "Alerts", "Potential Duplicates", "Anomalies", "Financial", "Lifecycle", "Reviews", "Peer comparison", "Recommendations", "Executive", "Ask AI", "Admin", "MPs", "States", "Districts", "Statistics"]) {
    await expect(primaryNavigation.getByRole("link", { name: protectedLabel, exact: true })).toHaveCount(0);
  }

  await primaryNavigation.getByRole("link", { name: "Monitoring" }).click();
  await expect(page).toHaveURL(/\/monitoring$/);
  await expect(page.getByRole("heading", { name: "Authorized monitoring" })).toBeVisible();
  await expect(page.getByRole("link", { name: "Risk", exact: true })).toHaveCount(0);

  await page.getByLabel("Authorized actor identity").fill("playwright-public-monitoring");
  await page.getByRole("button", { name: "Continue to monitoring" }).click();
  await expect(page.getByText("Risk-assessed works")).toBeVisible();
  await expect(page.getByRole("figure", { name: "Risk distribution" })).toBeVisible();

  await page.reload();
  await expect(page).toHaveURL(/\/monitoring$/);
  await expect(page.getByText("Risk-assessed works")).toBeVisible();
  await page.getByRole("link", { name: "Risk", exact: true }).click();
  await expect(page).toHaveURL(/\/monitoring\/risk$/);
  await expect(page.getByRole("heading", { name: "Risk-ranked works" })).toBeVisible();

  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/");
  await page.getByRole("button", { name: "Open navigation" }).click();
  await expect(page.getByRole("navigation", { name: "Mobile navigation" }).getByRole("link", { name: "Monitoring" })).toHaveAttribute("href", "/monitoring");
});

test("authorized monitoring uses the protected active-release APIs", async ({ page }) => {
  await page.goto("/monitoring");
  await expect(page.getByRole("heading", { name: "Authorized monitoring" })).toBeVisible();
  await page.getByLabel("Authorized actor identity").fill("playwright-reviewer");
  await page.getByRole("button", { name: "Continue to monitoring" }).click();
  await expect(page.getByText("Risk-assessed works")).toBeVisible({ timeout: 90_000 });
  await expect(page.getByText("Active dataset release", { exact: false })).toBeVisible({ timeout: 90_000 });

  await page.getByRole("link", { name: "Executive" }).click();
  await expect(page.getByRole("heading", { name: "Executive command center" })).toBeVisible();

  await page.getByRole("link", { name: "Risk", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Risk-ranked works" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Risk indicators" })).toBeVisible();

  await page.getByRole("link", { name: "Potential Duplicates", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Potential duplicate candidates" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Candidate pairs" })).toBeVisible();

  await page.getByRole("link", { name: "Reviews", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Review queue" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Cases" })).toBeVisible();

  await page.getByRole("link", { name: "Peer comparison", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Peer benchmarking" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Peer benchmark results" })).toBeVisible();

  await page.getByRole("link", { name: "Recommendations", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Review recommendations" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Recommendations", exact: true })).toBeVisible();
});

test("authorized monitoring risk, anomaly, and alert queues preserve live Grid and List views", async ({ page }) => {
  await page.goto("/monitoring");
  await page.getByLabel("Authorized actor identity").fill("playwright-record-views");
  await page.getByRole("button", { name: "Continue to monitoring" }).click();

  const views = [
    ["Risk", "Risk result view", "Risk indicator grid", "Risk indicator list"],
    ["Anomalies", "Anomaly result view", "Risk indicator grid", "Risk indicator list"],
    ["Alerts", "Alert result view", "Alert result grid", "Alert result list"],
  ] as const;

  for (const [link, toggle, grid, list] of views) {
    await page.getByRole("link", { name: link, exact: true }).click();
    await expect(page.getByLabel(list)).toBeVisible({ timeout: 90_000 });
    const controls = page.getByRole("group", { name: toggle });
    await controls.getByRole("button", { name: "Grid" }).click();
    await expect(page.getByLabel(grid)).toBeVisible({ timeout: 90_000 });
    await expect(page).toHaveURL(/view=grid/);
    await controls.getByRole("button", { name: "List" }).click();
    await expect(page.getByLabel(list)).toBeVisible({ timeout: 90_000 });
  }
});

test("authorized monitoring duplicate, review, and recommendation queues preserve live Grid and List views", async ({ page }) => {
  await page.goto("/monitoring");
  await page.getByLabel("Authorized actor identity").fill("playwright-workflow-views");
  await page.getByRole("button", { name: "Continue to monitoring" }).click();

  const views = [
    ["Potential Duplicates", "Potential duplicate result view", "Potential duplicate result grid", "Potential duplicate result list"],
    ["Reviews", "Review case view", "Review case grid", "Review case list"],
    ["Recommendations", "Recommendation result view", "Recommendation result grid", "Recommendation result list"],
  ] as const;

  for (const [link, toggle, grid, list] of views) {
    await page.getByRole("link", { name: link, exact: true }).click();
    await expect(page.getByLabel(list)).toBeVisible({ timeout: 90_000 });
    const controls = page.getByRole("group", { name: toggle });
    await controls.getByRole("button", { name: "Grid" }).click();
    await expect(page.getByLabel(grid)).toBeVisible({ timeout: 90_000 });
    await expect(page).toHaveURL(/view=grid/);
    await controls.getByRole("button", { name: "List" }).click();
    await expect(page.getByLabel(list)).toBeVisible({ timeout: 90_000 });
  }
});

test("Ask AI is authorization-gated and renders a bounded verified no-data result", async ({ page }) => {
  await page.goto("/monitoring/ai");
  await expect(page.getByRole("heading", { name: "Authorized monitoring" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Ask AI" })).not.toBeVisible();

  await page.getByLabel("Development role").selectOption("STATE_NODAL_AUTHORITY");
  await page.getByLabel("Authorized actor identity").fill("playwright-ask-ai");
  await page.getByLabel("Authorized State").fill("Not an authorized state");
  await page.getByRole("button", { name: "Continue to monitoring" }).click();
  await page.getByRole("link", { name: "Ask AI", exact: true }).click();
  await expect(page.getByRole("heading", { name: "MPLADS AI Assistant" })).toBeVisible();

  await page.getByPlaceholder(/Ask about MPLADS data or monitoring evidence/).fill("What is the current risk distribution?");
  await page.getByRole("button", { name: "Ask AI", exact: true }).click();
  await expect(page.getByRole("heading", { name: "No verified records" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Source and provenance" })).toBeVisible();
  await expect(page.getByText("MPLADS active dataset")).toBeVisible();
  await expect(page.getByRole("link", { name: "Risk-ranked works" })).toBeVisible();
});

test("Ask AI renders a verified work-status chart and safely rejects a forecast", async ({ page }) => {
  await page.route("**/api/v1/ai/ask", async (route) => {
    const request = route.request().postDataJSON() as { question?: string };
    const forecast = request.question?.toLowerCase().includes("next year");
    const shared = { request_id: "playwright-ai", tool_results_summary: forecast ? {} : { work_status_by_house: [{ house: "LOK_SABHA", status: "COMPLETED", work_count: 2 }] }, tool_result: forecast ? null : { tool_name: "get_work_summary", success: true, data: { work_status_by_house: [{ house: "LOK_SABHA", status: "COMPLETED", work_count: 2 }] }, result_count: 1, truncated: false, filters_applied: { view: "WORK_STATUS_BY_HOUSE" }, scope: {}, dataset_version: "verified-release", generated_at: "2026-01-01T00:00:00Z", warnings: [], navigation_links: [] }, grounding: { source_data: "Verified data returned by an authorized MPLADS backend tool.", analytical_result: "Persisted monitoring output.", explanation: "Gemini prose is non-authoritative and cannot replace the verified result." }, provenance: { tool_used: forecast ? null : "get_work_summary", filters_applied: {}, authorized_scope: { role: "PLATFORM_ADMINISTRATOR", state: null, district_or_ida: null, mp: null }, dataset_version: "verified-release" }, dataset_version: "verified-release", generated_at: "2026-01-01T00:00:00Z", scope: { role: "PLATFORM_ADMINISTRATOR", state: null, district_or_ida: null, mp: null }, warnings: [], navigation_links: [], clarification_required: false, clarification_options: [] };
    await route.fulfill({ contentType: "application/json", body: JSON.stringify(forecast ? { ...shared, answer: "Forecasts are not available from the current active dataset.", intent: "UNSUPPORTED_QUERY", visualization: null } : { ...shared, answer: "The verified source-status composition is shown below.", intent: "WORK_QUERY", visualization: { title: "Source work status by House", description: "Verified active-release result.", chart_type: "STACKED_BAR", x_axis: "House", y_axis: "Works", unit: "Works", series: [{ key: "series_0", label: "COMPLETED" }], rows: [{ label: "LOK SABHA", value: 2, series_0: 2 }], record_count: 1, data_available: true, selection: { rule: "category_composition", rationale: "Verified categories are stacked by House.", source: "verified_tool_result" } } }) });
  });
  await page.goto("/monitoring/ai");
  await page.getByLabel("Development role").selectOption("PLATFORM_ADMINISTRATOR");
  await page.getByLabel("Authorized actor identity").fill("playwright-phase152");
  await page.getByRole("button", { name: "Continue to monitoring" }).click();
  await page.getByRole("link", { name: "Ask AI", exact: true }).click();

  const question = page.getByPlaceholder(/Ask about MPLADS data or monitoring evidence/);
  await question.fill("Show work status by House");
  await page.getByRole("button", { name: "Ask AI", exact: true }).click();
  await expect(page.getByText("Intent: WORK QUERY")).toBeVisible();
  await expect(page.getByRole("figure", { name: "Source work status by House" })).toBeVisible();
  await expect(page.getByRole("figure", { name: "Source work status by House" }).getByText("Inspect supporting table")).toBeVisible();
  await expect(page.getByText("MPLADS active dataset")).toBeVisible();
  await expect(page.getByRole("button", { name: "Download CSV" })).toBeVisible();

  await question.fill("What will MPLADS expenditure be next year?");
  await page.getByRole("button", { name: "Ask AI", exact: true }).click();
  await expect(page.getByText("Intent: UNSUPPORTED QUERY")).toBeVisible();
  await expect(page.getByRole("heading", { name: "Verified visualization" })).toHaveCount(0);
});

test("Administration is server-guarded and exposes only real platform state", async ({ page }) => {
  await page.goto("/admin/access-requests");
  await expect(page.getByRole("heading", { name: "Authorized monitoring" })).toBeVisible();
  await page.getByLabel("Development role").selectOption("STATE_NODAL_AUTHORITY");
  await page.getByLabel("Authorized actor identity").fill("playwright-admin-denied");
  await page.getByLabel("Authorized State").fill("Not an administrator state");
  await page.getByRole("button", { name: "Continue to monitoring" }).click();
  await expect(page.getByText("Platform Administrator access required")).toBeVisible();

  await page.getByRole("button", { name: "Sign out" }).click();
  await page.getByLabel("Development role").selectOption("PLATFORM_ADMINISTRATOR");
  await page.getByLabel("Authorized actor identity").fill("playwright-platform-admin");
  await page.getByRole("button", { name: "Continue to monitoring" }).click();
  await expect(page.getByRole("heading", { name: "Access requests", exact: true })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Requests", exact: true })).toBeVisible();

  for (const label of ["Users & Roles", "Datasets", "Data Quality", "Audit Logs", "System Health"]) {
    await page.getByRole("link", { name: label, exact: true }).click();
    await expect(page.getByText("Administration", { exact: true }).first()).toBeVisible();
  }
  await expect(page.getByText("Live operational status only", { exact: false })).toBeVisible();
  await expect(page.getByText(/SQLite|AIza/)).toHaveCount(0);
});
