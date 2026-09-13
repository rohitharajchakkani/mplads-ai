import { useCallback, useEffect, useMemo, useState } from "react";
import { Filter, RotateCcw, X } from "lucide-react";
import { api } from "../api/client";
import type { AnalyticsResponse, FilterOption, FilterOptionsData, Filters, OptionField } from "../api/types";
import { useApi } from "../hooks/useApi";
import { filterLabels } from "../lib/filters";

export type { OptionField };

const dependencies: Partial<Record<OptionField, Array<keyof Filters>>> = {
  state: ["house"],
  district_or_ida: ["house", "state"],
  mp: ["house", "state", "district_or_ida"],
  work: ["house", "state", "district_or_ida", "mp"],
  financial_year: ["house", "state", "district_or_ida", "mp"],
  work_status: ["house", "state", "district_or_ida", "mp", "work"],
};
const dependentFields: Partial<Record<keyof Filters, Array<keyof Filters>>> = {
  house: ["state", "district_or_ida", "mp", "work"],
  state: ["district_or_ida", "mp", "work"],
  district_or_ida: ["mp", "work"],
  mp: ["work"],
};

function scopedFilters(field: OptionField, filters: Filters): Filters {
  const scoped: Filters = {};
  for (const key of dependencies[field] ?? []) if (filters[key]) scoped[key] = filters[key];
  return scoped;
}

function OptionInput({ field, filters, value, onChange }: { field: OptionField; filters: Filters; value?: string; onChange: (value: string) => void }) {
  const [focused, setFocused] = useState(false);
  const [debouncedValue, setDebouncedValue] = useState(value ?? "");

  // Debounce the input value so user typing doesn't fire rapid API requests
  useEffect(() => {
    if ((value ?? "") === debouncedValue) return;
    const timer = setTimeout(() => {
      setDebouncedValue(value ?? "");
    }, 250);
    return () => clearTimeout(timer);
  }, [value, debouncedValue]);

  const scope = useMemo(() => scopedFilters(field, filters), [field, filters]);
  const scopeKey = JSON.stringify(scope);
  
  // Only issue API request when focused or when there's an active filter or selection
  const shouldFetch = focused || Boolean(value);
  const request = useCallback(
    (signal: AbortSignal): Promise<AnalyticsResponse<FilterOptionsData>> => {
      if (!shouldFetch) {
        return Promise.resolve({
          data: { field, options: [] as FilterOption[], query: null, limited: false },
          provenance: { service: "filterOptions", release_version: "", batch_id: "", filters: {}, generated_at: "" }
        });
      }
      return api.filterOptions(field, scopedFilters(field, filters), debouncedValue, signal);
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [field, scopeKey, debouncedValue, shouldFetch]
  );

  const options = useApi<AnalyticsResponse<FilterOptionsData>>(request, [request]);
  const listId = `filter-options-${field}`;
  const data: FilterOptionsData | undefined = options.data?.data;
  const optionRows: FilterOption[] = Array.isArray(data?.options) ? data.options : [];
  const label = filterLabels[field] ?? field;

  return <label className="field-label relative">{label}
    <div className="relative flex items-center">
      <input
        className="field-control pr-7"
        list={listId}
        value={value ?? ""}
        onFocus={() => setFocused(true)}
        onChange={(event) => onChange(event.target.value)}
        placeholder={`All ${label}s`}
        aria-label={label}
        aria-describedby={`${listId}-status`}
        autoComplete="off"
      />
      {value ? (
        <button
          type="button"
          onClick={() => onChange("")}
          className="absolute right-2 text-slate-400 hover:text-slate-600 focus:outline-none"
          title={`Clear ${label}`}
          aria-label={`Clear ${label}`}
        >
          <X className="size-3.5" aria-hidden="true" />
        </button>
      ) : null}
    </div>
    <datalist id={listId}>
      {optionRows.map((option) => (
        <option key={option.value} value={option.value}>
          {option.label} ({option.count})
        </option>
      ))}
    </datalist>
    <span id={`${listId}-status`} className="mt-1 min-h-4 text-xs font-normal text-slate-500" aria-live="polite">
      {options.loading ? `Loading ${label.toLowerCase()} options…` : options.error ? `Unable to load ${label.toLowerCase()} options.` : data && optionRows.length === 0 && focused ? `No ${label.toLowerCase()} options match this selection.` : data?.limited ? "Refine your text to narrow the option list." : ""}
    </span>
  </label>;
}


export function FilterBar({ filters, onChange, onReset, includeStatus = true, fields: requestedFields }: { filters: Filters; onChange: (filters: Filters) => void; onReset: () => void; includeStatus?: boolean; fields?: OptionField[] }) {
  const update = (key: keyof Filters, value: string) => {
    const normalized = value.replace(/\s+/g, " ").trim();
    const next: Filters = { ...filters, [key]: normalized || undefined };
    for (const dependent of dependentFields[key] ?? []) next[dependent] = undefined;
    onChange(next);
  };
  const fields: OptionField[] = requestedFields ?? (includeStatus
    ? ["house", "state", "district_or_ida", "mp", "work", "financial_year", "work_status"]
    : ["house", "state", "district_or_ida", "mp", "work", "financial_year"]);
  const active = Object.entries(filters).filter(([, value]) => Boolean(value)) as Array<[keyof Filters, string]>;
  return <section className="overflow-hidden rounded-lg border border-line bg-white shadow-sm" aria-label="Data filters">
    <div className="gov-rule h-0.5" aria-hidden="true" /><div className="p-4"><div className="mb-3 flex flex-wrap items-center justify-between gap-3"><div><div className="flex items-center gap-2 font-medium text-ink"><Filter className="size-4 text-blue" aria-hidden="true" />Filter active-release results</div><p className="mt-1 text-xs text-slate-500">Refine the current view using values supplied by the API.</p></div><button className="button-quiet" type="button" onClick={onReset}><RotateCcw className="size-4" aria-hidden="true" />Clear filters</button></div>
    {active.length > 0 ? <div className="mb-4 flex flex-wrap gap-2" aria-label="Active filters">{active.map(([field, value]) => { const label = filterLabels[field] ?? field; return <button key={field} className="inline-flex items-center gap-1 rounded-full bg-blue-50 px-3 py-1 text-xs font-medium text-blue" type="button" onClick={() => update(field, "")} title={`Clear ${label}`}><span>{label}: {field === "house" ? value.replaceAll("_", " ") : value}</span><X className="size-3" aria-hidden="true" /></button>; })}</div> : <p className="mb-4 text-xs text-slate-500">No filters applied. Suggestions are sourced from the current active dataset.</p>}
    <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">{fields.map((field) => (
      <OptionInput key={field} field={field} filters={filters} value={filters[field]} onChange={(value) => update(field, value)} />
    ))}</div>
    <p className="mt-3 text-xs leading-5 text-slate-500">Choose a suggestion or type a source value manually. Text filters are normalized by the API, so case and ordinary repeated whitespace do not change the result.</p></div>
  </section>;
}
