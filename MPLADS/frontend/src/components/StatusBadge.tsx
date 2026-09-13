export function getSemanticDot(val?: string | null): string {
  if (!val) return "bg-slate-400";
  const normalized = val.toUpperCase().replace(/[\s-]+/g, "_");
  switch (normalized) {
    case "VERY_HIGH":
      return "bg-red-600 ring-2 ring-red-300";
    case "HIGH":
      return "bg-rose-600";
    case "MEDIUM":
      return "bg-amber-500";
    case "LOW":
      return "bg-emerald-500";
    case "INFO":
    case "NORMAL":
    case "OPEN":
      return "bg-sky-500";
    case "UNDER_REVIEW":
      return "bg-amber-500";
    case "ACTION_INITIATED":
      return "bg-indigo-600";
    case "FOLLOW_UP_REQUIRED":
      return "bg-orange-500";
    case "RESOLVED":
    case "CLOSED":
    case "COMPLETED":
    case "APPROVED":
      return "bg-emerald-600";
    case "NOTED":
      return "bg-slate-400";
    case "REOPENED":
      return "bg-purple-600";
    case "PENDING":
      return "bg-amber-500";
    case "REJECTED":
    case "FAILED":
      return "bg-rose-600";
    default:
      return "bg-slate-400";
  }
}

export function getSemanticStyle(val?: string | null): string {
  if (!val) return "border-slate-200 bg-slate-50 text-slate-700";
  const normalized = val.toUpperCase().replace(/[\s-]+/g, "_");
  switch (normalized) {
    case "VERY_HIGH":
      return "border-red-400 bg-red-100/90 text-red-950 font-bold shadow-xs";
    case "HIGH":
      return "border-rose-300 bg-rose-50 text-rose-800 font-semibold shadow-xs";
    case "MEDIUM":
      return "border-amber-300 bg-amber-50 text-amber-900 font-medium";
    case "LOW":
      return "border-emerald-300 bg-emerald-50 text-emerald-800 font-medium";
    case "INFO":
    case "NORMAL":
      return "border-sky-200 bg-sky-50 text-sky-800 font-medium";
    case "OPEN":
      return "border-sky-300 bg-sky-50 text-sky-800 font-medium";
    case "UNDER_REVIEW":
      return "border-amber-300 bg-amber-50 text-amber-800 font-medium";
    case "ACTION_INITIATED":
      return "border-indigo-300 bg-indigo-50 text-indigo-800 font-medium";
    case "FOLLOW_UP_REQUIRED":
      return "border-orange-300 bg-orange-50 text-orange-800 font-medium";
    case "RESOLVED":
    case "CLOSED":
    case "COMPLETED":
      return "border-emerald-300 bg-emerald-50 text-emerald-800 font-medium";
    case "NOTED":
      return "border-slate-300 bg-slate-100 text-slate-700 font-medium";
    case "REOPENED":
      return "border-purple-300 bg-purple-50 text-purple-800 font-medium";
    case "PENDING":
      return "border-amber-300 bg-amber-50 text-amber-800 font-medium";
    case "APPROVED":
      return "border-emerald-300 bg-emerald-50 text-emerald-800 font-medium";
    case "REJECTED":
    case "FAILED":
      return "border-rose-300 bg-rose-50 text-rose-800 font-medium";
    default:
      return "border-slate-200 bg-slate-50 text-slate-700 font-medium";
  }
}

export function StatusBadge({ value }: { value: string | null | undefined }) {
  const style = getSemanticStyle(value);
  const dot = getSemanticDot(value);
  const display = value ? value.replaceAll("_", " ") : "Not available";
  return (
    <span className={`inline-flex max-w-56 items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs ${style}`}>
      <span className={`size-1.5 shrink-0 rounded-full ${dot}`} aria-hidden="true" />
      <span>{display}</span>
    </span>
  );
}

export function SeverityBadge({ value, label }: { value: string | null | undefined; label?: string }) {
  const style = getSemanticStyle(value);
  const dot = getSemanticDot(value);
  const display = value ? value.replaceAll("_", " ") : "Not available";
  return (
    <span className={`inline-flex items-center gap-1.5 rounded-md border px-2.5 py-1 text-xs tracking-wide uppercase ${style}`}>
      <span className={`size-1.5 shrink-0 rounded-full ${dot}`} aria-hidden="true" />
      {label && <span className="opacity-75">{label}:</span>}
      <span>{display}</span>
    </span>
  );
}
