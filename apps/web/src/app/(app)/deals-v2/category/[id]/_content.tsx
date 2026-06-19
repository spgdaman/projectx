"use client";

import { Suspense, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useSearchParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { dealsApi, retailersApi, subscriptionsApi } from "@/lib/api";
import { DealCard } from "@/components/DealCard";
import { Pagination } from "@/components/Pagination";
import posthog from "posthog-js";

const PAGE_SIZE = 20;

function CategoryContent({ categoryId }: { categoryId: number }) {
  const router = useRouter();
  const searchParams = useSearchParams();

  const categoryName = searchParams.get("name") ?? "Category";
  const [search, setSearch] = useState(searchParams.get("search") ?? "");
  const [debouncedSearch, setDebouncedSearch] = useState(searchParams.get("search") ?? "");
  const [retailerId, setRetailerId] = useState<number | undefined>(
    searchParams.get("retailer") ? Number(searchParams.get("retailer")) : undefined
  );
  const [ordering, setOrdering] = useState(searchParams.get("ordering") ?? "");
  const [page, setPage] = useState(1);
  const [subscribing, setSubscribing] = useState<number | null>(null);
  const [successId, setSuccessId] = useState<number | null>(null);

  function handleSearch(val: string) {
    setSearch(val);
    clearTimeout((handleSearch as any)._t);
    (handleSearch as any)._t = setTimeout(() => {
      setDebouncedSearch(val);
      setPage(1);
    }, 350);
  }

  const { data: dealsData, isLoading } = useQuery({
    queryKey: ["deals-v2-cat", categoryId, debouncedSearch, retailerId, ordering, page],
    queryFn: () =>
      dealsApi.list({
        category: categoryId,
        search: debouncedSearch || undefined,
        retailer: retailerId,
        ordering: ordering || undefined,
        page,
      }),
    select: (r) => r.data,
  });

  const { data: retailersData } = useQuery({
    queryKey: ["retailers"],
    queryFn: () => retailersApi.list(),
    select: (r) => r.data.results ?? r.data,
  });

  const deals = dealsData?.results ?? [];
  const totalPages = Math.ceil((dealsData?.count ?? 0) / PAGE_SIZE);

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

  return (
    <div>
      {/* Breadcrumb */}
      <div className="flex items-center gap-2 mb-6 text-sm text-gray-500">
        <Link href="/deals-v2" className="hover:text-brand-600 transition">
          ← All categories
        </Link>
        <span>/</span>
        <span className="text-gray-800 font-medium">{categoryName}</span>
      </div>

      {/* Title */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-6">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">{categoryName}</h1>
          {dealsData?.count != null && (
            <p className="text-gray-500 text-sm mt-1">
              {dealsData.count.toLocaleString()} deals
            </p>
          )}
        </div>
        <button
          onClick={() => router.push("/alerts/new")}
          className="inline-flex items-center gap-2 bg-brand-600 hover:bg-brand-700 text-white text-sm font-semibold px-4 py-2.5 rounded-lg transition shrink-0"
        >
          🔔 Create Alert
        </button>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-3 mb-6">
        <input
          type="text"
          placeholder="Search within category…"
          className="border border-gray-200 rounded-lg px-4 py-2 text-sm flex-1 min-w-48 focus:outline-none focus:ring-2 focus:ring-brand-500"
          value={search}
          onChange={(e) => handleSearch(e.target.value)}
        />
        <select
          className="border border-gray-200 rounded-lg px-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500 bg-white"
          value={retailerId ?? ""}
          onChange={(e) => { setRetailerId(e.target.value ? Number(e.target.value) : undefined); setPage(1); }}
        >
          <option value="">All retailers</option>
          {(retailersData ?? []).map((r: any) => (
            <option key={r.id} value={r.id}>{r.name}</option>
          ))}
        </select>
        <select
          className="border border-gray-200 rounded-lg px-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500 bg-white"
          value={ordering}
          onChange={(e) => { setOrdering(e.target.value); setPage(1); }}
        >
          <option value="">Best discount</option>
          <option value="newest">Newest first</option>
          <option value="price_asc">Price: low to high</option>
          <option value="price_desc">Price: high to low</option>
        </select>
      </div>

      {successId && (
        <div className="mb-4 bg-brand-50 border border-brand-200 text-brand-700 text-sm font-medium rounded-lg px-4 py-3">
          ✅ Alert created! You&apos;ll be notified when this deal improves.
        </div>
      )}

      {/* Grid */}
      {isLoading ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
          {Array.from({ length: 8 }).map((_, i) => (
            <div key={i} className="bg-white rounded-xl border border-gray-100 p-4 animate-pulse">
              <div className="h-3 bg-gray-100 rounded w-1/3 mb-3" />
              <div className="h-4 bg-gray-100 rounded w-full mb-2" />
              <div className="h-3 bg-gray-100 rounded w-2/3 mb-4" />
              <div className="h-6 bg-gray-100 rounded w-1/2" />
            </div>
          ))}
        </div>
      ) : deals.length === 0 ? (
        <div className="text-center py-20 text-gray-400">
          <p className="text-5xl mb-4">🏷️</p>
          <p className="text-lg font-medium">No deals found</p>
          <p className="text-sm mt-1">Try adjusting your filters</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
          {deals.map((deal: any) => (
            <div key={deal.id} className="relative">
              {subscribing === deal.id && (
                <div className="absolute inset-0 bg-white/70 rounded-xl flex items-center justify-center z-10">
                  <div className="w-6 h-6 border-2 border-brand-600 border-t-transparent rounded-full animate-spin" />
                </div>
              )}
              <DealCard deal={deal} onSubscribe={handleSubscribe} />
            </div>
          ))}
        </div>
      )}

      <Pagination page={page} totalPages={totalPages} onPageChange={setPage} className="mt-8" />
    </div>
  );
}

// Exported wrapper: handles the Suspense boundary required by useSearchParams
export function CategoryPageClient({ categoryId }: { categoryId: number }) {
  return (
    <Suspense
      fallback={
        <div className="flex items-center justify-center py-20">
          <div className="w-8 h-8 border-4 border-brand-600 border-t-transparent rounded-full animate-spin" />
        </div>
      }
    >
      <CategoryContent categoryId={categoryId} />
    </Suspense>
  );
}
