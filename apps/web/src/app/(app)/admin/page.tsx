"use client";

import { useQuery } from "@tanstack/react-query";
import { adminApi } from "@/lib/api";

const STATS: { key: string; label: string; icon: string; color: string }[] = [
  { key: "total_users", label: "Total Users", icon: "👥", color: "bg-blue-50 text-blue-700" },
  { key: "paid_users", label: "Premium Users", icon: "⭐", color: "bg-yellow-50 text-yellow-700" },
  { key: "free_users", label: "Free Users", icon: "🆓", color: "bg-gray-50 text-gray-700" },
  { key: "total_products", label: "Products", icon: "📦", color: "bg-brand-50 text-brand-700" },
  { key: "total_deals", label: "Deals Tracked", icon: "🏷️", color: "bg-brand-50 text-brand-700" },
  { key: "active_subscriptions", label: "Active Alerts", icon: "🔔", color: "bg-green-50 text-green-700" },
  { key: "total_retailers", label: "Retailers", icon: "🏪", color: "bg-purple-50 text-purple-700" },
  { key: "unmapped_categories", label: "Unmapped Categories", icon: "⚠️", color: "bg-red-50 text-red-700" },
];

export default function AdminDashboard() {
  const { data: stats, isLoading } = useQuery({
    queryKey: ["admin-stats"],
    queryFn: () => adminApi.stats().then((r) => r.data),
    refetchInterval: 30_000,
  });

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-3xl font-bold text-gray-900">Dashboard</h1>
        <p className="text-gray-500 text-sm mt-1">Platform overview</p>
      </div>

      {isLoading ? (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          {Array.from({ length: 8 }).map((_, i) => (
            <div key={i} className="bg-white rounded-2xl border border-gray-100 p-5 animate-pulse h-24" />
          ))}
        </div>
      ) : (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          {STATS.map(({ key, label, icon, color }) => (
            <div
              key={key}
              className="bg-white rounded-2xl border border-gray-100 p-5 hover:shadow-sm transition"
            >
              <div className={`inline-flex items-center justify-center w-10 h-10 rounded-xl text-xl mb-3 ${color}`}>
                {icon}
              </div>
              <p className="text-2xl font-bold text-gray-900">
                {stats?.[key]?.toLocaleString() ?? "—"}
              </p>
              <p className="text-xs text-gray-500 mt-0.5">{label}</p>
            </div>
          ))}
        </div>
      )}

      {stats?.unmapped_categories > 0 && (
        <div className="mt-6 bg-amber-50 border border-amber-200 rounded-xl px-5 py-4 flex items-center justify-between">
          <div>
            <p className="text-sm font-semibold text-amber-800">
              {stats.unmapped_categories} retailer {stats.unmapped_categories === 1 ? "category" : "categories"} need mapping
            </p>
            <p className="text-xs text-amber-600 mt-0.5">
              Products in unmapped categories won't appear in filtered searches.
            </p>
          </div>
          <a
            href="/admin/categories"
            className="shrink-0 ml-4 bg-amber-600 hover:bg-amber-700 text-white text-xs font-semibold px-4 py-2 rounded-lg transition"
          >
            Fix now →
          </a>
        </div>
      )}
    </div>
  );
}
