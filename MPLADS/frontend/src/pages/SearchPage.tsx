import { useCallback, useEffect, useMemo, useState } from "react";
import { ArrowRight, Building2, Landmark, MapPin, Search, User, X } from "lucide-react";
import { Link, useSearchParams } from "react-router-dom";
import { api } from "../api/client";
import type { SearchItem } from "../api/types";
import { EmptyState, ErrorState, LoadingBlock, Skeleton } from "../components/DataState";
import { PageHeader } from "../components/PageHeader";
import { Pagination } from "../components/Pagination";
import { Panel } from "../components/Panel";
import { SourceIndicator } from "../components/SourceIndicator";
import { SourceText } from "../components/SourceText";
import { useApi } from "../hooks/useApi";
import { displayHouse } from "../lib/format";

function destination(item: SearchItem): string | undefined {
  if (!item.identifier) return undefined;
  if (item.entity_type === "WORK") return `/works/${encodeURIComponent(item.identifier)}`;
  if (item.entity_type === "MP") return `/mps/${encodeURIComponent(item.identifier)}`;
  if (item.entity_type === "STATE") return `/states/${encodeURIComponent(item.identifier)}`;
  if (item.entity_type === "DISTRICT_OR_IDA") return `/districts/${encodeURIComponent(item.identifier)}`;
  if (item.entity_type === "CONSTITUENCY" && item.label) return `/works?search=${encodeURIComponent(item.label)}`;
  return undefined;
}

const TYPE_ORDER: Array<SearchItem["entity_type"]> = ["STATE", "DISTRICT_OR_IDA", "MP", "WORK", "CONSTITUENCY"];

const TYPE_LABELS: Record<string, { label: string; icon: typeof Building2 }> = {
  STATE: { label: "States", icon: MapPin },
  DISTRICT_OR_IDA: { label: "Districts / IDA", icon: MapPin },
  MP: { label: "Members of Parliament", icon: User },
  WORK: { label: "Works", icon: Building2 },
  CONSTITUENCY: { label: "Constituencies", icon: Landmark },
};

