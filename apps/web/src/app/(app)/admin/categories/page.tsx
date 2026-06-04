"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { adminApi, categoriesApi } from "@/lib/api";

export default function AdminCategoriesPage() {
  const qc = useQueryClient();
  const [selectedUnmapped, setSelectedUnmapped] = useState<number | null>(null);
  const [selectedMaster, setSelectedMaster] = useState<number | null>(null);
  const [tab, setTab] = useState<"unmapped" | "mapped">("unmapped");

  const { data, isLoading, refetch } = useQuery({
    queryKey: ["admin-mappings"],
    queryFn: () => adminApi.mappings().then((r) => r.data),
  });

  const { data: masterCats } = useQuery({
    queryKey: ["categories"],
    queryFn: () => categoriesApi.list().then((r) => r.data.results ?? r.data),
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
      refetch();
    },
  });

  const deleteMap = useMutation({
    mutationFn: (id: number) => adminApi.deleteMapping(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["admin-mappings"] });
      qc.invalidateQueries({ queryKey: ["admin-stats"] });
      refetch();
    },
  });

  const unmapped: any[] = data?.unmapped ?? [];
  const mapped: any[] = data?.mapped ?? [];

  const topLevel = (masterCats ?? []).filter((c: any) => !c.parent);

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-3xl font-bold text-gray-900">Category Mappings</h1>
        <p className="text-gray-500 text-sm mt-1">
          Map retailer categories to master categories so products appear in searches.
        </p>
      </div>

      {/* Tab toggle */}
      <div className="flex gap-2 mb-6">
        {(["unmapped", "mapped"] as const).map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`px-4 py-2 rounded-lg text-sm font-semibold transition ${
              tab === t
                ? "bg-brand-600 text-white"
                : "border border-gray-200 text-gray-600 hover:bg-gray-50"
            }`}
          >
            {t === "unmapped"
              ? `Unmapped (${unmapped.length})`
              : `Mapped (${mapped.length})`}
          </button>
        ))}
      </div>

      {isLoading ? (
        <div className="space-y-2">
          {Array.from({ length: 5 }).map((_, i) => (
            <div key={i} className="h-12 bg-gray-100 rounded-xl animate-pulse" />
          ))}
        </div>
      ) : tab === "unmapped" ? (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Left: pick unmapped category */}
          <div className="bg-white rounded-2xl border border-gray-100 overflow-hidden">
            <div className="px-5 py-3 bg-gray-50 border-b border-gray-100">
              <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide">
                Retailer categories to map
              </p>
            </div>
            <div className="divide-y divide-gray-50 max-h-96 overflow-y-auto">
              {unmapped.length === 0 ? (
                <p className="py-10 text-center text-gray-400 text-sm">
                  All categories are mapped! 🎉
                </p>
              ) : (
                unmapped.map((rc: any) => (
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
                ))
              )}
            </div>
          </div>

          {/* Right: pick master category */}
          <div className="bg-white rounded-2xl border border-gray-100 overflow-hidden">
            <div className="px-5 py-3 bg-gray-50 border-b border-gray-100">
              <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide">
                Map to master category
              </p>
            </div>
            <div className="divide-y divide-gray-50 max-h-96 overflow-y-auto">
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

          {/* Create button */}
          {selectedUnmapped && selectedMaster && (
            <div className="lg:col-span-2 bg-brand-50 border border-brand-200 rounded-xl px-5 py-4 flex items-center justify-between">
              <div>
                <p className="text-sm font-semibold text-brand-800">
                  {unmapped.find((r: any) => r.id === selectedUnmapped)?.name ?? "Selected"}{" "}
                  →{" "}
                  {topLevel.find((m: any) => m.id === selectedMaster)?.name ?? "Selected"}
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
      ) : (
        /* Mapped tab */
        <div className="bg-white rounded-2xl border border-gray-100 overflow-hidden">
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
          {mapped.length === 0 && (
            <p className="text-center py-10 text-gray-400 text-sm">No mappings yet</p>
          )}
        </div>
      )}
    </div>
  );
}
