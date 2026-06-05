"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useAuth } from "@/store/auth";
import { useEffect } from "react";

const NAV = [
  { href: "/admin", label: "📊 Dashboard", exact: true },
  { href: "/admin/users", label: "👥 Users" },
  { href: "/admin/categories", label: "🏷️ Category Mappings" },
  { href: "/admin/scraper-runs", label: "🤖 Scraper Runs" },
];

export default function AdminLayout({ children }: { children: React.ReactNode }) {
  const { user, isLoading } = useAuth();
  const router = useRouter();
  const path = usePathname();

  useEffect(() => {
    if (!isLoading && !user?.is_staff) router.replace("/deals");
  }, [isLoading, user, router]);

  if (isLoading || !user?.is_staff) {
    return (
      <div className="flex min-h-[60vh] items-center justify-center">
        <div className="w-10 h-10 border-4 border-brand-600 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  return (
    <div className="flex flex-col md:flex-row gap-4 md:gap-6 min-h-[calc(100vh-3.5rem)]">
      {/* Sidebar — horizontal tab strip on mobile, vertical panel on desktop */}
      <aside className="md:w-52 md:shrink-0">
        <div className="bg-white rounded-2xl border border-gray-100 p-2 md:p-3 md:sticky md:top-20">
          <p className="hidden md:block text-xs font-bold text-gray-400 uppercase tracking-wider px-3 mb-2">
            Admin
          </p>
          <nav className="flex md:flex-col overflow-x-auto gap-1 md:gap-0 md:space-y-0.5 scrollbar-none">
            {NAV.map(({ href, label, exact }) => {
              const active = exact ? path === href : path.startsWith(href);
              return (
                <Link
                  key={href}
                  href={href}
                  className={`flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium transition whitespace-nowrap shrink-0 ${
                    active
                      ? "bg-brand-50 text-brand-700"
                      : "text-gray-600 hover:bg-gray-50"
                  }`}
                >
                  {label}
                </Link>
              );
            })}
          </nav>
        </div>
      </aside>

      {/* Main content */}
      <div className="flex-1 min-w-0 py-1">{children}</div>
    </div>
  );
}
