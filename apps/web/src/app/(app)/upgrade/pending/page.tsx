"use client";

import { useEffect, useRef } from "react";
import { useRouter } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { paymentsApi } from "@/lib/api";
import posthog from "posthog-js";

export default function PaymentPendingPage() {
  const router = useRouter();
  const didNavigate = useRef(false);

  const { data } = useQuery({
    queryKey: ["paymentStatus"],
    queryFn: () => paymentsApi.status().then((r) => r.data),
    refetchInterval: 3000,
  });

  useEffect(() => {
    if (!data || didNavigate.current) return;
    if (data.status === "success") {
      didNavigate.current = true;
      posthog.capture("upgrade_payment_completed", { payment_method: "mpesa", amount_kes: 299 });
      router.push("/upgrade?success=1");
    } else if (data.status === "failed" || data.status === "expired") {
      didNavigate.current = true;
      posthog.capture("upgrade_payment_failed", { payment_method: "mpesa", failure_reason: data.status });
      router.push("/upgrade?failed=1");
    }
  }, [data, router]);

  return (
    <div className="flex flex-col items-center justify-center min-h-[60vh] gap-6">
      <div className="w-14 h-14 border-4 border-brand-600 border-t-transparent rounded-full animate-spin" />
      <h2 className="text-2xl font-bold text-gray-900">Waiting for M-Pesa…</h2>
      <p className="text-gray-500 text-center max-w-sm">
        Check your phone and enter your M-Pesa PIN. This page updates automatically.
      </p>
    </div>
  );
}
