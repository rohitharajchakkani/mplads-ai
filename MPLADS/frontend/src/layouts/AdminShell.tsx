import { ClipboardCheck, Database, FileSearch, HeartPulse, ScrollText, Settings2, ShieldCheck, UsersRound } from "lucide-react";
import { NavLink, Outlet } from "react-router-dom";
import { DevelopmentAccessForm, useMonitoringAccess } from "../monitoring/MonitoringAccess";

const links = [
  ["Access Requests", "/admin/access-requests", ClipboardCheck],
  ["Users & Roles", "/admin/users", UsersRound],
  ["Datasets", "/admin/datasets", Database],
  ["Data Quality", "/admin/data-quality", FileSearch],
  ["Audit Logs", "/admin/audit-logs", ScrollText],
  ["System Health", "/admin/system", HeartPulse],
] as const;

export function AdminShell() {
  const { credentials, setCredentials } = useMonitoringAccess();
  if (!credentials) return <DevelopmentAccessForm />;
  return <div>
    <div className="mb-7 flex flex-wrap items-center justify-between gap-4 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3">
      <div><p className="text-xs font-semibold uppercase tracking-[0.14em] text-amber-900">Administration</p><p className="mt-1 text-sm text-slate-700">Platform administration is server-authorized. This browser profile does not grant access by itself.</p></div>
      <div className="flex items-center gap-2 text-sm"><ShieldCheck className="size-4 text-amber-800" aria-hidden="true" /><span>{credentials.role.replaceAll("_", " ")}</span><button type="button" className="button-secondary" onClick={() => setCredentials()}>Sign out</button></div>
    </div>
    <nav className="mb-7 flex gap-2 overflow-x-auto pb-1" aria-label="Administration navigation">
      {links.map(([label, to, Icon]) => <NavLink key={to} to={to} className={({ isActive }) => `inline-flex shrink-0 items-center gap-1.5 rounded-lg px-3 py-2 text-sm font-medium ${isActive ? "bg-navy text-white" : "border border-line bg-white text-slate-700 hover:border-blue hover:text-blue"}`}><Icon className="size-4" aria-hidden="true" />{label}</NavLink>)}
      <NavLink to="/admin/configuration" className={({ isActive }) => `inline-flex shrink-0 items-center gap-1.5 rounded-lg px-3 py-2 text-sm font-medium ${isActive ? "bg-navy text-white" : "border border-line bg-white text-slate-700 hover:border-blue hover:text-blue"}`}><Settings2 className="size-4" aria-hidden="true" />Configuration</NavLink>
    </nav>
    <Outlet />
  </div>;
}
