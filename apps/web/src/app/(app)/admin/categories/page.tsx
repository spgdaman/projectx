"use client";

import { useState, useEffect } from "react";
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

// Extract a keyword suggestion from product names.
// Strips weights/volumes, noise words, punctuation then takes first 2-3 words.
const NOISE = /\b(the|a|an|with|and|or|for|of|to|in|on|at|w\/|c\/w|easy|open|pack|pcs|pieces|assorted|super|extra|new|free|value|offer)\b/gi;
const WEIGHTS = /\b\d+\s*(?:g|kg|ml|l|cl|oz|lb|pcs|pc|x)\b/gi;

function suggestKeyword(names: string[]): string {
  const cleaned = names.map((n) =>
    n.toLowerCase()
      .replace(WEIGHTS, " ")
      .replace(NOISE, " ")
      .replace(/[^a-z\s]/g, " ")
      .replace(/\s+/g, " ")
      .trim()
      .split(" ")
      .filter((w) => w.length > 2)
  );
  if (cleaned.length === 0) return "";
  if (cleaned.length === 1) return cleaned[0].slice(0, 3).join(" ");
  // For multiple products find words common to all
  const common = cleaned[0].filter((w) => cleaned.every((ws) => ws.includes(w)));
  return (common.length > 0 ? common : cleaned[0]).slice(0, 2).join(" ");
}

