"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { adminApi } from "@/lib/api";
import { Pagination } from "@/components/Pagination";
import { useAuth } from "@/store/auth";

const PAGE_SIZE = 20;

export default function AdminUsersPage() {
  const { user: me } = useAuth();
  const qc = useQueryClient();
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const [debouncedSearch, setDebouncedSearch] = useState("");
  const [plan, setPlan] = useState("");

  function handleSearch(val: string) {
    setSearch(val);
    clearTimeout((handleSearch as any)._t);
    (handleSearch as any)._t = setTimeout(() => { setDebouncedSearch(val); setPage(1); }, 350);
  }

  const { data, isLoading } = useQuery({
    queryKey: ["admin-users", page, debouncedSearch, plan],
    queryFn: () =>
      adminApi.users({ search: debouncedSearch || undefined, plan: plan || undefined, page })
        .then((r) => r.data),
  });

  const toggleAdmin = useMutation({
    mutationFn: (id: number) => adminApi.toggleAdmin(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["admin-users"] }),
  });

  const users = data?.results ?? [];
  const totalPages = Math.ceil((data?.count ?? 0) / PAGE_SIZE);

  return (
    <div>
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-6">
        <div>
          <h1 className="text-2xl sm:text-3xl font-bold text-gray-900">Users</h1>
          <p className="text-gray-500 text-sm mt-1">{data?.count ?? 0} registered users</p>
        </div>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-3 mb-6">
        <input
          type="text"
          placeholder="Search by name or phone…"
          value={search}
          onChange={(e) => handleSearch(e.target.value)}
          className="border border-gray-200 rounded-lg px-4 py-2 text-sm flex-1 min-w-48 focus:outline-none focus:ring-2 focus:ring-brand-500"
        />
        <select
          value={plan}
          onChange={(e) => { setPlan(e.target.value); setPage(1); }}
          className="border border-gray-200 rounded-lg px-4 py-2 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-brand-500"
        >
          <option value="">All plans</option>
          <option value="paid">Premium</option>
          <option value="free">Free</option>
        </select>
      </div>

      {/* Responsive table */}
      <div className="bg-white rounded-2xl border border-gray-100 overflow-hidden overflow-x-auto">
        <table className="w-full text-sm min-w-[600px]">
          <thead>
            <tr className="border-b border-gray-100 bg-gray-50">
              <th className="text-left px-5 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wide">User</th>
              <th className="text-left px-5 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wide">Phone</th>
              <th className="text-left px-5 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wide">DOB</th>
              <th className="text-left px-5 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wide">Plan</th>
              <th className="text-left px-5 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wide">Role</th>
              <th className="text-left px-5 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wide">Joined</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-50">
            {isLoading
              ? Array.from({ length: 8 }).map((_, i) => (
                  <tr key={i}>
                    {Array.from({ length: 6 }).map((_, j) => (
                      <td key={j} className="px-5 py-3">
                        <div className="h-4 bg-gray-100 rounded animate-pulse" />
                      </td>
                    ))}
                  </tr>
                ))
              : users.length === 0
              ? (
                  <tr>
                    <td colSpan={6} className="text-center py-12 text-gray-400">No users found</td>
                  </tr>
                )
              : users.map((profile: any) => {
                  const u = profile.user;
                  const name = [u.first_name, u.last_name].filter(Boolean).join(" ") || u.username;
                  const joined = u.date_joined ? new Date(u.date_joined).toLocaleDateString() : "—";
                  const dob = profile.date_of_birth
                    ? new Date(profile.date_of_birth).toLocaleDateString() : "—";
                  const isMe = u.id === me?.id;

                  return (
                    <tr key={profile.id} className="hover:bg-gray-50 transition">
                      <td className="px-5 py-3">
                        <div className="flex items-center gap-3">
                          <div className="w-8 h-8 rounded-full bg-brand-100 text-brand-700 flex items-center justify-center text-xs font-bold shrink-0">
                            {name[0]?.toUpperCase() ?? "U"}
                          </div>
                          <div>
                            <p className="font-medium text-gray-900">{name}</p>
                            {u.email && <p className="text-xs text-gray-400">{u.email}</p>}
                          </div>
                        </div>
                      </td>
                      <td className="px-5 py-3 text-gray-600 whitespace-nowrap">{profile.phone_number}</td>
                      <td className="px-5 py-3 text-gray-500 whitespace-nowrap">{dob}</td>
                      <td className="px-5 py-3">
                        <span className={`text-xs font-bold px-2 py-0.5 rounded-full ${
                          profile.payment_status ? "bg-yellow-100 text-yellow-700" : "bg-gray-100 text-gray-600"
                        }`}>
                          {profile.payment_status ? "⭐ Premium" : "Free"}
                        </span>
                      </td>
                      <td className="px-5 py-3">
                        <div className="flex items-center gap-2">
                          <span className={`text-xs font-bold px-2 py-0.5 rounded-full ${
                            u.is_staff ? "bg-red-100 text-red-700" : "bg-gray-100 text-gray-500"
                          }`}>
                            {u.is_staff ? "Admin" : "User"}
                          </span>
                          {!isMe && (
                            <button
                              onClick={() => toggleAdmin.mutate(profile.id)}
                              disabled={toggleAdmin.isPending}
                              className="text-xs text-brand-600 hover:underline disabled:opacity-50 whitespace-nowrap"
                            >
                              {u.is_staff ? "Remove" : "Make Admin"}
                            </button>
                          )}
                        </div>
                      </td>
                      <td className="px-5 py-3 text-gray-500 whitespace-nowrap">{joined}</td>
                    </tr>
                  );
                })}
          </tbody>
        </table>
      </div>

      <Pagination page={page} totalPages={totalPages} onPageChange={setPage} className="mt-6" />
    </div>
  );
}
