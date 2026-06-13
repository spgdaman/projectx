"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
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

const SCRAPERS = [
  { key: "naivas",     label: "Naivas" },
  { key: "chandarana", label: "Chandarana" },
  { key: "quickmart",  label: "Quickmart" },
  { key: "carrefour",  label: "Carrefour" },
  { key: "oraimo",    label: "Oraimo" },
  { key: "hotpoint",  label: "Hotpoint" },
];

const RETAILERS = SCRAPERS;

const STRATEGY_LABEL: Record<string, string> = {
  api:     "API",
  scraper: "Playwright",
};

function fmt(dt: string) {
  return new Date(dt).toLocaleString("en-KE", {
    month: "short", day: "numeric",
    hour: "2-digit", minute: "2-digit",
  });
}

export default function ScraperRunsPage() {
  const qc = useQueryClient();
  const [page, setPage]           = useState(1);
  const [retailer, setRetailer]   = useState("");
  const [status, setStatus]       = useState("");
  const [expandedId, setExpanded] = useState<number | null>(null);
  const [triggerMsg, setTriggerMsg] = useState<{ retailer: string; ok: boolean; text: string } | null>(null);

  const { data, isLoading, dataUpdatedAt } = useQuery({
    queryKey: ["admin-scraper-runs", page, retailer, status],
    queryFn: () =>
      adminApi.scraperRuns({
        page,
        retailer: retailer || undefined,
        status:   status   || undefined,
      }).then((r) => r.data),
    refetchInterval: 15_000,
  });

  const trigger = useMutation({
    mutationFn: (key: string) => adminApi.triggerScrape(key),
    onSuccess: (_data, key) => {
      const isNormalize = key === "normalize";
      const label = SCRAPERS.find(r => r.key === key)?.label ?? key;
      const text = isNormalize
        ? "Normalization queued — staging rows will be promoted to deals within minutes."
        : `${label} scraper queued — check the table below for the new run.`;
      setTriggerMsg({ retailer: label, ok: true, text });
      setTimeout(() => setTriggerMsg(null), 6000);
      setTimeout(() => qc.invalidateQueries({ queryKey: ["admin-scraper-runs"] }), 3000);
    },
    onError: (_err, key) => {
      const label = SCRAPERS.find(r => r.key === key)?.label ?? key;
      setTriggerMsg({ retailer: label, ok: false, text: `Failed to queue ${label} — is Celery running?` });
      setTimeout(() => setTriggerMsg(null), 6000);
    },
  });

  const runs: Run[] = data?.results ?? [];
  const totalPages  = data?.num_pages ?? 1;
  const lastUpdated = dataUpdatedAt ? new Date(dataUpdatedAt).toLocaleTimeString("en-KE") : "—";

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-2xl sm:text-3xl font-bold text-gray-900">Scraper Runs</h1>
        <p className="text-gray-500 text-sm mt-1">
          {data?.count ?? 0} total runs · auto-refreshes every 15 s · last updated {lastUpdated}
        </p>
      </div>

      {/* ── Trigger panel ── */}
      <div className="bg-white rounded-2xl border border-gray-100 p-4 mb-6 space-y-4">
        {/* Scraper triggers */}
        <div>
          <p className="text-xs font-bold text-gray-400 uppercase tracking-wider mb-2">
            Trigger scrape
          </p>
          <div className="flex flex-wrap gap-2">
            {SCRAPERS.map(({ key, label }) => {
              const isRunning = trigger.isPending && trigger.variables === key;
              return (
                <button
                  key={key}
                  onClick={() => trigger.mutate(key)}
                  disabled={trigger.isPending}
                  className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-semibold border transition
                    ${isRunning
                      ? "bg-brand-50 border-brand-300 text-brand-700"
                      : "bg-white border-gray-200 text-gray-700 hover:border-brand-400 hover:text-brand-700"
                    } disabled:opacity-60`}
                >
                  {isRunning
                    ? <span className="w-3.5 h-3.5 border-2 border-brand-600 border-t-transparent rounded-full animate-spin" />
                    : <span>▶</span>
                  }
                  {label}
                </button>
              );
            })}
          </div>
        </div>

        {/* Normalize trigger */}
        <div className="border-t border-gray-100 pt-3">
          <p className="text-xs font-bold text-gray-400 uppercase tracking-wider mb-2">
            Normalize staging → deals
          </p>
          <p className="text-xs text-gray-400 mb-2">
            Promotes any rows in the staging table to Products &amp; Deals. Runs automatically after each scrape — only needed manually if a scrape completed but deals aren&apos;t showing.
          </p>
          <button
            onClick={() => trigger.mutate("normalize")}
            disabled={trigger.isPending}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-semibold border transition
              ${trigger.isPending && trigger.variables === "normalize"
                ? "bg-green-50 border-green-300 text-green-700"
                : "bg-white border-gray-200 text-gray-700 hover:border-green-400 hover:text-green-700"
              } disabled:opacity-60`}
          >
            {trigger.isPending && trigger.variables === "normalize"
              ? <span className="w-3.5 h-3.5 border-2 border-green-600 border-t-transparent rounded-full animate-spin" />
              : <span>⚡</span>
            }
            Run normalization now
          </button>
        </div>

        {triggerMsg && (
          <p className={`text-sm font-medium ${triggerMsg.ok ? "text-green-700" : "text-red-600"}`}>
            {triggerMsg.ok ? "✓" : "✕"} {triggerMsg.text}
          </p>
        )}
      </div>

      {/* ── Filters ── */}
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
          <option value="running">Running</option>
          <option value="success">Success</option>
          <option value="failed">Failed</option>
          <option value="partial">Partial</option>
        </select>
      </div>

      {/* ── Table ── */}
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
                  <tr
                    key={r.id}
                    onClick={() => r.error ? setExpanded(expandedId === r.id ? null : r.id) : undefined}
                    className={`transition ${r.status === "running" ? "bg-blue-50/40" : ""} ${r.error ? "cursor-pointer hover:bg-red-50" : "hover:bg-gray-50"}`}
                  >
                    <td className="px-4 py-3 text-gray-500 whitespace-nowrap">{fmt(r.started_at)}</td>
                    <td className="px-4 py-3 font-medium text-gray-900 whitespace-nowrap">{r.retailer}</td>
                    <td className="px-4 py-3 text-gray-500 whitespace-nowrap max-w-[140px] truncate" title={r.branch ?? ""}>
                      {r.branch ?? <span className="text-gray-300">—</span>}
                    </td>
                    <td className="px-4 py-3 text-gray-500 whitespace-nowrap">
                      {STRATEGY_LABEL[r.strategy] ?? r.strategy}
                    </td>
                    <td className="px-4 py-3">
                      <span className={`text-xs font-bold px-2 py-0.5 rounded-full whitespace-nowrap ${STATUS_STYLES[r.status] ?? "bg-gray-100 text-gray-600"}`}>
                        {r.status === "running" && <span className="inline-block w-1.5 h-1.5 bg-blue-500 rounded-full mr-1 animate-pulse" />}
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
                      {r.duration_seconds != null ? `${r.duration_seconds}s` : r.status === "running" ? <span className="text-blue-500">…</span> : "—"}
                    </td>
                    {expandedId === r.id && r.error && (
                      <td colSpan={12} className="px-4 py-3 bg-red-50">
                        <p className="text-xs font-semibold text-red-700 mb-1">Error trace</p>
                        <pre className="text-xs text-red-600 whitespace-pre-wrap break-all font-mono leading-relaxed">
                          {r.error}
                        </pre>
                      </td>
                    )}
                  </tr>
                ))}
          </tbody>
        </table>
      </div>

      <Pagination page={page} totalPages={totalPages} onPageChange={setPage} className="mt-6" />
    </div>
  );
}
