import type { LucideIcon } from "lucide-react";
import { CircleHelp } from "lucide-react";

export function MetricCard({ label, value, exactValue, description, icon: Icon }: { label: string; value: string; exactValue?: string; description: string; icon?: LucideIcon }) {
  return <article className="group relative overflow-hidden rounded-lg border border-line bg-white p-5 shadow-sm transition duration-200 hover:-translate-y-0.5 hover:border-blue-200 hover:shadow-panel">
    <div className="absolute inset-x-0 top-0 h-0.5 bg-gradient-to-r from-[#d97706] via-blue to-[#18794e] opacity-0 transition group-hover:opacity-100" aria-hidden="true" />
    <div className="flex items-start justify-between gap-3"><div><div className="flex items-center gap-1.5 text-sm font-medium text-slate-600"><span>{label}</span><span className="group/help relative"><CircleHelp className="size-3.5" aria-hidden="true" /><span role="tooltip" className="pointer-events-none absolute bottom-full left-0 z-20 mb-2 hidden w-56 rounded bg-ink p-2 text-xs font-normal leading-5 text-white shadow-lg group-hover/help:block group-focus-within/help:block">{description}{exactValue ? ` Exact value: ${exactValue}.` : ""}</span></span></div><p className="mt-3 text-2xl font-semibold tracking-tight text-ink" title={exactValue ?? value} aria-label={exactValue ? `${label}: ${exactValue}` : undefined}>{value}</p></div>{Icon && <div className="rounded-md border border-blue-100 bg-blue-50 p-2.5 text-blue"><Icon className="size-5" aria-hidden="true" /></div>}</div>
  </article>;
}
