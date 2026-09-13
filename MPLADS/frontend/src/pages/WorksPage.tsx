import { useCallback, useMemo } from "react";
import { ArrowRight, ArrowUpDown, Search } from "lucide-react";
import { Link, useSearchParams } from "react-router-dom";
import { api } from "../api/client";
import type { Filters, WorkListItem } from "../api/types";
import { EmptyState, ErrorState, LoadingBlock } from "../components/DataState";
import { FilterBar } from "../components/FilterBar";
import { PageHeader } from "../components/PageHeader";
import { Pagination } from "../components/Pagination";
import { Panel } from "../components/Panel";
import { SourceIndicator } from "../components/SourceIndicator";
import { StatusBadge } from "../components/StatusBadge";
import { ViewToggle, type CollectionView, getPersistedView, setPersistedView } from "../components/ViewToggle";
import { useApi } from "../hooks/useApi";
import { SourceText } from "../components/SourceText";
import { filtersFromSearch, queryFromFilters } from "../lib/filters";
import { displayHouse } from "../lib/format";

function WorkGrid({ items }: { items: WorkListItem[] }) {
  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3" aria-label="Work results grid">
      {items.map((item) => {
        return (
          <article
            key={item.canonical_work_key}
            className="group flex min-h-64 flex-col justify-between rounded-lg border border-line bg-white p-5 shadow-xs transition hover:border-blue-300 hover:shadow-md"
          >
            <div>
              <div className="flex items-start justify-between gap-3">
                <div>
                  <p className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Work ID</p>
                  <Link
                    to={`/works/${encodeURIComponent(item.canonical_work_key)}`}
                    className="mt-0.5 block font-semibold text-blue underline-offset-4 hover:underline break-all"
                  >
                    {item.work_id ?? item.canonical_work_key}
                  </Link>
                </div>
                <StatusBadge value={displayHouse(item.house)} />
              </div>

              <div className="mt-3.5">
                <SourceText
                  text={item.work_description}
                  clamp
                  className="text-sm font-medium leading-snug text-ink"
                />
              </div>

              <dl className="mt-4 grid grid-cols-2 gap-x-3 gap-y-2 border-t border-line/80 pt-3 text-xs">
                <div>
                  <dt className="text-slate-400 font-medium">State</dt>
                  <dd className="mt-0.5 font-medium text-slate-700 truncate" title={item.state ?? undefined}>
                    {item.state ?? "Not available"}
                  </dd>
                </div>
                <div>
                  <dt className="text-slate-400 font-medium">District / IDA</dt>
                  <dd className="mt-0.5 font-medium text-slate-700 truncate" title={item.district_or_ida ?? undefined}>
                    {item.district_or_ida ?? "Not available"}
                  </dd>
                </div>
                {item.financial_year && (
                  <div>
                    <dt className="text-slate-400 font-medium">Financial year</dt>
                    <dd className="mt-0.5 font-medium text-slate-700">{item.financial_year}</dd>
                  </div>
                )}
                {item.source_work_category && (
                  <div>
                    <dt className="text-slate-400 font-medium">Category</dt>
                    <dd className="mt-0.5 font-medium text-slate-700 truncate" title={item.source_work_category}>
                      {item.source_work_category}
                    </dd>
                  </div>
                )}
              </dl>
            </div>

            <div className="mt-4 pt-3 border-t border-line/60 flex items-center justify-between">
              <Link
                className="inline-flex items-center gap-1.5 text-xs font-semibold text-blue hover:text-navy hover:underline"
                to={`/works/${encodeURIComponent(item.canonical_work_key)}`}
              >
                View Details <ArrowRight className="size-3.5 transition group-hover:translate-x-1" aria-hidden="true" />
              </Link>
            </div>
          </article>
        );
      })}
    </div>
  );
}

