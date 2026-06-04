"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/store/auth";
import { AppNavbar } from "@/components/AppNavbar";

export default function AppLayout({ children }: { children: React.ReactNode }) {
  const { isLoading, isAuthenticated } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      router.replace("/login");
    }
  }, [isLoading, isAuthenticated, router]);

  if (isLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <div className="w-10 h-10 border-4 border-brand-600 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  if (!isAuthenticated) {
    return null;
  }

  return (
    <>
      <AppNavbar />
      <main className="max-w-7xl mx-auto px-3 sm:px-6 py-5 sm:py-8">{children}</main>
    </>
  );
}
