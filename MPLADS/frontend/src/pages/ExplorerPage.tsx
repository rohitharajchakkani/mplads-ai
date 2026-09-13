import { useCallback, useMemo } from "react";
import { ArrowRight, MapPin, Search, Users } from "lucide-react";
import { Link, useSearchParams } from "react-router-dom";
import { api } from "../api/client";
import type { DistrictListItem, Filters, MPListItem, StateListItem } from "../api/types";
import { EmptyState, ErrorState, LoadingBlock } from "../components/DataState";
import { FilterBar } from "../components/FilterBar";
import { PageHeader } from "../components/PageHeader";
import { Pagination } from "../components/Pagination";
import { Panel } from "../components/Panel";
import { SourceIndicator } from "../components/SourceIndicator";
import { StatusBadge } from "../components/StatusBadge";
import { ViewToggle, type CollectionView, getPersistedView, setPersistedView } from "../components/ViewToggle";
import { useApi } from "../hooks/useApi";
import { filtersFromSearch, queryFromFilters } from "../lib/filters";
import { displayHouse, formatInteger } from "../lib/format";

type ExplorerType = "mps" | "states" | "districts";

function ListSearch({ value, onChange, placeholder }: { value: string; onChange: (value: string) => void; placeholder: string }) {
  return <label className="relative block max-w-md"><span className="sr-only">{placeholder}</span><Search className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-slate-400" aria-hidden="true" /><input value={value} onChange={(event) => onChange(event.target.value)} className="field-control pl-9" placeholder={placeholder} /></label>;
}

function MpsGrid({ items }: { items: MPListItem[] }) {
  return <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3" aria-label="MP results grid">{items.map((item) => <article key={item.mp_id} className="group rounded-lg border border-line bg-white p-5 transition hover:border-blue-200 hover:shadow-panel"><div className="flex items-start justify-between gap-3"><div className="grid size-10 place-items-center rounded-md bg-blue-50 text-blue"><Users className="size-5" aria-hidden="true" /></div><StatusBadge value={displayHouse(item.house)} /></div><h2 className="mt-5 text-base font-semibold text-ink">{item.name}</h2><p className="mt-1 text-sm text-slate-600">{item.state ?? "State not available"}{item.constituency ? ` · ${item.constituency}` : ""}</p><div className="mt-5 flex items-end justify-between border-t border-line pt-4"><div><p className="text-xs text-slate-500">Canonical works</p><p className="mt-1 text-xl font-semibold text-ink">{formatInteger(item.work_count)}</p></div><Link className="inline-flex items-center gap-1 text-sm font-semibold text-blue hover:underline" to={`/mps/${encodeURIComponent(item.mp_id)}`}>View profile <ArrowRight className="size-4 transition group-hover:translate-x-1" aria-hidden="true" /></Link></div></article>)}</div>;
}

function MpsList({ items }: { items: MPListItem[] }) {
  return <div className="overflow-x-auto"><table className="min-w-[800px] w-full text-left text-sm" aria-label="MP results list"><thead className="sticky top-0 z-10 bg-slate-50"><tr className="border-b border-line text-xs uppercase tracking-wide text-slate-500"><th className="px-3 py-3 font-medium">MP</th><th className="px-3 py-3 font-medium">House</th><th className="px-3 py-3 font-medium">State</th><th className="px-3 py-3 font-medium">Constituency</th><th className="px-3 py-3 text-right font-medium">Works</th><th className="px-3 py-3 text-right font-medium">Action</th></tr></thead><tbody>{items.map((item) => <tr key={item.mp_id} className="border-b border-line/70 last:border-0 hover:bg-blue-50/30"><td className="px-3 py-3 font-medium text-ink">{item.name}</td><td className="px-3 py-3"><StatusBadge value={displayHouse(item.house)} /></td><td className="px-3 py-3 text-slate-700">{item.state ?? "Not available"}</td><td className="px-3 py-3 text-slate-700">{item.constituency ?? "Not available"}</td><td className="px-3 py-3 text-right font-medium text-ink">{formatInteger(item.work_count)}</td><td className="px-3 py-3 text-right"><Link className="button-quiet" to={`/mps/${encodeURIComponent(item.mp_id)}`}>View profile <ArrowRight className="size-3.5" aria-hidden="true" /></Link></td></tr>)}</tbody></table></div>;
}

