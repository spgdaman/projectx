"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { productsApi, categoriesApi, retailersApi, subscriptionsApi } from "@/lib/api";
import posthog from "posthog-js";

type TargetType = "product" | "category" | "retailer";

const TABS: { key: TargetType; label: string; icon: string; desc: string }[] = [
  { key: "product", label: "Product", icon: "📦", desc: "Get alerted when a specific product's price drops" },
  { key: "category", label: "Category", icon: "🏷️", desc: "Track all deals in a product category" },
  { key: "retailer", label: "Retailer", icon: "🏪", desc: "Follow deals from a specific retailer" },
];

export default function CreateAlertPage() {
  const router = useRouter();
  const qc = useQueryClient();

  const [type, setType] = useState<TargetType>("product");
  const [search, setSearch] = useState("");
  const [debouncedSearch, setDebouncedSearch] = useState("");
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [selectedName, setSelectedName] = useState("");

  function handleSearch(val: string) {
    setSearch(val);
    clearTimeout((handleSearch as any)._t);
    (handleSearch as any)._t = setTimeout(() => setDebouncedSearch(val), 350);
  }

  const productsQ = useQuery({
    queryKey: ["products", debouncedSearch],
    queryFn: () =>
      productsApi.list({ search: debouncedSearch || undefined }).then((r) => r.data?.results ?? r.data ?? []),
    enabled: type === "product",
  });

  const categoriesQ = useQuery({
    queryKey: ["categories"],
    queryFn: () => categoriesApi.list().then((r) => r.data?.results ?? r.data ?? []),
    enabled: type === "category",
  });

  const retailersQ = useQuery({
    queryKey: ["retailers"],
    queryFn: () => retailersApi.list().then((r) => r.data?.results ?? r.data ?? []),
    enabled: type === "retailer",
  });

  const raw =
    type === "product" ? productsQ.data : type === "category" ? categoriesQ.data : retailersQ.data;
  const items: any[] = Array.isArray(raw) ? raw : [];

  const isLoadingItems = productsQ.isLoading || categoriesQ.isLoading || retailersQ.isLoading;

  const filteredItems =
    type !== "product" && search
      ? items.filter((i) => i.name.toLowerCase().includes(search.toLowerCase()))
      : items;

  const createMutation = useMutation({
    mutationFn: () => {
      if (!selectedId) throw new Error("Nothing selected");
      return subscriptionsApi.create({
        target_type: type,
        product_id: type === "product" ? selectedId : undefined,
        category_id: type === "category" ? selectedId : undefined,
        retailer_id: type === "retailer" ? selectedId : undefined,
      });
    },
    onSuccess: () => {
      posthog.capture("deal_alert_created", {
        target_type: type,
        target_id: selectedId,
        target_name: selectedName,
      });
      qc.invalidateQueries({ queryKey: ["subscriptions"] });
      router.push("/subscriptions");
    },
    onError: (e: any) => {
      posthog.captureException(e);
      const data = e?.response?.data;
      const msg =
        data?.detail ??
        data?.non_field_errors?.[0] ??
        "Could not create alert.";
      alert(msg);
    },
  });

  function selectItem(id: number, name: string) {
    setSelectedId(id);
    setSelectedName(name);
  }

  return (
    <div className="max-w-2xl mx-auto">
      <button
        onClick={() => router.back()}
        className="text-sm text-gray-500 hover:text-gray-700 mb-6 inline-flex items-center gap-1"
      >
        ← Back
      </button>

      <h1 className="text-3xl font-bold text-gray-900 mb-2">Create Alert</h1>
      <p className="text-gray-500 mb-6">Choose what you want to track and we&apos;ll notify you when new deals appear.</p>

      {/* Type tabs */}
      <div className="grid grid-cols-3 gap-3 mb-6">
        {TABS.map((tab) => (
          <button
            key={tab.key}
            onClick={() => { setType(tab.key); setSelectedId(null); setSelectedName(""); setSearch(""); setDebouncedSearch(""); }}
            className={`flex flex-col items-center p-4 rounded-xl border-2 transition text-center ${
              type === tab.key
                ? "border-brand-600 bg-brand-50 text-brand-700"
                : "border-gray-200 bg-white text-gray-600 hover:border-gray-300"
            }`}
          >
            <span className="text-2xl mb-1">{tab.icon}</span>
            <span className="text-sm font-semibold">{tab.label}</span>
            <span className="text-xs mt-1 leading-tight opacity-70 hidden sm:block">{tab.desc}</span>
          </button>
        ))}
      </div>

      <div className="bg-white rounded-xl border border-gray-100 overflow-hidden">
        {/* Search */}
        <div className="px-4 py-3 border-b border-gray-100">
          <input
            type="text"
            placeholder={`Search ${type}s…`}
            value={search}
            onChange={(e) => handleSearch(e.target.value)}
            className="w-full text-sm focus:outline-none placeholder-gray-400"
          />
        </div>

        {/* List */}
        <div className="max-h-80 overflow-y-auto divide-y divide-gray-50">
          {isLoadingItems ? (
            <div className="flex justify-center py-12">
              <div className="w-8 h-8 border-4 border-brand-600 border-t-transparent rounded-full animate-spin" />
            </div>
          ) : filteredItems.length === 0 ? (
            <div className="py-12 text-center text-gray-400 text-sm">
              No {type}s found{search ? ` for "${search}"` : ""}
            </div>
          ) : (
            filteredItems.map((item: any) => (
              <button
                key={item.id}
                onClick={() => selectItem(item.id, item.name)}
                className={`w-full text-left px-4 py-3 flex items-center justify-between hover:bg-gray-50 transition ${
                  selectedId === item.id ? "bg-brand-50" : ""
                }`}
              >
                <div>
                  <p className={`text-sm font-medium ${selectedId === item.id ? "text-brand-700" : "text-gray-900"}`}>
                    {item.name}
                  </p>
                  {item.retailer && (
                    <p className="text-xs text-gray-400 mt-0.5">{item.retailer.name}</p>
                  )}
                  {item.master_category && (
                    <p className="text-xs text-gray-400 mt-0.5">{item.master_category.name}</p>
                  )}
                </div>
                {selectedId === item.id && (
                  <span className="text-brand-600 font-bold text-lg">✓</span>
                )}
              </button>
            ))
          )}
        </div>
      </div>

      {/* Selected + Create */}
      {selectedId && (
        <div className="mt-4 bg-brand-50 border border-brand-200 rounded-xl px-4 py-3 flex items-center justify-between">
          <div>
            <p className="text-xs text-brand-600 font-semibold uppercase tracking-wide">{type} selected</p>
            <p className="text-sm font-semibold text-brand-800">{selectedName}</p>
          </div>
          <button
            onClick={() => createMutation.mutate()}
            disabled={createMutation.isPending}
            className="bg-brand-600 hover:bg-brand-700 text-white text-sm font-semibold px-5 py-2.5 rounded-lg transition disabled:opacity-60"
          >
            {createMutation.isPending ? "Creating…" : "🔔 Create Alert"}
          </button>
        </div>
      )}

      {!selectedId && (
        <p className="text-center text-sm text-gray-400 mt-4">
          Select a {type} above to create your alert
        </p>
      )}
    </div>
  );
}
