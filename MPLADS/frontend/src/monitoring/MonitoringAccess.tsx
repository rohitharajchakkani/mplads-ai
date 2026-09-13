import { createContext, useContext, useState, type ReactNode } from "react";
import { LockKeyhole } from "lucide-react";
import { setMonitoringCredentials, type MonitoringCredentials } from "../api/client";
import type { MonitoringRole } from "../api/types";

interface AccessContext { credentials?: MonitoringCredentials; setCredentials: (value?: MonitoringCredentials) => void; }
const MonitoringAccessContext = createContext<AccessContext | undefined>(undefined);
const storageKey = "mplads-monitoring-development-profile";

export function MonitoringAccessProvider({ children }: { children: ReactNode }) {
  const [credentials, setCredentialsState] = useState<MonitoringCredentials | undefined>(() => {
    try {
      const stored = JSON.parse(sessionStorage.getItem(storageKey) ?? "null") as MonitoringCredentials | undefined;
      setMonitoringCredentials(stored);
      return stored;
    } catch {
      setMonitoringCredentials(undefined);
      return undefined;
    }
  });
  // This is only development UX state. Install it synchronously before protected
  // child effects run; the server still authorizes every request independently.
  const setCredentials = (value?: MonitoringCredentials) => { setMonitoringCredentials(value); setCredentialsState(value); if (value) sessionStorage.setItem(storageKey, JSON.stringify(value)); else sessionStorage.removeItem(storageKey); };
  return <MonitoringAccessContext.Provider value={{ credentials, setCredentials }}>{children}</MonitoringAccessContext.Provider>;
}

export function useMonitoringAccess() {
  const context = useContext(MonitoringAccessContext);
  if (!context) throw new Error("Monitoring access provider is missing.");
  return context;
}

export function DevelopmentAccessForm() {
  const { setCredentials } = useMonitoringAccess();
  const [role, setRole] = useState<MonitoringRole>("PLATFORM_ADMINISTRATOR");
  const [scope, setScope] = useState("");
  const [actor, setActor] = useState("");
  const scopeLabel = role === "MP" ? "Authorized MP source name" : role === "DISTRICT_AUTHORITY" ? "Authorized District / IDA" : role === "STATE_NODAL_AUTHORITY" ? "Authorized State" : "";
  const submit = (event: React.FormEvent) => { event.preventDefault(); setCredentials({ role, actor, ...(role === "MP" ? { mpScope: scope } : role === "DISTRICT_AUTHORITY" ? { districtScope: scope } : role === "STATE_NODAL_AUTHORITY" ? { stateScope: scope } : {}) }); };
  return <section className="mx-auto max-w-xl overflow-hidden rounded-lg border border-blue-100 bg-white shadow-panel"><div className="gov-rule h-1" aria-hidden="true" /><div className="p-6"><div className="grid size-11 place-items-center rounded-md border border-blue-100 bg-blue-50 text-blue"><LockKeyhole className="size-5" aria-hidden="true" /></div><p className="eyebrow mt-5">Protected workspace</p><h1 className="section-title mt-3 text-3xl font-semibold">Authorized monitoring</h1><p className="mt-3 leading-6 text-slate-600">Please sign in to access authorized monitoring. This local prototype sends a development role, scope, and actor header to the server; it is not production government authentication. The backend remains authoritative.</p><form onSubmit={submit} className="mt-6 grid gap-4"><label className="field-label">Development role<select className="field-control" value={role} onChange={(event) => { setRole(event.target.value as MonitoringRole); setScope(""); }}><option value="PLATFORM_ADMINISTRATOR">Platform Administrator</option><option value="MINISTRY">Ministry</option><option value="STATE_NODAL_AUTHORITY">State Nodal Authority</option><option value="DISTRICT_AUTHORITY">District Authority</option><option value="MP">MP</option></select></label><label className="field-label">Authorized actor identity<input className="field-control" required value={actor} onChange={(event) => setActor(event.target.value)} placeholder="Development review actor" /></label>{scopeLabel && <label className="field-label">{scopeLabel}<input className="field-control" required value={scope} onChange={(event) => setScope(event.target.value)} placeholder="Exact source value" /></label>}<button className="button-primary justify-self-start" type="submit">Continue to monitoring</button></form></div></section>;
}
