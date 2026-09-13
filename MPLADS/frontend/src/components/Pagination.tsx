import { ChevronLeft, ChevronRight } from "lucide-react";
import type { Pagination as PaginationType } from "../api/types";

export function Pagination({ page, onPageChange }: { page: PaginationType; onPageChange: (page: number) => void }) {
  if (!page.total) return null;
  const first = (page.page - 1) * page.page_size + 1;
  const last = Math.min(page.page * page.page_size, page.total);
  return <nav className="flex flex-wrap items-center justify-between gap-3 border-t border-line px-5 py-3 text-sm" aria-label="Pagination">
    <span className="text-slate-600">Showing {first.toLocaleString("en-IN")}–{last.toLocaleString("en-IN")} of {page.total.toLocaleString("en-IN")}</span>
    <div className="flex items-center gap-2"><button className="button-secondary" onClick={() => onPageChange(page.page - 1)} disabled={page.page <= 1}><ChevronLeft className="size-4" aria-hidden="true" />Previous</button><button className="button-secondary" onClick={() => onPageChange(page.page + 1)} disabled={page.page >= page.total_pages}><span>Next</span><ChevronRight className="size-4" aria-hidden="true" /></button></div>
  </nav>;
}
