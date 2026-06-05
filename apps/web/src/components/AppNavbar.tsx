"use client";

import { useState, useEffect, useRef } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useAuth } from "@/store/auth";

const NAV_LINKS = [
  { href: "/deals", label: "Deals", icon: "🏷️" },
  { href: "/shopping-list", label: "Shopping List", icon: "🛒" },
  { href: "/alerts/new", label: "Create Alert", icon: "🔔" },
  { href: "/subscriptions", label: "My Alerts", icon: "📋" },
  { href: "/upgrade", label: "Upgrade", icon: "⭐" },
];

export function AppNavbar() {
  const path = usePathname();
  const router = useRouter();
  const { logout, user } = useAuth();
  const [open, setOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  // Close on outside click
  useEffect(() => {
    function handler(e: MouseEvent) {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  // Close on route change
  useEffect(() => { setOpen(false); }, [path]);

  function handleLogout() {
    logout();
    router.push("/");
  }

  const isActive = (href: string) =>
    path === href || (href !== "/deals" && path.startsWith(href));

  const linkCls = (href: string) =>
    `block px-4 py-2.5 rounded-lg text-sm font-medium transition ${
      isActive(href) ? "bg-brand-50 text-brand-700" : "text-gray-600 hover:bg-gray-50"
    }`;

  const displayName = user?.first_name || "Profile";

  return (
    <nav className="bg-white border-b border-gray-100 sticky top-0 z-50" ref={menuRef}>
      <div className="max-w-7xl mx-auto px-4 h-14 flex items-center justify-between gap-3">
        {/* Logo */}
        <Link href="/" className="flex items-center gap-2 font-bold text-brand-600 text-lg shrink-0">
          <span>🏷️</span>
          <span>Bargain Hunters</span>
        </Link>

        {/* Desktop nav */}
        <div className="hidden md:flex items-center gap-1 flex-1 justify-center">
          {NAV_LINKS.map(({ href, label }) => (
            <Link key={href} href={href} className={`px-3 py-1.5 rounded-lg text-sm font-medium transition whitespace-nowrap ${
              isActive(href) ? "bg-brand-50 text-brand-700" : "text-gray-600 hover:bg-gray-50"
            }`}>
              {label}
            </Link>
          ))}
        </div>

        {/* Desktop right-side actions */}
        <div className="hidden md:flex items-center gap-1 shrink-0">
          {user?.is_staff && (
            <Link href="/admin" className={`px-3 py-1.5 rounded-lg text-sm font-medium transition ${
              path.startsWith("/admin") ? "bg-brand-50 text-brand-700" : "text-gray-600 hover:bg-gray-50"
            }`}>
              ⚙️ Admin
            </Link>
          )}
          <Link href="/profile" className={`px-3 py-1.5 rounded-lg text-sm font-medium transition ${
            path === "/profile" ? "bg-brand-50 text-brand-700" : "text-gray-600 hover:bg-gray-50"
          }`}>
            {displayName}
          </Link>
          <button
            onClick={handleLogout}
            className="px-3 py-1.5 rounded-lg text-sm font-medium text-gray-600 hover:bg-gray-50 transition"
          >
            Sign Out
          </button>
        </div>

        {/* Mobile: profile initial + hamburger */}
        <div className="flex md:hidden items-center gap-2">
          <Link href="/profile" className="w-8 h-8 rounded-full bg-brand-600 text-white flex items-center justify-center text-sm font-bold">
            {(user?.first_name?.[0] ?? user?.username?.[0] ?? "U").toUpperCase()}
          </Link>
          <button
            onClick={() => setOpen((o) => !o)}
            aria-label="Toggle menu"
            className="p-2 rounded-lg text-gray-600 hover:bg-gray-100 transition"
          >
            {open ? (
              <svg className="w-5 h-5" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
              </svg>
            ) : (
              <svg className="w-5 h-5" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" d="M4 6h16M4 12h16M4 18h16" />
              </svg>
            )}
          </button>
        </div>
      </div>

      {/* Mobile dropdown menu */}
      {open && (
        <div className="md:hidden bg-white border-t border-gray-100 px-4 py-3 space-y-1 shadow-lg">
          {NAV_LINKS.map(({ href, label, icon }) => (
            <Link key={href} href={href} className={linkCls(href)}>
              <span className="mr-2">{icon}</span>{label}
            </Link>
          ))}

          <div className="border-t border-gray-100 my-2 pt-2 space-y-1">
            {user?.is_staff && (
              <Link href="/admin" className={linkCls("/admin")}>
                <span className="mr-2">⚙️</span>Admin Panel
              </Link>
            )}
            <Link href="/profile" className={linkCls("/profile")}>
              <span className="mr-2">👤</span>{displayName}
            </Link>
            <button
              onClick={handleLogout}
              className="w-full text-left px-4 py-2.5 rounded-lg text-sm font-medium text-red-500 hover:bg-red-50 transition"
            >
              <span className="mr-2">🚪</span>Sign Out
            </button>
          </div>
        </div>
      )}
    </nav>
  );
}
