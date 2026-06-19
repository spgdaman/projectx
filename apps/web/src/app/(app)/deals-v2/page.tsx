"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { dealsApi, retailersApi, categoriesApi, subscriptionsApi } from "@/lib/api";
import { DealCard } from "@/components/DealCard";
import posthog from "posthog-js";

const ROW_PREVIEW = 10;

// ─── CategoryRow ───────────────────────────────────────────────────────────────
// Defined at module level (not inside page) so it can safely use hooks.
interface RowProps {
  category: { id: number; name: string };
  search: string;
  retailerId: number | undefined;
  ordering: string;
  onSubscribe: (deal: any) => void;
  subscribing: number | null;
}

function CategoryRow({ category, search, retailerId, ordering, onSubscribe, subscribing }: RowProps) {
  const { data, isLoading } = useQuery({
    queryKey: ["deals-v2-row", category.id, search, retailerId, ordering],
    queryFn: () =>
      dealsApi.list({
        category: category.id,
        search: search || undefined,
        retailer: retailerId,
        ordering: ordering || undefined,
        page: 1,
      }),
    select: (r) => r.data,
  });

  const allDeals = data?.results ?? [];
  const deals = allDeals.slice(0, ROW_PREVIEW);
  const totalCount: number = data?.count ?? 0;

  // Don't render once we know this category has no matching deals
  if (!isLoading && deals.length === 0) return null;

  const qs = new URLSearchParams();
  if (search) qs.set("search", search);
  if (retailerId) qs.set("retailer", String(retailerId));
  if (ordering) qs.set("ordering", ordering);
  qs.set("name", category.name);
  const viewAllHref = `/deals-v2/category/${category.id}?${qs.toString()}`;

  return (
    <section className="mb-10">
      {/* Row header */}
      <div className="flex items-center justify-between mb-3 px-0.5">
        <h2 className="text-lg font-bold text-gray-900">{category.name}</h2>
        {!isLoading && totalCount > 0 && (
          <Link
            href={viewAllHref}
            className="text-sm font-semibold text-brand-600 hover:text-brand-700 transition whitespace-nowrap"
          >
            View all {totalCount.toLocaleString()} →
          </Link>
        )}
      </div>

      {/* Horizontal scroll strip */}
      {isLoading ? (
        <div className="flex gap-4 overflow-hidden">
          {Array.from({ length: 5 }).map((_, i) => (
            <div
              key={i}
              className="flex-shrink-0 w-52 bg-white rounded-xl border border-gray-100 p-4 animate-pulse"
            >
              <div className="h-24 bg-gray-100 rounded-lg mb-3" />
              <div className="h-3 bg-gray-100 rounded w-full mb-2" />
              <div className="h-3 bg-gray-100 rounded w-2/3 mb-2" />
              <div className="h-5 bg-gray-100 rounded w-1/2" />
            </div>
          ))}
        </div>
      ) : (
        <div className="flex gap-4 overflow-x-auto pb-3 -mx-0.5 px-0.5" style={{ scrollbarWidth: "thin" }}>
          {deals.map((deal: any) => (
            <div key={deal.id} className="flex-shrink-0 w-52 relative">
              {subscribing === deal.id && (
                <div className="absolute inset-0 bg-white/70 rounded-xl flex items-center justify-center z-10">
                  <div className="w-5 h-5 border-2 border-brand-600 border-t-transparent rounded-full animate-spin" />
                </div>
              )}
              <DealCard deal={deal} onSubscribe={onSubscribe} />
            </div>
          ))}

          {/* "See more" end-cap when there are more than preview count */}
          {totalCount > ROW_PREVIEW && (
            <Link
              href={viewAllHref}
              className="flex-shrink-0 w-40 flex flex-col items-center justify-center gap-2 bg-brand-50 hover:bg-brand-100 border border-brand-100 rounded-xl text-brand-600 text-sm font-semibold transition"
            >
              <span className="text-3xl">→</span>
              <span className="text-center leading-tight px-3">
                {totalCount - ROW_PREVIEW} more deals
              </span>
            </Link>
          )}
        </div>
      )}
    </section>
  );
}

