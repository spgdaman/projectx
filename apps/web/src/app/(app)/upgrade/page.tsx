"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useMutation } from "@tanstack/react-query";
import { paymentsApi } from "@/lib/api";

export default function UpgradePage() {
  const router = useRouter();
  const [phone, setPhone] = useState("");
  const [error, setError] = useState("");

  const initiate = useMutation({
    mutationFn: () => paymentsApi.initiate(phone.trim()),
    onSuccess: () => router.push("/upgrade/pending"),
    onError: (e: any) => {
      setError(e?.response?.data?.detail ?? "Payment failed. Try again.");
    },
  });

  return (
    <div className="max-w-lg mx-auto">
      <h1 className="text-3xl font-bold text-gray-900 mb-2">Upgrade to Premium</h1>
      <p className="text-gray-500 mb-8">Get unlimited deal alerts and subscriptions.</p>

      <div className="bg-white rounded-2xl border border-gray-100 p-8 shadow-sm">
        <div className="flex items-end gap-1 mb-6">
          <span className="text-4xl font-extrabold text-brand-600">KES 299</span>
          <span className="text-gray-400 mb-1">/ month</span>
        </div>

        <ul className="space-y-2 mb-8">
          {[
            "Unlimited deal alert subscriptions",
            "Unlimited notifications",
            "Priority deal updates",
            "30-day subscription",
          ].map((f) => (
            <li key={f} className="flex items-center gap-2 text-sm text-gray-700">
              <span className="text-brand-500">✓</span>
              {f}
            </li>
          ))}
        </ul>

        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              M-Pesa phone number
            </label>
            <input
              type="tel"
              value={phone}
              onChange={(e) => setPhone(e.target.value)}
              placeholder="+254700000000"
              className="w-full border border-gray-200 rounded-lg px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
            />
          </div>

          {error && (
            <p className="text-sm text-red-600 bg-red-50 rounded-lg px-3 py-2">{error}</p>
          )}

          <button
            onClick={() => initiate.mutate()}
            disabled={!phone.trim() || initiate.isPending}
            className="w-full bg-brand-600 hover:bg-brand-700 disabled:opacity-50 text-white font-semibold rounded-lg py-3 transition"
          >
            {initiate.isPending ? "Sending request…" : "Pay via M-Pesa"}
          </button>
          <p className="text-xs text-gray-400 text-center">
            You'll receive a prompt on your phone. Enter your M-Pesa PIN to complete.
          </p>
        </div>
      </div>
    </div>
  );
}
