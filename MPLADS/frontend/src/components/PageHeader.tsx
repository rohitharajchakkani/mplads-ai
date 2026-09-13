import type { ReactNode } from "react";
import { Link, useLocation } from "react-router-dom";
import { ChevronRight, Home } from "lucide-react";

export function PageHeader({ eyebrow, title, description, actions }: { eyebrow?: string; title: string; description: string | ReactNode; actions?: ReactNode }) {
  const location = useLocation();
  const paths = location.pathname.split("/").filter(Boolean);
  return <div className="mb-7 border-b border-line pb-7"><nav className="mb-5 flex items-center gap-1 text-xs text-slate-500" aria-label="Breadcrumb"><Link to="/" className="rounded p-1 hover:bg-blue-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue"><Home className="size-3.5" aria-label="Home" /></Link>{paths.slice(0, -1).map((path, index) => <span key={`${path}-${index}`} className="flex items-center gap-1"><ChevronRight className="size-3.5" aria-hidden="true" /><span className="capitalize">{decodeURIComponent(path).replaceAll("-", " ")}</span></span>)}{paths.length > 0 && <span className="flex items-center gap-1"><ChevronRight className="size-3.5" aria-hidden="true" /><span className="capitalize text-slate-700" aria-current="page">{title}</span></span>}</nav><div className="flex flex-wrap items-end justify-between gap-4"><div>{eyebrow && <p className="eyebrow mb-3">{eyebrow}</p>}<h1 className="section-title text-3xl font-semibold sm:text-4xl">{title}</h1><div className="mt-3 max-w-3xl text-base leading-7 text-slate-600">{description}</div></div>{actions}</div></div>;
}