export default function AdminCategoriesPage() {
  const qc = useQueryClient();
  const [tab, setTab] = useState<"products" | "mapped">("products");

  // Product list state
  const [search, setSearch] = useState("");
  const [retailerFilter, setRetailerFilter] = useState<number | "">("");
  const [page, setPage] = useState(1);

  // Multi-select state
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set());

  // Category picker state
  const [expandedRoot, setExpandedRoot] = useState<number | null>(null);
  const [selectedCategory, setSelectedCategory] = useState<{ id: number; name: string } | null>(null);

  // Keyword rule state
  const [createRule, setCreateRule] = useState(false);
  const [keyword, setKeyword] = useState("");

  // Retailer mapping state
  const [selectedUnmapped, setSelectedUnmapped] = useState<number | null>(null);
  const [selectedMaster, setSelectedMaster] = useState<number | null>(null);

  // Feedback
  const [successMsg, setSuccessMsg] = useState("");

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

  const products: Product[] = productsData?.results ?? [];
  const totalPages: number = productsData?.num_pages ?? 1;
  const totalProducts: number = productsData?.count ?? 0;
  const tree: Category[] = categoryTree ?? [];
  const unmapped: any[] = mappingsData?.unmapped ?? [];
  const mapped: any[] = mappingsData?.mapped ?? [];
  const topLevel = tree.filter((c) => c.parent === null);

  // Auto-suggest keyword when selection or category changes
  useEffect(() => {
    if (!createRule) return;
    const names = products.filter((p) => selectedIds.has(p.id)).map((p) => p.name);
    if (names.length > 0) setKeyword(suggestKeyword(names));
  }, [selectedIds, createRule]);

  // Reset selection when page/filters change
  useEffect(() => {
    setSelectedIds(new Set());
  }, [search, retailerFilter, page]);

  const bulkSave = useMutation({
    mutationFn: () => {
      if (selectedIds.size === 0 || !selectedCategory) throw new Error("Select products and category");
      return adminApi.bulkSetProductCategory(
        Array.from(selectedIds),
        selectedCategory.id,
        createRule ? keyword : undefined,
      );
    },
    onSuccess: (res) => {
      const { updated, keyword_rule_created, keyword: kw } = res.data;
      let msg = `${updated} product${updated !== 1 ? "s" : ""} mapped to ${selectedCategory?.name}.`;
      if (keyword_rule_created) msg += ` Keyword rule "${kw}" created.`;
      setSuccessMsg(msg);
      setTimeout(() => setSuccessMsg(""), 5000);
      qc.invalidateQueries({ queryKey: ["admin-uncategorized"] });
      qc.invalidateQueries({ queryKey: ["admin-stats"] });
      setSelectedIds(new Set());
      setSelectedCategory(null);
      setExpandedRoot(null);
      setCreateRule(false);
      setKeyword("");
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

  const pageIds = products.map((p) => p.id);
  const allPageSelected = pageIds.length > 0 && pageIds.every((id) => selectedIds.has(id));

  function toggleAll() {
    if (allPageSelected) {
      setSelectedIds((prev) => {
        const next = new Set(prev);
        pageIds.forEach((id) => next.delete(id));
        return next;
      });
    } else {
      setSelectedIds((prev) => new Set([...prev, ...pageIds]));
    }
  }

  function toggleOne(id: number) {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });
  }

  function handleRootClick(root: Category) {
    setExpandedRoot(expandedRoot === root.id ? null : root.id);
    if (!root.children?.length) setSelectedCategory({ id: root.id, name: root.name });
  }

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-3xl font-bold text-gray-900">Category Mappings</h1>
        <p className="text-gray-500 text-sm mt-1">
          Select products, pick a sub-category, optionally create a keyword rule for future auto-mapping.
        </p>
      </div>

      {successMsg && (
        <div className="mb-4 bg-green-50 border border-green-200 text-green-700 text-sm font-medium rounded-lg px-4 py-3">
          ✓ {successMsg}
        </div>
      )}

      {/* Tabs */}
      <div className="flex gap-2 mb-6">
        <button
          onClick={() => setTab("products")}
          className={`px-4 py-2 rounded-lg text-sm font-semibold transition ${
            tab === "products" ? "bg-brand-600 text-white" : "border border-gray-200 text-gray-600 hover:bg-gray-50"
          }`}
        >
          Uncategorized Products ({totalProducts})
        </button>
        <button
          onClick={() => setTab("mapped")}
          className={`px-4 py-2 rounded-lg text-sm font-semibold transition ${
            tab === "mapped" ? "bg-brand-600 text-white" : "border border-gray-200 text-gray-600 hover:bg-gray-50"
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
              onChange={(e) => { setSearch(e.target.value); setPage(1); }}
              className="flex-1 border border-gray-200 rounded-lg px-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-400"
            />
            <select
              value={retailerFilter}
              onChange={(e) => { setRetailerFilter(e.target.value ? Number(e.target.value) : ""); setPage(1); }}
              className="border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-400"
            >
              <option value="">All retailers</option>
              {(retailers ?? []).map((r: any) => (
                <option key={r.id} value={r.id}>{r.name}</option>
              ))}
            </select>
          </div>

          {/* Selection summary pill */}
          {selectedIds.size > 0 && (
            <div className="flex items-center gap-3">
              <span className="text-sm font-semibold text-brand-700 bg-brand-50 border border-brand-200 px-3 py-1 rounded-full">
                {selectedIds.size} product{selectedIds.size !== 1 ? "s" : ""} selected
              </span>
              <button
                onClick={() => setSelectedIds(new Set())}
                className="text-xs text-gray-400 hover:text-gray-700 transition"
              >
                Clear selection
              </button>
            </div>
          )}

          {/* Two-column layout */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Left: product list with checkboxes */}
            <div className="bg-white rounded-2xl border border-gray-100 overflow-hidden">
              {/* Header with select-all */}
              <div className="px-5 py-3 bg-gray-50 border-b border-gray-100 flex items-center gap-3">
                <input
                  type="checkbox"
                  checked={allPageSelected}
                  onChange={toggleAll}
                  className="w-4 h-4 accent-brand-600 cursor-pointer"
                />
                <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide">
                  {allPageSelected ? "Deselect page" : "Select all on page"}
                </p>
              </div>

              <div className="divide-y divide-gray-50 max-h-[480px] overflow-y-auto">
                {productsLoading ? (
                  Array.from({ length: 8 }).map((_, i) => (
                    <div key={i} className="h-14 px-5 py-3 flex items-center gap-3">
                      <div className="w-4 h-4 bg-gray-100 rounded animate-pulse" />
                      <div className="h-4 flex-1 bg-gray-100 rounded animate-pulse" />
                    </div>
                  ))
                ) : products.length === 0 ? (
                  <p className="py-10 text-center text-gray-400 text-sm">
                    {search || retailerFilter ? "No products match your search" : "All products are categorized! 🎉"}
                  </p>
                ) : (
                  products.map((p) => {
                    const checked = selectedIds.has(p.id);
                    return (
                      <label
                        key={p.id}
                        className={`flex items-center gap-3 px-5 py-3 cursor-pointer hover:bg-gray-50 transition ${
                          checked ? "bg-brand-50" : ""
                        }`}
                      >
                        <input
                          type="checkbox"
                          checked={checked}
                          onChange={() => toggleOne(p.id)}
                          className="w-4 h-4 accent-brand-600 shrink-0 cursor-pointer"
                        />
                        <div className="min-w-0">
                          <p className={`text-sm font-medium leading-snug truncate ${
                            checked ? "text-brand-700" : "text-gray-900"
                          }`}>
                            {p.name}
                          </p>
                          <p className="text-xs text-gray-400 mt-0.5">{p.retailer.name}</p>
                        </div>
                      </label>
                    );
                  })
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
                  <span className="text-xs text-gray-500">Page {page} of {totalPages}</span>
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
                  {selectedIds.size > 0
                    ? `Assign category to ${selectedIds.size} product${selectedIds.size !== 1 ? "s" : ""}`
                    : "Select products first"}
                </p>
              </div>
              <div className="max-h-[480px] overflow-y-auto">
                {selectedIds.size === 0 ? (
                  <p className="py-10 text-center text-gray-300 text-sm">
                    ← Check products to see categories
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
                              <span className="text-gray-400 text-xs ml-2">{isExpanded ? "▲" : "▼"}</span>
                            )}
                          </button>

                          {isExpanded && hasChildren && (
                            <ul className="border-t border-gray-50 bg-gray-50/50">
                              {root.children.map((child) => {
                                const isSelected = selectedCategory?.id === child.id;
                                return (
                                  <li key={child.id}>
                                    <button
                                      onClick={() => setSelectedCategory({ id: child.id, name: child.name })}
                                      className={`w-full text-left pl-10 pr-5 py-2.5 hover:bg-brand-50 transition ${
                                        isSelected ? "bg-brand-50" : ""
                                      }`}
                                    >
                                      <span className={`text-sm ${isSelected ? "text-brand-700 font-semibold" : "text-gray-700"}`}>
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
          {selectedIds.size > 0 && selectedCategory && (
            <div className="bg-brand-50 border border-brand-200 rounded-xl px-5 py-4 space-y-3">
              <div className="flex items-center justify-between gap-4">
                <p className="text-sm font-semibold text-brand-800">
                  {selectedIds.size} product{selectedIds.size !== 1 ? "s" : ""} → {selectedCategory.name}
                </p>
                <button
                  onClick={() => bulkSave.mutate()}
                  disabled={bulkSave.isPending}
                  className="shrink-0 bg-brand-600 hover:bg-brand-700 text-white text-sm font-semibold px-5 py-2.5 rounded-lg transition disabled:opacity-60"
                >
                  {bulkSave.isPending ? "Saving…" : "Save Mapping"}
                </button>
              </div>

              {/* Keyword rule row */}
              <div className="flex items-center gap-3 pt-1 border-t border-brand-200">
                <label className="flex items-center gap-2 cursor-pointer select-none">
                  <input
                    type="checkbox"
                    checked={createRule}
                    onChange={(e) => {
                      setCreateRule(e.target.checked);
                      if (e.target.checked) {
                        const names = products.filter((p) => selectedIds.has(p.id)).map((p) => p.name);
                        setKeyword(suggestKeyword(names));
                      }
                    }}
                    className="w-4 h-4 accent-brand-600"
                  />
                  <span className="text-xs font-semibold text-brand-700">Create keyword rule</span>
                </label>
                {createRule && (
                  <input
                    type="text"
                    value={keyword}
                    onChange={(e) => setKeyword(e.target.value)}
                    placeholder="e.g. ritter sport"
                    className="flex-1 border border-brand-300 bg-white rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-brand-400"
                  />
                )}
                {createRule && (
                  <span className="text-xs text-brand-600 shrink-0">
                    Future products matching this keyword → {selectedCategory.name}
                  </span>
                )}
              </div>
            </div>
          )}
        </div>
      )}

      {/* ── Retailer mappings tab ── */}
      {tab === "mapped" && (
        <div className="space-y-6">
          {unmapped.length > 0 && (
            <div>
              <h2 className="text-sm font-semibold text-gray-700 mb-3">
                Unmapped retailer categories ({unmapped.length})
              </h2>
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                <div className="bg-white rounded-2xl border border-gray-100 overflow-hidden">
                  <div className="px-5 py-3 bg-gray-50 border-b border-gray-100">
                    <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide">Retailer category</p>
                  </div>
                  <div className="divide-y divide-gray-50 max-h-72 overflow-y-auto">
                    {unmapped.map((rc: any) => (
                      <button
                        key={rc.id}
                        onClick={() => setSelectedUnmapped(rc.id)}
                        className={`w-full text-left px-5 py-3 hover:bg-gray-50 transition ${selectedUnmapped === rc.id ? "bg-brand-50" : ""}`}
                      >
                        <p className={`text-sm font-medium ${selectedUnmapped === rc.id ? "text-brand-700" : "text-gray-900"}`}>{rc.name}</p>
                        <p className="text-xs text-gray-400 mt-0.5">{rc.retailer}</p>
                      </button>
                    ))}
                  </div>
                </div>

                <div className="bg-white rounded-2xl border border-gray-100 overflow-hidden">
                  <div className="px-5 py-3 bg-gray-50 border-b border-gray-100">
                    <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide">Map to master category</p>
                  </div>
                  <div className="divide-y divide-gray-50 max-h-72 overflow-y-auto">
                    {topLevel.map((mc: any) => (
                      <button
                        key={mc.id}
                        onClick={() => setSelectedMaster(mc.id)}
                        className={`w-full text-left px-5 py-3 hover:bg-gray-50 transition ${selectedMaster === mc.id ? "bg-brand-50" : ""}`}
                      >
                        <p className={`text-sm font-medium ${selectedMaster === mc.id ? "text-brand-700" : "text-gray-900"}`}>{mc.name}</p>
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

          <div>
            <h2 className="text-sm font-semibold text-gray-700 mb-3">Existing retailer mappings ({mapped.length})</h2>
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
                            onClick={() => { if (confirm(`Remove mapping for "${m.retailer_category}"?`)) deleteMap.mutate(m.id); }}
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
