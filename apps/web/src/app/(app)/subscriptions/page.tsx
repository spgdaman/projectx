"use client";

import Link from "next/link";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { subscriptionsApi } from "@/lib/api";
import posthog from "posthog-js";

const typeIcon: Record<string, string> = { product: "📦", category: "🏷️", retailer: "🏪" };
const typeLabel: Record<string, string> = { product: "Product", category: "Category", retailer: "Retailer" };

export default function SubscriptionsPage() {
  const qc = useQueryClient();

  const { data: subs, isLoading } = useQuery({
    queryKey: ["subscriptions"],
    queryFn: () => subscriptionsApi.list().then((r) => r.data.results ?? r.data),
  });

  const toggle = useMutation({
    mutationFn: ({ id, active }: { id: number; active: boolean }) =>
      active ? subscriptionsApi.deactivate(id) : subscriptionsApi.activate(id),
    onSuccess: (_data, { id, active }) => {
      posthog.capture(active ? "alert_paused" : "alert_resumed", { subscription_id: id });
      qc.invalidateQueries({ queryKey: ["subscriptions"] });
    },
  });

  const remove = useMutation({
    mutationFn: (id: number) => subscriptionsApi.destroy(id),
    onSuccess: (_data, id) => {
      posthog.capture("alert_deleted", { subscription_id: id });
      qc.invalidateQueries({ queryKey: ["subscriptions"] });
    },
  });

  return (
    <div>
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-6">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">My Alerts</h1>
          <p className="text-gray-500 text-sm mt-1">
            Manage your deal notifications
          </p>
        </div>
        <Link
          href="/alerts/new"
          className="inline-flex items-center gap-2 bg-brand-600 hover:bg-brand-700 text-white text-sm font-semibold px-4 py-2.5 rounded-lg transition"
        >
          🔔 New Alert
        </Link>
      </div>

      {isLoading ? (
        <div className="space-y-3">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="bg-white rounded-xl border border-gray-100 p-4 animate-pulse h-20" />
          ))}
        </div>
      ) : !subs || subs.length === 0 ? (
        <div className="text-center py-20 text-gray-400">
          <p className="text-5xl mb-4">🔔</p>
          <p className="text-lg font-medium text-gray-600">No alerts yet</p>
          <p className="text-sm mt-1 mb-6">Create an alert to get notified about deals you care about</p>
          <Link
            href="/alerts/new"
            className="inline-flex items-center gap-2 bg-brand-600 hover:bg-brand-700 text-white text-sm font-semibold px-6 py-3 rounded-lg transition"
          >
            🔔 Create your first alert
          </Link>
        </div>
      ) : (
        <div className="space-y-3">
          {subs.map((sub: any) => {
            const label = sub.product?.name ?? sub.category?.name ?? sub.retailer?.name ?? "—";
            const subtitle = sub.product?.master_category?.name ?? sub.category?.parent?.name ?? null;
            const expiresAt = sub.expires_at ? new Date(sub.expires_at) : null;
            const isExpired = expiresAt ? expiresAt < new Date() : false;

            return (
              <div
                key={sub.id}
                className={`bg-white rounded-xl border border-gray-100 px-5 py-4 transition ${
                  !sub.is_active ? "opacity-60" : ""
                }`}
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="flex items-start gap-3 flex-1 min-w-0">
                    <span className="text-2xl flex-shrink-0 mt-0.5">{typeIcon[sub.target_type]}</span>
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-2 flex-wrap">
                        <p className="font-semibold text-gray-900 truncate">{label}</p>
                        <span className="text-xs bg-gray-100 text-gray-500 px-2 py-0.5 rounded-full">
                          {typeLabel[sub.target_type]}
                        </span>
                        {!sub.is_active && (
                          <span className="text-xs bg-yellow-100 text-yellow-700 px-2 py-0.5 rounded-full">
                            Paused
                          </span>
                        )}
                        {isExpired && (
                          <span className="text-xs bg-red-100 text-red-600 px-2 py-0.5 rounded-full">
                            Expired
                          </span>
                        )}
                      </div>
                      {subtitle && (
                        <p className="text-xs text-gray-400 mt-0.5">{subtitle}</p>
                      )}
                      {expiresAt && !isExpired && (
                        <p className="text-xs text-gray-400 mt-0.5">
                          Expires {expiresAt.toLocaleDateString()}
                        </p>
                      )}
                    </div>
                  </div>

                  <div className="flex items-center gap-2 flex-shrink-0">
                    <button
                      onClick={() => toggle.mutate({ id: sub.id, active: sub.is_active })}
                      disabled={toggle.isPending}
                      className={`text-xs font-semibold px-3 py-1.5 rounded-full border transition ${
                        sub.is_active
                          ? "border-gray-200 text-gray-500 hover:border-gray-400 hover:text-gray-700"
                          : "border-brand-300 text-brand-600 hover:border-brand-500 bg-brand-50"
                      }`}
                    >
                      {sub.is_active ? "Pause" : "Resume"}
                    </button>
                    <button
                      onClick={() => {
                        if (confirm("Remove this alert?")) remove.mutate(sub.id);
                      }}
                      className="text-xs text-red-400 hover:text-red-600 transition px-1"
                    >
                      Remove
                    </button>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {subs && subs.length > 0 && (
        <p className="text-center text-xs text-gray-400 mt-8">
          {subs.filter((s: any) => s.is_active).length} active of {subs.length} alerts
        </p>
      )}
    </div>
  );
}
