import { cleanup, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, describe, expect, it } from "vitest";
import { AppShell } from "./AppShell";

function renderShell(path = "/") {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route element={<AppShell />}>
          <Route path="/" element={<h1>Public page</h1>} />
          <Route path="/monitoring" element={<h1>Protected monitoring target</h1>} />
        </Route>
      </Routes>
    </MemoryRouter>,
  );
}

afterEach(cleanup);

describe("public navigation", () => {
  it("contains only the Monitoring entry for the protected experience and links to /monitoring", async () => {
    const user = userEvent.setup();
    renderShell();

    const navigation = screen.getByRole("navigation", { name: "Primary navigation" });
    const monitoring = within(navigation).getByRole("link", { name: "Monitoring" });
    expect(monitoring).toHaveAttribute("href", "/monitoring");
    for (const publicLabel of ["Home", "Dashboard", "Works", "Search", "Monitoring", "About"]) {
      expect(within(navigation).getByRole("link", { name: publicLabel })).toBeInTheDocument();
    }
    for (const protectedLabel of ["Risk", "Alerts", "Duplicates", "Anomalies", "Financial", "Lifecycle", "Reviews", "Peer comparison", "Recommendations", "Executive", "Ask AI", "Admin", "MPs", "States", "Districts", "Statistics"]) {
      expect(within(navigation).queryByRole("link", { name: protectedLabel })).not.toBeInTheDocument();
    }

    await user.click(monitoring);
    expect(screen.getByRole("heading", { name: "Protected monitoring target" })).toBeInTheDocument();
  });

  it("exposes the same Monitoring entry in the responsive navigation", async () => {
    const user = userEvent.setup();
    renderShell();

    await user.click(screen.getByRole("button", { name: "Open navigation" }));
    const mobileNavigation = screen.getByRole("navigation", { name: "Mobile navigation" });
    expect(within(mobileNavigation).getByRole("link", { name: "Monitoring" })).toHaveAttribute("href", "/monitoring");
  });
});
