import type { ReactNode } from "react";
import { AlertCircle, DatabaseZap, LoaderCircle, RefreshCw } from "lucide-react";

export function LoadingBlock({ label = "Loading data…", className = "" }: { label?: string; className?: string }) {
  return <div className={`grid min-h-32 place-items-center rounded-xl border border-line bg-white p-6 text-sm text-slate-600 ${className}`} role="status" aria-live="polite"><span className="flex items-center gap-2"><LoaderCircle className="size-4 animate-spin" aria-hidden="true" />{label}</span></div>;
}

export function Skeleton({ className = "" }: { className?: string }) {
  return <div className={`animate-pulse rounded bg-slate-200 motion-reduce:animate-none ${className}`} aria-label="Loading" />;
}

export function EmptyState({ title = "No data available", detail = "No records match the current selection.", icon }: { title?: string; detail?: string; icon?: ReactNode }) {
  return <section className="grid min-h-36 place-items-center rounded-xl border border-dashed border-slate-300 bg-slate-50 px-6 py-8 text-center" aria-live="polite">
    <div className="max-w-md"><div className="mx-auto mb-3 grid size-9 place-items-center rounded-full bg-blue-50 text-blue">{icon ?? <DatabaseZap className="size-5" aria-hidden="true" />}</div><h3 className="font-semibold text-ink">{title}</h3><p className="mt-1 text-sm leading-6 text-slate-600">{detail}</p></div>
  </section>;
}

export function ErrorState({ error, onRetry, title = "Unable to load data." }: { error?: Error; onRetry?: () => void; title?: string }) {
  return <section className="grid min-h-36 place-items-center rounded-xl border border-red-200 bg-red-50 px-6 py-8 text-center" role="alert">
    <div className="max-w-md"><AlertCircle className="mx-auto mb-3 size-6 text-red-700" aria-hidden="true" /><h3 className="font-semibold text-red-950">{title}</h3><p className="mt-1 text-sm leading-6 text-red-900">{error?.message ?? "Please check the connection and try again."}</p>{onRetry && <button onClick={onRetry} className="button-secondary mt-4"><RefreshCw className="size-4" aria-hidden="true" />Retry</button>}</div>
  </section>;
}