function StateGrid({ items }: { items: StateListItem[] }) {
  return <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3" aria-label="State results grid">{items.map((item) => <Link className="group rounded-lg border border-line bg-white p-5 transition hover:border-blue-200 hover:shadow-panel focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue" key={item.state_id} to={`/states/${encodeURIComponent(item.state_id)}`}><div className="flex items-start justify-between gap-3"><div className="grid size-10 place-items-center rounded-md bg-blue-50 text-blue"><MapPin className="size-5" aria-hidden="true" /></div><ArrowRight className="size-4 text-slate-400 transition group-hover:translate-x-1 group-hover:text-blue" aria-hidden="true" /></div><h2 className="mt-5 text-base font-semibold text-ink">{item.name}</h2><p className="mt-4 border-t border-line pt-4 text-sm text-slate-600"><span className="block text-xs text-slate-500">Canonical works</span><span className="mt-1 block text-xl font-semibold text-ink">{formatInteger(item.work_count)}</span></p></Link>)}</div>;
}

function StateList({ items }: { items: StateListItem[] }) {
  return <div className="overflow-x-auto"><table className="min-w-[620px] w-full text-left text-sm" aria-label="State results list"><thead className="sticky top-0 z-10 bg-slate-50"><tr className="border-b border-line text-xs uppercase tracking-wide text-slate-500"><th className="px-3 py-3 font-medium">State / UT</th><th className="px-3 py-3 text-right font-medium">Canonical works</th><th className="px-3 py-3 text-right font-medium">Action</th></tr></thead><tbody>{items.map((item) => <tr key={item.state_id} className="border-b border-line/70 last:border-0 hover:bg-blue-50/30"><td className="px-3 py-3 font-medium text-ink">{item.name}</td><td className="px-3 py-3 text-right font-medium text-ink">{formatInteger(item.work_count)}</td><td className="px-3 py-3 text-right"><Link className="button-quiet" to={`/states/${encodeURIComponent(item.state_id)}`}>View details <ArrowRight className="size-3.5" aria-hidden="true" /></Link></td></tr>)}</tbody></table></div>;
}

function DistrictsList({ filters, page, setPage }: { filters: Filters; page: number; setPage: (page: number) => void }) {
  const request = useCallback((signal: AbortSignal) => api.listDistricts({ ...filters, page, page_size: 25 }, signal), [filters, page]);
  const result = useApi(request, [request]);
  return <Panel title="District / Implementing Authority directory" description="Choose a State filter first to narrow this list. The source may label records as a District or Implementing Authority.">{result.loading && !result.data ? <LoadingBlock /> : result.error && !result.data ? <ErrorState error={result.error} onRetry={result.reload} /> : result.data ? <><div className="overflow-x-auto"><table className="min-w-[650px] w-full text-left text-sm"><thead className="sticky top-0 z-10 bg-slate-50"><tr className="border-b border-line text-xs uppercase tracking-wide text-slate-500"><th className="px-3 py-3 font-medium">District / Implementing Authority</th><th className="px-3 py-3 font-medium">State</th><th className="px-3 py-3 text-right font-medium">Works</th><th className="px-3 py-3 text-right font-medium">Action</th></tr></thead><tbody>{result.data.items.map((item: DistrictListItem) => <tr key={item.district_id} className="border-b border-line/70 last:border-0 hover:bg-blue-50/30"><td className="px-3 py-3 font-medium text-ink">{item.district_or_ida}</td><td className="px-3 py-3 text-slate-700">{item.state ?? "Not available"}</td><td className="px-3 py-3 text-right font-medium text-ink">{formatInteger(item.work_count)}</td><td className="px-3 py-3 text-right"><Link className="button-quiet" to={`/districts/${encodeURIComponent(item.district_id)}`}>View details <ArrowRight className="size-3.5" aria-hidden="true" /></Link></td></tr>)}</tbody></table></div>{!result.data.items.length && <EmptyState title="No District / IDA records match the selected filters." detail="Select a State or adjust the current filters." />}{<Pagination page={result.data.pagination} onPageChange={setPage} />}<SourceIndicator provenance={result.data.provenance} /></> : null}</Panel>;
}

