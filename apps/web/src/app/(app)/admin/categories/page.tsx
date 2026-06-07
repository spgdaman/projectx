"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { adminApi, categoriesApi, retailersApi } from "@/lib/api";

interface Product {
  id: number;
  name: string;
  image_url?: string | null;
  retailer: { id: number; name: string };
}

interface Category {
  id: number;
  name: string;
  parent: number | null;
  children: Category[];
}

export default function AdminCategoriesPage() {
  const qc = useQueryClient();
  const [tab, setTab] = useState<"products" | "mapped">("products");

  // Product mapping state
  const [search, setSearch] = useState("");
  const [retailerFilter, setRetailerFilter] = useState<number | "">("");
  const [page, setPage] = useState(1);
  const [selectedProduct, setSelectedProduct] = useState<Product | null>(null);
  const [expandedRoot, setExpandedRoot] = useState<number | null>(null);
  const [selectedCategory, setSelectedCategory] = useState<{ id: number; name: string } | null>(null);

  // Retailer category mapping state
  const [selectedUnmapped, setSelectedUnmapped] = useState<number | null>(null);
  const [selectedMaster, setSelectedMaster] = useState<number | null>(null);

  const { data: retailers } = useQuery({
    queryKey: ["retailers"],
    queryFn: () => retailersApi.list().then((r) => r.data.results ?? r.data),
  });

  const { data: productsData, isLoading: productsLoading } = useQuery({
    queryKey: ["admin-uncategorized", search, retailerFilter, page],
    queryFn: () =>
      adminApi
        .uncategorizedProducts({ search: search || undefined, retailer: retailerFilter || undefined, page })
        .then((r) => r.data),
    placeholderData: (prev) => prev,
  });

  const { data: categoryTree } = useQuery({
    queryKey: ["categories-tree"],
    queryFn: () => categoriesApi.tree().then((r) => r.data),
  });

  const { data: mappingsData, isLoading: mappingsLoading, refetch: refetchMappings } = useQuery({
    queryKey: ["admin-mappings"],
    queryFn: () => adminApi.mappings().then((r) => r.data),
  });

  const setCategory = useMutation({
    mutationFn: () => {
      if (!selectedProduct || !selectedCategory) throw new Error("Select both");
      return adminApi.setProductCategory(selectedProduct.id, selectedCategory.id);
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["admin-uncategorized"] });
      qc.invalidateQueries({ queryKey: ["admin-stats"] });
      setSelectedProduct(null);
      setSelectedCategory(null);
      setExpandedRoot(null);
    },
  });

  const createMap = useMutation({
    mutationFn: () => {
      if (!selectedUnmapped || !selectedMaster) throw new Error("Select both");
      return adminApi.createMapping(selectedUnmapped, selectedMaster);
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["admin-mappings"] });
      qc.invalidateQueries({ queryKey: ["admin-stats"] });
      setSelectedUnmapped(null);
      setSelectedMaster(null);
      refetchMappings();
    },
  });

  const deleteMap = useMutation({
    mutationFn: (id: number) => adminApi.deleteMapping(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["admin-mappings"] });
      qc.invalidateQueries({ queryKey: ["admin-stats"] });
    },
  });

  const products: Product[] = productsData?.results ?? [];
  const totalPages: number = productsData?.num_pages ?? 1;
  const totalProducts: number = productsData?.count ?? 0;
  const tree: Category[] = categoryTree ?? [];
  const unmapped: any[] = mappingsData?.unmapped ?? [];
  const mapped: any[] = mappingsData?.mapped ?? [];
  const topLevel = tree.filter((c) => c.parent === null);

  function handleSearchChange(val: string) {
    setSearch(val);
    setPage(1);
  }

  function handleRetailerChange(val: number | "") {
    setRetailerFilter(val);
    setPage(1);
  }

  function handleSelectProduct(p: Product) {
    setSelectedProduct(p);
    setSelectedCategory(null);
    setExpandedRoot(null);
  }

  function handleRootClick(root: Category) {
    setExpandedRoot(expandedRoot === root.id ? null : root.id);
    if (!root.children?.length) {
      setSelectedCategory({ id: root.id, name: root.name });
    }
  }

  function handleChildClick(child: Category) {
    setSelectedCategory({ id: child.id, name: child.name });
  }

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-3xl font-bold text-gray-900">Category Mappings</h1>
        <p className="text-gray-500 text-sm mt-1">
          Map uncategorized products to the correct category so they appear in searches.
        </p>
      </div>

      {/* Tabs */}
      <div className="flex gap-2 mb-6">
        <button
          onClick={() => setTab("products")}
          className={`px-4 py-2 rounded-lg text-sm font-semibold transition ${
            tab === "products"
              ? "bg-brand-600 text-white"
              : "border border-gray-200 text-gray-600 hover:bg-gray-50"
          }`}
        >
          Uncategorized Products ({totalProducts})
        </button>
        <button
          onClick={() => setTab("mapped")}
          className={`px-4 py-2 rounded-lg text-sm font-semibold transition ${
            tab === "mapped"
              ? "bg-brand-600 text-white"
              : "border border-gray-200 text-gray-600 hover:bg-gray-50"
          }`}
        >
          Retailer Mappings ({mapped.length})
        </button>
      </div>

      {/* ── Products tab ── */}
      {tab === "products" && (
        <div className="space-y-4">
          {/* Filters */}
          <div className="flex gap-3">
            <input
              type="text"
              placeholder="Search products..."
              value={search}
              onChange={(e) => handleSearchChange(e.target.value)}
              className="flex-1 border border-gray-200 rounded-lg px-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-400"
            />
            <select
              value={retailerFilter}
              onChange={(e) => handleRetailerChange(e.target.value ? Number(e.target.value) : "")}
              className="border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-400"
            >
              <option value="">All retailers</option>
              {(retailers ?? []).map((r: any) => (
                <option key={r.id} value={r.id}>{r.name}</option>
              ))}
            </select>
          </div>

          {/* Two-column layout */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Left: product list */}
            <div className="bg-white rounded-2xl border border-gray-100 overflow-hidden">
              <div className="px-5 py-3 bg-gray-50 border-b border-gray-100">
                <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide">
                  Select a product
                </p>
              </div>
              <div className="divide-y divide-gray-50 max-h-[480px] overflow-y-auto">
                {productsLoading ? (
                  Array.from({ length: 8 }).map((_, i) => (
                    <div key={i} className="h-14 px-5 py-3 flex items-center gap-3">
                      <div className="h-4 w-48 bg-gray-100 rounded animate-pulse" />
                    </div>
                  ))
                ) : products.length === 0 ? (
                  <p className="py-10 text-center text-gray-400 text-sm">
                    {search || retailerFilter ? "No products match your search" : "All products are categorized! 🎉"}
                  </p>
                ) : (
                  products.map((p) => (
                    <button
                      key={p.id}
                      onClick={() => handleSelectProduct(p)}
                      className={`w-full text-left px-5 py-3 hover:bg-gray-50 transition ${
                        selectedProduct?.id === p.id ? "bg-brand-50" : ""
                      }`}
                    >
                      <p className={`text-sm font-medium leading-snug ${
                        selectedProduct?.id === p.id ? "text-brand-700" : "text-gray-900"
                      }`}>
                        {p.name}
                      </p>
                      <p className="text-xs text-gray-400 mt-0.5">{p.retailer.name}</p>
                    </button>
                  ))
                )}
              </div>

              {/* Pagination */}
              {totalPages > 1 && (
                <div className="flex items-center justify-between px-5 py-3 border-t border-gray-100 bg-gray-50">
                  <button
                    onClick={() => setPage((p) => Math.max(1, p - 1))}
                    disabled={page === 1}
                    className="text-xs text-gray-500 hover:text-gray-800 disabled:opacity-30 transition"
                  >
                    ← Prev
                  </button>
                  <span className="text-xs text-gray-500">
                    Page {page} of {totalPages}
                  </span>
                  <button
                    onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                    disabled={page === totalPages}
                    className="text-xs text-gray-500 hover:text-gray-800 disabled:opacity-30 transition"
                  >
                    Next →
                  </button>
                </div>
              )}
            </div>

            {/* Right: category tree */}
            <div className="bg-white rounded-2xl border border-gray-100 overflow-hidden">
              <div className="px-5 py-3 bg-gray-50 border-b border-gray-100">
                <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide">
                  {selectedProduct ? `Assign category for: ${selectedProduct.name}` : "Select a product first"}
                </p>
              </div>
              <div className="max-h-[480px] overflow-y-auto">
                {!selectedProduct ? (
                  <p className="py-10 text-center text-gray-300 text-sm">
                    ← Pick a product to see categories
                  </p>
                ) : (
                  <ul className="divide-y divide-gray-50">
                    {topLevel.map((root) => {
                      const isExpanded = expandedRoot === root.id;
                      const hasChildren = root.children?.length > 0;
                      const isRootSelected = selectedCategory?.id === root.id;

                      return (
                        <li key={root.id}>
                          <button
                            onClick={() => handleRootClick(root)}
                            className={`w-full text-left px-5 py-3 hover:bg-gray-50 transition flex items-center justify-between ${
                              isRootSelected && !isExpanded ? "bg-brand-50" : ""
                            }`}
                          >
                            <span className={`text-sm font-semibold ${
                              isRootSelected && !isExpanded ? "text-brand-700" : "text-gray-900"
                            }`}>
                              {root.name}
                            </span>
                            {hasChildren && (
                              <span className="text-gray-400 text-xs ml-2">
                                {isExpanded ? "▲" : "▼"}
                              </span>
                            )}
                          </button>

                          {isExpanded && hasChildren && (
                            <ul className="border-t border-gray-50 bg-gray-50/50">
                              {root.children.map((child) => {
                                const isSelected = selectedCategory?.id === child.id;
                                return (
                                  <li key={child.id}>
                                    <button
                                      onClick={() => handleChildClick(child)}
                                      className={`w-full text-left pl-10 pr-5 py-2.5 hover:bg-brand-50 transition ${
                                        isSelected ? "bg-brand-50" : ""
                                      }`}
                                    >
                                      <span className={`text-sm ${
                                        isSelected ? "text-brand-700 font-semibold" : "text-gray-700"
                                      }`}>
                                        {child.name}
                                      </span>
                                    </button>
                                  </li>
                                );
                              })}
                            </ul>
                          )}
                        </li>
                      );
                    })}
                  </ul>
                )}
              </div>
            </div>
          </div>

          {/* Confirmation bar */}
          {selectedProduct && selectedCategory && (
            <div className="bg-brand-50 border border-brand-200 rounded-xl px-5 py-4 flex items-center justify-between">
              <div>
                <p className="text-sm font-semibold text-brand-800">
                  {selectedProduct.name} → {selectedCategory.name}
                </p>
                <p className="text-xs text-brand-600 mt-0.5">Save this category assignment</p>
              </div>
              <button
                onClick={() => setCategory.mutate()}
                disabled={setCategory.isPending}
                className="shrink-0 ml-4 bg-brand-600 hover:bg-brand-700 text-white text-sm font-semibold px-5 py-2.5 rounded-lg transition disabled:opacity-60"
              >
                {setCategory.isPending ? "Saving…" : "Save Mapping"}
              </button>
            </div>
          )}
        </div>
      )}

      {/* ── Retailer mappings tab ── */}
      {tab === "mapped" && (
        <div className="space-y-6">
          {/* Unmapped retailer categories */}
          {unmapped.length > 0 && (
            <div>
              <h2 className="text-sm font-semibold text-gray-700 mb-3">
                Unmapped retailer categories ({unmapped.length})
              </h2>
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                <div className="bg-white rounded-2xl border border-gray-100 overflow-hidden">
                  <div className="px-5 py-3 bg-gray-50 border-b border-gray-100">
                    <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide">
                      Retailer category
                    </p>
                  </div>
                  <div className="divide-y divide-gray-50 max-h-72 overflow-y-auto">
                    {unmapped.map((rc: any) => (
                      <button
                        key={rc.id}
                        onClick={() => setSelectedUnmapped(rc.id)}
                        className={`w-full text-left px-5 py-3 hover:bg-gray-50 transition ${
                          selectedUnmapped === rc.id ? "bg-brand-50" : ""
                        }`}
                      >
                        <p className={`text-sm font-medium ${selectedUnmapped === rc.id ? "text-brand-700" : "text-gray-900"}`}>
                          {rc.name}
                        </p>
                        <p className="text-xs text-gray-400 mt-0.5">{rc.retailer}</p>
                      </button>
                    ))}
                  </div>
                </div>

                <div className="bg-white rounded-2xl border border-gray-100 overflow-hidden">
                  <div className="px-5 py-3 bg-gray-50 border-b border-gray-100">
                    <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide">
                      Map to master category
                    </p>
                  </div>
                  <div className="divide-y divide-gray-50 max-h-72 overflow-y-auto">
                    {topLevel.map((mc: any) => (
                      <button
                        key={mc.id}
                        onClick={() => setSelectedMaster(mc.id)}
                        className={`w-full text-left px-5 py-3 hover:bg-gray-50 transition ${
                          selectedMaster === mc.id ? "bg-brand-50" : ""
                        }`}
                      >
                        <p className={`text-sm font-medium ${selectedMaster === mc.id ? "text-brand-700" : "text-gray-900"}`}>
                          {mc.name}
                        </p>
                      </button>
                    ))}
                  </div>
                </div>

                {selectedUnmapped && selectedMaster && (
                  <div className="lg:col-span-2 bg-brand-50 border border-brand-200 rounded-xl px-5 py-4 flex items-center justify-between">
                    <div>
                      <p className="text-sm font-semibold text-brand-800">
                        {unmapped.find((r: any) => r.id === selectedUnmapped)?.name} → {topLevel.find((m: any) => m.id === selectedMaster)?.name}
                      </p>
                      <p className="text-xs text-brand-600 mt-0.5">Click to create this mapping</p>
                    </div>
                    <button
                      onClick={() => createMap.mutate()}
                      disabled={createMap.isPending}
                      className="shrink-0 ml-4 bg-brand-600 hover:bg-brand-700 text-white text-sm font-semibold px-5 py-2.5 rounded-lg transition disabled:opacity-60"
                    >
                      {createMap.isPending ? "Saving…" : "Create Mapping"}
                    </button>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Existing mappings table */}
          <div>
            <h2 className="text-sm font-semibold text-gray-700 mb-3">
              Existing retailer mappings ({mapped.length})
            </h2>
            <div className="bg-white rounded-2xl border border-gray-100 overflow-hidden">
              {mappingsLoading ? (
                <div className="p-6 space-y-2">
                  {Array.from({ length: 5 }).map((_, i) => (
                    <div key={i} className="h-10 bg-gray-100 rounded animate-pulse" />
                  ))}
                </div>
              ) : (
                <table className="w-full text-sm">
                  <thead>
                    <tr className="bg-gray-50 border-b border-gray-100">
                      <th className="text-left px-5 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wide">Retailer</th>
                      <th className="text-left px-5 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wide">Retailer Category</th>
                      <th className="text-left px-5 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wide">Master Category</th>
                      <th className="px-5 py-3" />
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-50">
                    {mapped.map((m: any) => (
                      <tr key={m.id} className="hover:bg-gray-50 transition">
                        <td className="px-5 py-3 text-gray-500 text-xs">{m.retailer}</td>
                        <td className="px-5 py-3 font-medium text-gray-900">{m.retailer_category}</td>
                        <td className="px-5 py-3">
                          <span className="inline-block bg-brand-50 text-brand-700 text-xs font-semibold px-2.5 py-1 rounded-full">
                            {m.master_category}
                          </span>
                        </td>
                        <td className="px-5 py-3 text-right">
                          <button
                            onClick={() => {
                              if (confirm(`Remove mapping for "${m.retailer_category}"?`)) {
                                deleteMap.mutate(m.id);
                              }
                            }}
                            className="text-xs text-red-400 hover:text-red-600 transition"
                          >
                            Remove
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
              {!mappingsLoading && mapped.length === 0 && (
                <p className="text-center py-10 text-gray-400 text-sm">No mappings yet</p>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