// ─── Page ─────────────────────────────────────────────────────────────────────
export default function DealsV2Page() {
  const router = useRouter();
  const [search, setSearch] = useState("");
  const [debouncedSearch, setDebouncedSearch] = useState("");
  const [retailerId, setRetailerId] = useState<number | undefined>();
  const [ordering, setOrdering] = useState("");
  const [subscribing, setSubscribing] = useState<number | null>(null);
  const [successId, setSuccessId] = useState<number | null>(null);

  function handleSearch(val: string) {
    setSearch(val);
    clearTimeout((handleSearch as any)._t);
    (handleSearch as any)._t = setTimeout(() => setDebouncedSearch(val), 350);
  }

  const { data: retailersData } = useQuery({
    queryKey: ["retailers"],
    queryFn: () => retailersApi.list(),
    select: (r) => r.data.results ?? r.data,
  });

  const { data: categoriesData, isLoading: catsLoading } = useQuery({
    queryKey: ["categories", retailerId],
    queryFn: () => categoriesApi.list(retailerId ? { retailer: retailerId } : undefined),
    select: (r) => r.data.results ?? r.data,
  });

  async function handleSubscribe(deal: any) {
    if (!deal.product?.id) { router.push("/alerts/new"); return; }
    setSubscribing(deal.id);
    try {
      await subscriptionsApi.create({ target_type: "product", product_id: deal.product.id });
      posthog.capture("deal_alert_created_from_deal_card", {
        deal_id: deal.id,
        product_id: deal.product.id,
        product_name: deal.product.name,
        retailer: deal.retailer?.name,
        current_price: deal.current_price,
        discount_pct: deal.discount_pct,
      });
      setSuccessId(deal.id);
      setTimeout(() => setSuccessId(null), 3000);
    } catch (e: any) {
      posthog.captureException(e);
      alert(e?.response?.data?.detail ?? "Could not create alert.");
    } finally {
      setSubscribing(null);
    }
  }

  const categories: any[] = categoriesData ?? [];

  return (
    <div>
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-4 mb-6">
        <div>
          <div className="flex items-center gap-3 mb-1">
            <h1 className="text-3xl font-bold text-gray-900">Today&apos;s Deals</h1>
            <span className="inline-flex items-center bg-amber-100 text-amber-700 text-xs font-bold px-2.5 py-1 rounded-full">
              ✦ New layout
            </span>
          </div>
          <p className="text-gray-500 text-sm">Browse deals by category</p>
        </div>
        <div className="flex items-center gap-3 shrink-0">
          <Link
            href="/deals"
            className="text-sm text-gray-500 hover:text-gray-700 transition"
          >
            ← Original layout
          </Link>
          <button
            onClick={() => router.push("/alerts/new")}
            className="inline-flex items-center gap-2 bg-brand-600 hover:bg-brand-700 text-white text-sm font-semibold px-4 py-2.5 rounded-lg transition"
          >
            🔔 Create Alert
          </button>
        </div>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-3 mb-8">
        <input
          type="text"
          placeholder="Search deals…"
          className="border border-gray-200 rounded-lg px-4 py-2 text-sm flex-1 min-w-48 focus:outline-none focus:ring-2 focus:ring-brand-500"
          value={search}
          onChange={(e) => handleSearch(e.target.value)}
        />
        <select
          className="border border-gray-200 rounded-lg px-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500 bg-white"
          value={retailerId ?? ""}
          onChange={(e) => setRetailerId(e.target.value ? Number(e.target.value) : undefined)}
        >
          <option value="">All retailers</option>
          {(retailersData ?? []).map((r: any) => (
            <option key={r.id} value={r.id}>{r.name}</option>
          ))}
        </select>
        <select
          className="border border-gray-200 rounded-lg px-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500 bg-white"
          value={ordering}
          onChange={(e) => setOrdering(e.target.value)}
        >
          <option value="">Best discount</option>
          <option value="newest">Newest first</option>
          <option value="price_asc">Price: low to high</option>
          <option value="price_desc">Price: high to low</option>
        </select>
      </div>

      {successId && (
        <div className="mb-6 bg-brand-50 border border-brand-200 text-brand-700 text-sm font-medium rounded-lg px-4 py-3">
          ✅ Alert created! You&apos;ll be notified when this deal improves.
        </div>
      )}

      {/* Category rows */}
      {catsLoading ? (
        // Skeleton for category rows while categories load
        Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="mb-10">
            <div className="h-5 bg-gray-100 rounded w-40 mb-4 animate-pulse" />
            <div className="flex gap-4 overflow-hidden">
              {Array.from({ length: 5 }).map((_, j) => (
                <div
                  key={j}
                  className="flex-shrink-0 w-52 bg-white rounded-xl border border-gray-100 p-4 animate-pulse"
                >
                  <div className="h-24 bg-gray-100 rounded-lg mb-3" />
                  <div className="h-3 bg-gray-100 rounded w-full mb-2" />
                  <div className="h-3 bg-gray-100 rounded w-2/3" />
                </div>
              ))}
            </div>
          </div>
        ))
      ) : categories.length === 0 ? (
        <div className="text-center py-20 text-gray-400">
          <p className="text-5xl mb-4">🏷️</p>
          <p className="text-lg font-medium">No categories found</p>
        </div>
      ) : (
        categories.map((cat: any) => (
          <CategoryRow
            key={cat.id}
            category={cat}
            search={debouncedSearch}
            retailerId={retailerId}
            ordering={ordering}
            onSubscribe={handleSubscribe}
            subscribing={subscribing}
          />
        ))
      )}
    </div>
  );
}
