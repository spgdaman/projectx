"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import { useAuth } from "@/store/auth";
import { authApi, subscriptionsApi } from "@/lib/api";

export default function ProfilePage() {
  const { user, logout, refreshUser } = useAuth();
  const router = useRouter();
  const [showLogoutConfirm, setShowLogoutConfirm] = useState(false);

  // Edit state
  const [editing, setEditing] = useState(false);
  const [email, setEmail] = useState("");
  const [dob, setDob] = useState("");
  const [saveMsg, setSaveMsg] = useState<{ ok: boolean; text: string } | null>(null);

  const { data: subs } = useQuery({
    queryKey: ["subscriptions"],
    queryFn: () => subscriptionsApi.list().then((r) => r.data.results ?? r.data),
  });

  const updateMe = useMutation({
    mutationFn: (data: { email?: string; date_of_birth?: string }) =>
      authApi.updateMe(data),
    onSuccess: async () => {
      await refreshUser();
      setSaveMsg({ ok: true, text: "Profile updated." });
      setEditing(false);
      setTimeout(() => setSaveMsg(null), 4000);
    },
    onError: (err: any) => {
      const msg = err?.response?.data?.detail ?? err?.response?.data?.email?.[0] ?? "Failed to save.";
      setSaveMsg({ ok: false, text: msg });
    },
  });

  if (!user) return null;

  const displayName =
    [user.first_name, user.last_name].filter(Boolean).join(" ") || user.username;
  const initials =
    ((user.first_name?.[0] ?? "") + (user.last_name?.[0] ?? "")).toUpperCase() ||
    user.username?.[0]?.toUpperCase() ||
    "U";

  const activeSubs = (subs ?? []).filter((s: any) => s.is_active).length;
  const totalSubs = (subs ?? []).length;

  const dobFormatted = user.date_of_birth
    ? new Date(user.date_of_birth).toLocaleDateString(undefined, {
        year: "numeric", month: "long", day: "numeric",
      })
    : null;

  function startEditing() {
    setEmail(user!.email ?? "");
    setDob(user!.date_of_birth ?? "");
    setSaveMsg(null);
    setEditing(true);
  }

  function handleSave() {
    const payload: { email?: string; date_of_birth?: string } = {};
    if (email !== (user!.email ?? "")) payload.email = email;
    if (dob !== (user!.date_of_birth ?? "")) payload.date_of_birth = dob;
    if (Object.keys(payload).length === 0) {
      setEditing(false);
      return;
    }
    updateMe.mutate(payload);
  }

  function handleLogout() {
    logout();
    router.push("/");
  }

  const Row = ({ label, value }: { label: string; value: string }) => (
    <div className="flex justify-between py-3 border-b border-gray-50 last:border-0">
      <span className="text-sm text-gray-500">{label}</span>
      <span className="text-sm font-medium text-gray-900 text-right max-w-[60%] break-words">{value}</span>
    </div>
  );

  return (
    <div className="max-w-2xl mx-auto space-y-5 pb-10">
      <h1 className="text-2xl sm:text-3xl font-bold text-gray-900">My Profile</h1>

      {saveMsg && (
        <div className={`text-sm font-medium px-4 py-3 rounded-lg ${
          saveMsg.ok
            ? "bg-green-50 border border-green-200 text-green-700"
            : "bg-red-50 border border-red-200 text-red-700"
        }`}>
          {saveMsg.ok ? "✓" : "✕"} {saveMsg.text}
        </div>
      )}

      {/* Identity card */}
      <div className="bg-white rounded-2xl border border-gray-100 p-5 sm:p-6 flex flex-col sm:flex-row sm:items-center gap-4">
        <div className="w-16 h-16 rounded-full bg-brand-600 text-white flex items-center justify-center text-2xl font-bold shrink-0">
          {initials}
        </div>
        <div className="flex-1 min-w-0">
          <p className="text-xl font-bold text-gray-900 truncate">{displayName}</p>
          <p className="text-gray-500 text-sm mt-0.5">{user.phone_number}</p>
          {user.email && <p className="text-gray-400 text-xs mt-0.5">{user.email}</p>}
        </div>
        <div className="flex flex-wrap gap-2 shrink-0">
          {user.is_staff && (
            <span className="text-xs font-bold bg-red-100 text-red-700 px-3 py-1 rounded-full">
              Admin
            </span>
          )}
          <span className={`text-xs font-bold px-3 py-1 rounded-full ${
            user.payment_status
              ? "bg-yellow-100 text-yellow-700"
              : "bg-gray-100 text-gray-600"
          }`}>
            {user.payment_status ? "⭐ Premium" : "Free"}
          </span>
        </div>
      </div>

      {/* Plan card */}
      <div className="bg-white rounded-2xl border border-gray-100 p-5 sm:p-6">
        <h2 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-4">Subscription</h2>
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div>
            <p className="text-lg font-bold text-gray-900">
              {user.payment_status ? "⭐ Premium" : "Free Plan"}
            </p>
            <p className="text-sm text-gray-500 mt-0.5">
              {user.payment_status
                ? "Unlimited deal alerts and subscriptions"
                : `Up to 3 active alerts · ${activeSubs} used`}
            </p>
          </div>
          {!user.payment_status && (
            <Link
              href="/upgrade"
              className="self-start sm:self-auto shrink-0 bg-brand-600 hover:bg-brand-700 text-white text-sm font-semibold px-5 py-2.5 rounded-lg transition"
            >
              Upgrade
            </Link>
          )}
        </div>
      </div>

      {/* Alerts summary */}
      <div className="bg-white rounded-2xl border border-gray-100 p-5 sm:p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xs font-semibold text-gray-500 uppercase tracking-wide">My Alerts</h2>
          <Link href="/subscriptions" className="text-sm text-brand-600 hover:underline font-medium">
            Manage →
          </Link>
        </div>
        <div className="grid grid-cols-2 gap-4">
          <div className="bg-brand-50 rounded-xl p-4 text-center">
            <p className="text-3xl font-bold text-brand-600">{activeSubs}</p>
            <p className="text-xs text-gray-500 mt-1">Active alerts</p>
          </div>
          <div className="bg-gray-50 rounded-xl p-4 text-center">
            <p className="text-3xl font-bold text-gray-700">{totalSubs}</p>
            <p className="text-xs text-gray-500 mt-1">Total created</p>
          </div>
        </div>
      </div>

      {/* Account details + edit */}
      <div className="bg-white rounded-2xl border border-gray-100 p-5 sm:p-6">
        <div className="flex items-center justify-between mb-2">
          <h2 className="text-xs font-semibold text-gray-500 uppercase tracking-wide">Account Details</h2>
          {!editing && (
            <button
              onClick={startEditing}
              className="text-sm text-brand-600 hover:underline font-medium"
            >
              Edit
            </button>
          )}
        </div>

        {editing ? (
          <div className="space-y-4 pt-2">
            <div>
              <label className="block text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1.5">
                Email address
              </label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@example.com"
                className="w-full border border-gray-200 rounded-lg px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-brand-400"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1.5">
                Date of birth
              </label>
              <input
                type="date"
                value={dob}
                onChange={(e) => setDob(e.target.value)}
                className="w-full border border-gray-200 rounded-lg px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-brand-400"
              />
            </div>

            <div className="flex gap-3 pt-1">
              <button
                onClick={handleSave}
                disabled={updateMe.isPending}
                className="flex-1 bg-brand-600 hover:bg-brand-700 text-white font-semibold text-sm py-2.5 rounded-lg transition disabled:opacity-60"
              >
                {updateMe.isPending ? "Saving…" : "Save changes"}
              </button>
              <button
                onClick={() => { setEditing(false); setSaveMsg(null); }}
                className="flex-1 border border-gray-200 text-gray-600 hover:bg-gray-50 font-semibold text-sm py-2.5 rounded-lg transition"
              >
                Cancel
              </button>
            </div>
          </div>
        ) : (
          <>
            <Row label="Full name" value={displayName} />
            <Row label="Phone" value={user.phone_number} />
            <Row label="Email" value={user.email || "—"} />
            <Row label="Date of birth" value={dobFormatted ?? "—"} />
            <Row label="Username" value={user.username} />
            <Row label="Plan" value={user.payment_status ? "Premium" : "Free"} />
          </>
        )}
      </div>

      {/* Logout */}
      <div className="bg-white rounded-2xl border border-gray-100 p-5 sm:p-6">
        <h2 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-4">Account Actions</h2>
        {!showLogoutConfirm ? (
          <button
            onClick={() => setShowLogoutConfirm(true)}
            className="w-full border border-red-200 text-red-600 hover:bg-red-50 font-semibold rounded-xl py-3 transition text-sm"
          >
            Sign Out
          </button>
        ) : (
          <div className="flex gap-3">
            <button
              onClick={handleLogout}
              className="flex-1 bg-red-600 hover:bg-red-700 text-white font-semibold rounded-xl py-3 transition text-sm"
            >
              Yes, sign out
            </button>
            <button
              onClick={() => setShowLogoutConfirm(false)}
              className="flex-1 border border-gray-200 text-gray-600 hover:bg-gray-50 font-semibold rounded-xl py-3 transition text-sm"
            >
              Cancel
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