function WorkList({ items }: { items: WorkListItem[] }) {
  return (
    <div className="overflow-x-auto">
      <table className="min-w-[1080px] w-full text-left text-sm" aria-label="Work results list">
        <thead className="sticky top-0 z-10 bg-slate-50">
          <tr className="border-b border-line text-xs uppercase tracking-wide text-slate-500">
            <th className="px-3 py-3 font-medium">Work ID</th>
            <th className="px-3 py-3 font-medium">Work title</th>
            <th className="px-3 py-3 font-medium">House</th>
            <th className="px-3 py-3 font-medium">State</th>
            <th className="px-3 py-3 font-medium">District / IDA</th>
            <th className="px-3 py-3 font-medium">Financial year</th>
            <th className="px-3 py-3 text-right font-medium">Action</th>
          </tr>
        </thead>
        <tbody>
          {items.map((item) => {
            return (
              <tr key={item.canonical_work_key} className="border-b border-line/70 align-top last:border-0 hover:bg-blue-50/30">
                <td className="px-3 py-3">
                  <Link to={`/works/${encodeURIComponent(item.canonical_work_key)}`} className="font-medium text-blue underline-offset-4 hover:underline">
                    {item.work_id ?? item.canonical_work_key}
                  </Link>
                </td>
                <td className="max-w-sm px-3 py-3 leading-5 text-slate-700">
                  <SourceText text={item.work_description} clamp />
                </td>
                <td className="px-3 py-3">
                  <StatusBadge value={displayHouse(item.house)} />
                </td>
                <td className="px-3 py-3 text-slate-700">{item.state ?? "Not available"}</td>
                <td className="px-3 py-3 text-slate-700">{item.district_or_ida ?? "Not available"}</td>
                <td className="px-3 py-3 text-slate-700">{item.financial_year ?? "Not available"}</td>
                <td className="px-3 py-3 text-right">
                  <Link className="button-quiet" to={`/works/${encodeURIComponent(item.canonical_work_key)}`}>
                    View details <ArrowRight className="size-3.5" aria-hidden="true" />
                  </Link>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

export default function WorksPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const filters = useMemo(() => filtersFromSearch(searchParams), [searchParams]);
  const page = Math.max(1, Number(searchParams.get("page") ?? 1) || 1);
  const searchText = searchParams.get("search") ?? "";
  const sort = searchParams.get("sort") ?? "work_id";
  const persistedView = getPersistedView("works", "grid");
  const viewParam = searchParams.get("view");
  const view: CollectionView = viewParam === "list" ? "list" : viewParam === "grid" ? "grid" : persistedView;

  const update = (nextFilters: Filters, nextPage = 1, nextSearch = searchText, nextSort = sort, nextView = view) => {
    setPersistedView("works", nextView);
    const query = queryFromFilters(nextFilters);
    if (nextPage > 1) query.set("page", String(nextPage));
    if (nextSearch) query.set("search", nextSearch);
    if (nextSort !== "work_id") query.set("sort", nextSort);
    query.set("view", nextView);
    setSearchParams(query);
  };

  const request = useCallback(
    (signal: AbortSignal) => api.listWorks({ ...filters, search: searchText, sort, page, page_size: 25 }, signal),
    [filters, page, searchText, sort]
  );
  const result = useApi(request, [request]);
  const firstVisible = result.data?.pagination.total ? (result.data.pagination.page - 1) * result.data.pagination.page_size + 1 : 0;
  const lastVisible = result.data ? Math.min(result.data.pagination.page * result.data.pagination.page_size, result.data.pagination.total) : 0;

  return (
    <div>
      <PageHeader
        eyebrow="Work explorer"
        title="Browse active MPLADS work records"
        description="A server-paginated catalogue of canonical works. Search and filters are executed by the analytical API, not against an in-browser copy."
      />
      <FilterBar filters={filters} onChange={(next) => update(next)} onReset={() => update({})} />
      <section className="mt-6">
        <Panel
          title="Works"
          description="Use Grid for record context or List for rapid scanning. Fields appear only when provided by the canonical-work API."
          actions={
            <div className="flex flex-wrap items-center gap-2">
              <ViewToggle value={view} onChange={(next) => update(filters, 1, searchText, sort, next)} label="Works view" />
              <label className="relative">
                <span className="sr-only">Search works</span>
                <Search className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-slate-400" aria-hidden="true" />
                <input
                  className="field-control w-56 pl-9"
                  value={searchText}
                  onChange={(event) => update(filters, 1, event.target.value)}
                  placeholder="Work ID, description, MP…"
                />
              </label>
              <label className="relative">
                <span className="sr-only">Sort works</span>
                <ArrowUpDown className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-slate-400" aria-hidden="true" />
                <select className="field-control pl-9" value={sort} onChange={(event) => update(filters, 1, searchText, event.target.value)}>
                  <option value="work_id">Work ID</option>
                  <option value="state">State</option>
                  <option value="mp">MP</option>
                  <option value="financial_year">Financial year</option>
                </select>
              </label>
            </div>
          }
        >
          {result.loading && !result.data ? (
            <LoadingBlock label="Loading works…" />
          ) : result.error && !result.data ? (
            <ErrorState error={result.error} onRetry={result.reload} />
          ) : result.data ? (
            <>
              <div className="mb-4 flex items-center justify-between text-sm text-slate-600">
                <span>
                  Showing {firstVisible.toLocaleString("en-IN")}–{lastVisible.toLocaleString("en-IN")} of{" "}
                  {result.data.pagination.total.toLocaleString("en-IN")}
                </span>
                <span>{view === "grid" ? "Grid view" : "List view"}</span>
              </div>
              {view === "grid" ? <WorkGrid items={result.data.items} /> : <WorkList items={result.data.items} />}
              {!result.data.items.length && (
                <EmptyState title="No works match the selected filters." detail="Try adjusting filters or reset the current selection." />
              )}
              <Pagination page={result.data.pagination} onPageChange={(next) => update(filters, next)} />
              <SourceIndicator provenance={result.data.provenance} />
            </>
          ) : null}
        </Panel>
      </section>
    </div>
  );
}
