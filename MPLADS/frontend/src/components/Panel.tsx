import type { ReactNode } from "react";

export function Panel({ title, description, actions, children, className = "" }: { title: string; description?: string; actions?: ReactNode; children: ReactNode; className?: string }) {
  return <section className={`overflow-hidden rounded-lg border border-line bg-white shadow-sm ${className}`}>
    <header className="flex flex-wrap items-start justify-between gap-4 border-b border-line bg-slate-50/70 px-5 py-4"><div><h2 className="font-semibold text-ink">{title}</h2>{description && <p className="mt-1 text-sm leading-5 text-slate-600">{description}</p>}</div>{actions}</header>
    <div className="p-5">{children}</div>
  </section>;
}
