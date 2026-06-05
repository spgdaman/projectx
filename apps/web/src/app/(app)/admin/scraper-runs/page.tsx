"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { adminApi } from "@/lib/api";
import { Pagination } from "@/components/Pagination";

type Run = {
  id: number;
  retailer: string;
  branch: string | null;
  strategy: string;
  status: "success" | "failed" | "partial" | "running";
  deals_found: number;
  deals_changed: number;
  products_new: number;
  products_skipped: number;
  pages_scraped: number;
  http_errors: number;
  duration_seconds: number | null;
  started_at: string;
  error: string;
};

const STATUS_STYLES: Record<string, string> = {
  success: "bg-green-100 text-green-700",
  failed:  "bg-red-100 text-red-700",
  partial: "bg-amber-100 text-amber-700",
  running: "bg-blue-100 text-blue-700",
};

const STRATEGY_LABEL: Record<string, string> = {
  api:     "API",
  scraper: "Playwright",
};

function fmt(dt: string) {
  const d = new Date(dt);
  return d.toLocaleString("en-KE", {
    month: "short", day: "numeric",
    hour: "2-digit", minute: "2-digit",
  });
}

export default function ScraperRunsPage() {
  const [page, setPage]       = useState(1);
  const [retailer, setRetailer] = useState("");
  const [status, setStatus]   = useState("");
  const [expandedId, setExpandedId] = useState<number | null>(null);

  const { data, isLoading } = useQuery({
    queryKey: ["admin-scraper-runs", page, retailer, status],
    queryFn: () =>
      adminApi.scraperRuns({
        page,
        retailer: retailer || undefined,
        status:   status   || undefined,
      }).then((r) => r.data),
    refetchInterval: 30_000,
  });

  const runs: Run[] = data?.results ?? [];
  const totalPages  = data?.num_pages ?? 1;

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-2xl sm:text-3xl font-bold text-gray-900">Scraper Runs</h1>
        <p className="text-gray-500 text-sm mt-1">
          {data?.count ?? 0} total runs · refreshes every 30 s
        </p>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-3 mb-6">
        <input
          type="text"
          placeholder="Filter by retailer…"
          value={retailer}
          onChange={(e) => { setRetailer(e.target.value); setPage(1); }}
          className="border border-gray-200 rounded-lg px-4 py-2 text-sm flex-1 min-w-40 focus:outline-none focus:ring-2 focus:ring-brand-500"
        />
        <select
          value={status}
          onChange={(e) => { setStatus(e.target.value); setPage(1); }}
          className="border border-gray-200 rounded-lg px-4 py-2 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-brand-500"
        >
          <option value="">All statuses</option>
          <option value="success">Success</option>
          <option value="failed">Failed</option>
          <option value="partial">Partial</option>
          <option value="running">Running</option>
        </select>
      </div>

      <div className="bg-white rounded-2xl border border-gray-100 overflow-hidden overflow-x-auto">
        <table className="w-full text-sm min-w-[900px]">
          <thead>
            <tr className="border-b border-gray-100 bg-gray-50">
              {["Started", "Retailer", "Branch", "Strategy", "Status", "Found", "Changed", "New", "Skipped", "Pages", "Errors", "Duration"].map((h) => (
                <th key={h} className="text-left px-4 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wide whitespace-nowrap">
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-50">
            {isLoading
              ? Array.from({ length: 10 }).map((_, i) => (
                  <tr key={i}>
                    {Array.from({ length: 12 }).map((_, j) => (
                      <td key={j} className="px-4 py-3">
                        <div className="h-3 bg-gray-100 rounded animate-pulse" />
                      </td>
                    ))}
                  </tr>
                ))
              : runs.length === 0
              ? (
                  <tr>
                    <td colSpan={12} className="text-center py-12 text-gray-400">No runs found</td>
                  </tr>
                )
              : runs.map((r) => (
                  <>
                    <tr
                      key={r.id}
                      onClick={() => setExpandedId(expandedId === r.id ? null : r.id)}
                      className={`transition cursor-pointer ${r.error ? "hover:bg-red-50" : "hover:bg-gray-50"}`}
                    >
                      <td className="px-4 py-3 text-gray-500 whitespace-nowrap">{fmt(r.started_at)}</td>
                      <td className="px-4 py-3 font-medium text-gray-900 whitespace-nowrap">{r.retailer}</td>
                      <td className="px-4 py-3 text-gray-500 whitespace-nowrap max-w-[160px] truncate" title={r.branch ?? ""}>
                        {r.branch ?? <span className="text-gray-300">—</span>}
                      </td>
                      <td className="px-4 py-3 text-gray-500 whitespace-nowrap">
                        {STRATEGY_LABEL[r.strategy] ?? r.strategy}
                      </td>
                      <td className="px-4 py-3">
                        <span className={`text-xs font-bold px-2 py-0.5 rounded-full whitespace-nowrap ${STATUS_STYLES[r.status] ?? "bg-gray-100 text-gray-600"}`}>
                          {r.status.toUpperCase()}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-right tabular-nums">{r.deals_found.toLocaleString()}</td>
                      <td className="px-4 py-3 text-right tabular-nums">{r.deals_changed.toLocaleString()}</td>
                      <td className="px-4 py-3 text-right tabular-nums text-green-700">{r.products_new.toLocaleString()}</td>
                      <td className="px-4 py-3 text-right tabular-nums text-gray-400">{r.products_skipped.toLocaleString()}</td>
                      <td className="px-4 py-3 text-right tabular-nums">{r.pages_scraped}</td>
                      <td className={`px-4 py-3 text-right tabular-nums ${r.http_errors > 0 ? "text-red-600 font-semibold" : "text-gray-400"}`}>
                        {r.http_errors}
                      </td>
                      <td className="px-4 py-3 text-right tabular-nums text-gray-500 whitespace-nowrap">
                        {r.duration_seconds != null ? `${r.duration_seconds}s` : "—"}
                      </td>
                    </tr>
                    {expandedId === r.id && r.error && (
                      <tr key={`${r.id}-err`} className="bg-red-50">
                        <td colSpan={12} className="px-4 py-3">
                          <p className="text-xs font-semibold text-red-700 mb-1">Error trace</p>
                          <pre className="text-xs text-red-600 whitespace-pre-wrap break-all font-mono leading-relaxed">
                            {r.error}
                          </pre>
                        </td>
                      </tr>
                    )}
                  </>
                ))}
          </tbody>
        </table>
      </div>

      <Pagination page={page} totalPages={totalPages} onPageChange={setPage} className="mt-6" />
    </div>
  );
}
