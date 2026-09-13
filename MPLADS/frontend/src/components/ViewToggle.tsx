import { LayoutGrid, List } from "lucide-react";

export type CollectionView = "grid" | "list";

export function getPersistedView(key: string, defaultView: CollectionView = "grid"): CollectionView {
  try {
    const saved = sessionStorage.getItem(`mplads_view_${key}`);
    if (saved === "grid" || saved === "list") return saved;
  } catch {
    // sessionStorage unavailable
  }
  return defaultView;
}

export function setPersistedView(key: string, view: CollectionView): void {
  try {
    sessionStorage.setItem(`mplads_view_${key}`, view);
  } catch {
    // ignore
  }
}

export function ViewToggle({
  value,
  onChange,
  label = "Result view",
}: {
  value: CollectionView;
  onChange: (view: CollectionView) => void;
  label?: string;
}) {
  return (
    <div className="inline-flex rounded-md border border-line bg-white p-0.5 shadow-sm" role="group" aria-label={label}>
      <button
        type="button"
        className={`inline-flex items-center gap-1.5 rounded px-2.5 py-1.5 text-sm font-medium transition ${
          value === "grid"
            ? "bg-navy text-white shadow-xs"
            : "text-slate-700 hover:bg-blue-50 hover:text-blue"
        }`}
        aria-pressed={value === "grid"}
        onClick={() => onChange("grid")}
      >
        <LayoutGrid className="size-4" aria-hidden="true" />
        <span>Grid</span>
        {value === "grid" && (
          <span className="text-xs font-bold text-emerald-300" aria-hidden="true">
            ✓
          </span>
        )}
      </button>
      <button
        type="button"
        className={`inline-flex items-center gap-1.5 rounded px-2.5 py-1.5 text-sm font-medium transition ${
          value === "list"
            ? "bg-navy text-white shadow-xs"
            : "text-slate-700 hover:bg-blue-50 hover:text-blue"
        }`}
        aria-pressed={value === "list"}
        onClick={() => onChange("list")}
      >
        <List className="size-4" aria-hidden="true" />
        <span>List</span>
        {value === "list" && (
          <span className="text-xs font-bold text-emerald-300" aria-hidden="true">
            ✓
          </span>
        )}
      </button>
    </div>
  );
}
