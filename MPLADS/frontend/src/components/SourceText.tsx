import { useState } from "react";
import { AlertCircle } from "lucide-react";

export function SourceText({
  text,
  className = "",
  clamp = false,
  showRawToggle = false,
}: {
  text?: string | null;
  className?: string;
  clamp?: boolean;
  showRawToggle?: boolean;
}) {
  const [showRaw, setShowRaw] = useState(false);

  if (!text) {
    return <span className={`text-slate-400 italic ${className}`}>Description not available in source record.</span>;
  }

  // Check if string is predominantly question marks or replacement characters
  const qMarkCount = (text.match(/[\?\uFFFD]/g) || []).length;
  const nonSpaceLength = text.replace(/\s+/g, "").length;
  const isEntirelyCorrupted =
    nonSpaceLength > 0 &&
    (qMarkCount / nonSpaceLength > 0.35 || (/^[\s\d\W\?\uFFFD]+$/.test(text) && qMarkCount >= 3));

  if (isEntirelyCorrupted) {
    return (
      <div className={className}>
        <div className="flex flex-wrap items-center gap-1.5">
          <span className="inline-flex items-center gap-1 rounded bg-amber-50 px-2 py-0.5 text-xs font-medium text-amber-800 border border-amber-200">
            <AlertCircle className="size-3 text-amber-600 shrink-0" aria-hidden="true" />
            Source text unavailable
          </span>
          <span className="text-xs text-slate-500 italic">
            (Source encoding issue in portal dataset)
          </span>
          {showRawToggle && (
            <button
              type="button"
              onClick={() => setShowRaw(!showRaw)}
              className="text-[11px] text-blue hover:underline ml-1"
            >
              {showRaw ? "Hide raw artifact" : "View raw artifact"}
            </button>
          )}
        </div>
        {showRaw && (
          <p className="mt-1 font-mono text-[11px] text-slate-500 bg-slate-50 p-1.5 rounded border border-line break-all">
            {text}
          </p>
        )}
      </div>
    );
  }

  // If partially corrupted with blocks of repeated ??? or replacement chars
  const hasCorruptedBlocks = /\?{2,}|[\uFFFD]+/.test(text);

  if (hasCorruptedBlocks) {
    const parts = text.split(/(\?{2,}|[\uFFFD]+)/g);
    return (
      <div className={className}>
        <span className={clamp ? "line-clamp-3" : ""}>
          {parts.map((part, i) => {
            if (/\?{2,}|[\uFFFD]+/.test(part)) {
              return (
                <span
                  key={i}
                  className="inline-block text-[10px] font-medium text-amber-800 bg-amber-50 px-1 py-0.2 rounded border border-amber-200 mx-0.5 align-baseline"
                  title="Source encoding issue: character sequence unencoded in official portal"
                >
                  [Source encoding issue]
                </span>
              );
            }
            return <span key={i}>{part}</span>;
          })}
        </span>
      </div>
    );
  }

  // Valid Unicode / Latin / Numbers: render normally!
  return <span className={`${className} ${clamp ? "line-clamp-3" : ""}`}>{text}</span>;
}

export function cleanSourceText(text?: string | null): string {
  if (!text) {
    return "Description not available in source record.";
  }
  const qMarkCount = (text.match(/[\?\uFFFD]/g) || []).length;
  const nonSpaceLength = text.replace(/\s+/g, "").length;
  const isEntirelyCorrupted =
    nonSpaceLength > 0 &&
    (qMarkCount / nonSpaceLength > 0.35 || (/^[\s\d\W\?\uFFFD]+$/.test(text) && qMarkCount >= 3));

  if (isEntirelyCorrupted) {
    return "Source text unavailable";
  }

  return text.replace(/\?{2,}|[\uFFFD]+/g, "[Source encoding issue]").trim();
}