function MpsDirectory({ filters, page, setPage, setSearchText, view, setView }: { filters: Filters; page: number; setPage: (page: number) => void; setSearchText: (text: string) => void; view: CollectionView; setView: (view: CollectionView) => void }) {
  const search = filters.mp ?? "";
  const directoryFilters = useMemo(() => { const { mp: _mpFilter, ...remainingFilters } = filters; return remainingFilters; }, [filters]);
  const request = useCallback((signal: AbortSignal) => api.listMps({ ...directoryFilters, search, page, page_size: 25 }, signal), [directoryFilters, page, search]);
  const result = useApi(request, [request]);
  return <Panel title="MP directory" description="Names and attributes are supplied by the active dataset." actions={<div className="flex flex-wrap items-center gap-2"><ViewToggle value={view} onChange={setView} label="MP result view" /><ListSearch value={search} onChange={setSearchText} placeholder="Search MP name" /></div>}>{result.loading && !result.data ? <LoadingBlock /> : result.error && !result.data ? <ErrorState error={result.error} onRetry={result.reload} /> : result.data ? <>{view === "grid" ? <MpsGrid items={result.data.items} /> : <MpsList items={result.data.items} />}{!result.data.items.length && <EmptyState title="No MPs match the selected filters." detail="Try adjusting the search or filters." />}{<Pagination page={result.data.pagination} onPageChange={setPage} />}<SourceIndicator provenance={result.data.provenance} /></> : null}</Panel>;
}

function StatesDirectory({ filters, page, setPage, view, setView }: { filters: Filters; page: number; setPage: (page: number) => void; view: CollectionView; setView: (view: CollectionView) => void }) {
  const request = useCallback((signal: AbortSignal) => api.listStates({ ...filters, page, page_size: 25 }, signal), [filters, page]);
  const result = useApi(request, [request]);
  return <Panel title="State / UT directory" description="State values are generated from the active canonical-work dataset." actions={<ViewToggle value={view} onChange={setView} label="State result view" />}>{result.loading && !result.data ? <LoadingBlock /> : result.error && !result.data ? <ErrorState error={result.error} onRetry={result.reload} /> : result.data ? <>{view === "grid" ? <StateGrid items={result.data.items} /> : <StateList items={result.data.items} />}{!result.data.items.length && <EmptyState title="No state records match the selected filters." detail="Try adjusting the current filters." />}{<Pagination page={result.data.pagination} onPageChange={setPage} />}<SourceIndicator provenance={result.data.provenance} /></> : null}</Panel>;
}

export default function ExplorerPage({ type }: { type: ExplorerType }) {
  const [search, setSearch] = useSearchParams();
  const filters = useMemo(() => filtersFromSearch(search), [search]);
  const page = Math.max(1, Number(search.get("page") ?? 1) || 1);
  const persistedView = getPersistedView(type, "grid");
  const viewParam = search.get("view");
  const view: CollectionView = viewParam === "list" ? "list" : viewParam === "grid" ? "grid" : persistedView;
  const update = (next: Filters, nextPage = 1, nextView = view) => {
    setPersistedView(type, nextView);
    const nextSearch = queryFromFilters(next);
    if (nextPage > 1) nextSearch.set("page", String(nextPage));
    nextSearch.set("view", nextView);
    setSearch(nextSearch);
  };
  const config = { mps: { title: "MP explorer", eyebrow: "Representative records", description: "Search, filter and open source-backed MP records from the active dataset." }, states: { title: "State explorer", eyebrow: "Geographic records", description: "Navigate active dataset results by State or Union Territory." }, districts: { title: "District / IDA explorer", eyebrow: "Geographic records", description: "Explore source values labelled as District or Implementing Authority." } }[type];
  return <div><PageHeader {...config} /><FilterBar filters={filters} onChange={(next) => update(next)} onReset={() => update({})} includeStatus={type === "mps"} /><div className="mt-6">{type === "mps" ? <MpsDirectory filters={filters} page={page} setPage={(next) => update(filters, next)} setSearchText={(text) => update({ ...filters, mp: text || undefined })} view={view} setView={(next) => update(filters, 1, next)} /> : type === "states" ? <StatesDirectory filters={filters} page={page} setPage={(next) => update(filters, next)} view={view} setView={(next) => update(filters, 1, next)} /> : <DistrictsList filters={filters} page={page} setPage={(next) => update(filters, next)} />}</div></div>;
}
