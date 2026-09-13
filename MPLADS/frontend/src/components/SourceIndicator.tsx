import type { Provenance } from "../api/types";
import { Database, Info } from "lucide-react";
import { formatDateTime } from "../lib/format";

export function SourceIndicator({ provenance, compact = false }: { provenance?: Provenance; compact?: boolean }) {
  if (!provenance) return null;
  if (compact) {
    return (
      <span className="inline-flex items-center gap-1.5 text-xs text-slate-500">
        <Database className="size-3.5" aria-hidden="true" />
        Data source: MPLADS active dataset
      </span>
    );
  }
  return (
    <aside className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-blue-100 bg-blue-50/70 px-4 py-3 text-sm text-slate-700">
      <div className="flex flex-wrap items-center gap-2">
        <Info className="size-4 shrink-0 text-blue" aria-hidden="true" />
        <span className="font-medium text-ink">Data source: MPLADS active dataset</span>
        <span className="text-slate-400">·</span>
        <span className="text-xs text-slate-600">Generated {formatDateTime(provenance.generated_at)}</span>
      </div>
      {provenance.release_version ? (
        <details className="text-xs text-slate-500">
          <summary className="cursor-pointer text-slate-500 hover:text-slate-700 hover:underline">
            Technical details
          </summary>
          <span className="ml-1 font-mono text-[11px] bg-white px-2 py-0.5 rounded border border-blue-200 text-slate-700">
            Release: {provenance.release_version} {provenance.batch_id ? `· Batch: ${provenance.batch_id}` : ""}
          </span>
        </details>
      ) : null}
    </aside>
  );
}