export default function SearchPage() {
  const [params, setParams] = useSearchParams();
  const q = params.get("q") ?? "";
  const page = Math.max(1, Number(params.get("page") ?? 1) || 1);
  const selectedType = params.get("type") ?? "ALL";
  const [term, setTerm] = useState(q);

  useEffect(() => setTerm(q), [q]);

  const request = useCallback((signal: AbortSignal) => (q ? api.search(q, page, 25, signal) : Promise.resolve(undefined)), [page, q]);
  const result = useApi(request, [request]);

  const submit = (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const next = term.trim().replace(/\s+/g, " ");
    setParams(next ? { q: next } : {});
  };

  const clear = () => {
    setTerm("");
    setParams({});
  };

  const setPage = (next: number) => {
    const nextParams: Record<string, string> = { q, page: String(next) };
    if (selectedType !== "ALL") nextParams.type = selectedType;
    setParams(nextParams);
  };

  const setType = (type: string) => {
    const nextParams: Record<string, string> = { q, page: "1" };
    if (type !== "ALL") nextParams.type = type;
    setParams(nextParams);
  };

  const allItems = result.data?.items ?? [];
  const filteredItems = useMemo(() => {
    if (selectedType === "ALL") return allItems;
    return allItems.filter((item) => item.entity_type === selectedType);
  }, [allItems, selectedType]);

  const groups = useMemo(() => {
    const map: Partial<Record<SearchItem["entity_type"], SearchItem[]>> = {};
    for (const item of filteredItems) {
      (map[item.entity_type] ??= []).push(item);
    }
    return map;
  }, [filteredItems]);

  const typeCounts = useMemo(() => {
    const counts: Record<string, number> = { ALL: allItems.length };
    for (const item of allItems) {
      counts[item.entity_type] = (counts[item.entity_type] ?? 0) + 1;
    }
    return counts;
  }, [allItems]);

  return (
    <div>
      <PageHeader
        eyebrow="Global search"
        title="Search the active dataset"
        description="Search Work ID, title/description, MP names, States, or District / IDA values. Case-insensitive and backed by the active release."
      />

      <form onSubmit={submit} className="mb-6 flex max-w-2xl gap-2" role="search">
        <div className="relative flex-1">
          <label htmlFor="global-search-input" className="sr-only">Search the active dataset</label>
          <Search className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-slate-400" aria-hidden="true" />
          <input
            id="global-search-input"
            autoFocus
            className="field-control pl-9 pr-9"
            value={term}
            onChange={(event) => setTerm(event.target.value)}
            placeholder="Search Work ID, MP, State, or District / IDA"
            aria-label="Search the active dataset"
          />
          {term && (
            <button
              type="button"
              onClick={clear}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 focus:outline-none"
              aria-label="Clear search text"
            >
              <X className="size-4" />
            </button>
          )}
        </div>
        <button className="button-primary" type="submit">Search</button>
      </form>

      {!q ? (
        <EmptyState title="Start with a search" detail="Enter a Work ID, MP name, State, or District / IDA to query active release records." />
      ) : result.loading && !result.data ? (
        <div className="space-y-4">
          <LoadingBlock label={`Searching for “${q}”…`} />
          <div className="grid gap-3 sm:grid-cols-2">
            <Skeleton className="h-24" />
            <Skeleton className="h-24" />
          </div>
        </div>
      ) : result.error && !result.data ? (
        <ErrorState error={result.error} onRetry={result.reload} />
      ) : result.data ? (
        <Panel
          title={`Results for “${q}”`}
          description={`${result.data.pagination.total.toLocaleString("en-IN")} total matching record${result.data.pagination.total === 1 ? "" : "s"} found across active release.`}
        >
          {allItems.length > 0 && (
            <div className="mb-6 flex flex-wrap gap-2 border-b border-line pb-4" role="tablist" aria-label="Search result types">
              <button
                type="button"
                role="tab"
                aria-selected={selectedType === "ALL"}
                onClick={() => setType("ALL")}
                className={`rounded-full px-3 py-1 text-xs font-medium transition ${
                  selectedType === "ALL" ? "bg-blue text-white" : "bg-slate-100 text-slate-700 hover:bg-slate-200"
                }`}
              >
                All results ({allItems.length})
              </button>
              {TYPE_ORDER.map((type) => {
                const count = typeCounts[type] ?? 0;
                if (!count) return null;
                const config = TYPE_LABELS[type] ?? { label: type };
                return (
                  <button
                    key={type}
                    type="button"
                    role="tab"
                    aria-selected={selectedType === type}
                    onClick={() => setType(type)}
                    className={`rounded-full px-3 py-1 text-xs font-medium transition ${
                      selectedType === type ? "bg-blue text-white" : "bg-slate-100 text-slate-700 hover:bg-slate-200"
                    }`}
                  >
                    {config.label} ({count})
                  </button>
                );
              })}
            </div>
          )}

          <div className="space-y-8">
            {TYPE_ORDER.map((type) => {
              const items = groups[type];
              if (!items || !items.length) return null;
              const config = TYPE_LABELS[type] ?? { label: type.replaceAll("_", " "), icon: Building2 };
              const Icon = config.icon;

              return (
                <section key={type} aria-labelledby={`search-group-${type}`}>
                  <div className="mb-3 flex items-center justify-between border-b border-line pb-2">
                    <h2 id={`search-group-${type}`} className="flex items-center gap-2 text-sm font-semibold uppercase tracking-wider text-ink">
                      <Icon className="size-4 text-blue" aria-hidden="true" />
                      {config.label}
                    </h2>
                    <span className="text-xs text-slate-500">
                      {items.length} {config.label.toLowerCase()} on this page
                    </span>
                  </div>

                  <div className="divide-y divide-line">
                    {items.map((item, idx) => {
                      const to = destination(item);
                      const isWork = item.entity_type === "WORK";
                      const isMp = item.entity_type === "MP";
                      const isDistrict = item.entity_type === "DISTRICT_OR_IDA";
                      const isState = item.entity_type === "STATE";

                      return (
                        <div
                          key={`${item.entity_type}-${item.identifier}-${item.label}-${idx}`}
                          className="flex flex-col gap-2 py-3.5 sm:flex-row sm:items-center sm:justify-between"
                        >
                          <div className="min-w-0 flex-1">
                            <div className="flex flex-wrap items-center gap-2">
                              <span className="font-semibold text-ink">{item.label ?? "Not available"}</span>
                              {item.house && (
                                <span className="inline-flex rounded-md bg-slate-100 px-2 py-0.5 text-xs font-medium text-slate-700">
                                  {displayHouse(item.house)}
                                </span>
                              )}
                              {item.state && !isState && (
                                <span className="inline-flex items-center gap-1 text-xs text-slate-500">
                                  <MapPin className="size-3" />
                                  {item.state}
                                </span>
                              )}
                              {item.district && !isDistrict && (
                                <span className="text-xs text-slate-500">· {item.district}</span>
                              )}
                              {item.mp && !isMp && (
                                <span className="inline-flex items-center gap-1 text-xs text-slate-500">
                                  <User className="size-3" />
                                  {item.mp}
                                </span>
                              )}
                            </div>

                            {item.title && item.title !== item.label && (
                              <SourceText text={item.title} clamp className="mt-1 text-xs leading-5 text-slate-600" />
                            )}
                            {item.description && item.description !== item.title && (
                              <SourceText text={item.description} clamp className="mt-0.5 text-xs text-slate-500" />
                            )}
                          </div>

                          {to ? (
                            <Link className="button-secondary shrink-0 self-start sm:self-center" to={to}>
                              {isWork ? "View work" : isMp ? "View MP" : isState ? "View State" : isDistrict ? "View District" : "Explore"}
                              <ArrowRight className="size-3.5" aria-hidden="true" />
                            </Link>
                          ) : null}
                        </div>
                      );
                    })}
                  </div>
                </section>
              );
            })}
          </div>

          {!filteredItems.length && (
            <EmptyState title="No records found." detail="Try a more general term or review the spelling from source data." />
          )}

          {result.data.pagination && <Pagination page={result.data.pagination} onPageChange={setPage} />}
          <div className="mt-4">
            <SourceIndicator provenance={result.data.provenance} />
          </div>
        </Panel>
      ) : null}
    </div>
  );
}
