import Link from 'next/link'
import { ReactNode } from 'react'

export default function LegalLayout({ children }: { children: ReactNode }) {
  return (
    <div className="min-h-screen bg-white">
      <header className="border-b border-gray-200 px-6 py-4">
        <div className="max-w-3xl mx-auto flex items-center justify-between">
          <Link
            href="/"
            className="text-brand-600 font-semibold text-base hover:text-brand-700 transition"
          >
            ← Bargain Hunters
          </Link>
        </div>
      </header>

      <main className="max-w-3xl mx-auto px-6 py-10">{children}</main>

      <footer className="border-t border-gray-200 mt-16 px-6 py-8 text-center">
        <div className="flex justify-center gap-6 text-sm text-gray-500 flex-wrap">
          <Link href="/privacy" className="hover:text-brand-600 transition">
            Privacy Policy
          </Link>
          <Link href="/terms" className="hover:text-brand-600 transition">
            Terms of Service
          </Link>
          <Link href="/cookies" className="hover:text-brand-600 transition">
            Cookie Notice
          </Link>
        </div>
        <p className="text-xs text-gray-400 mt-4">
          © {new Date().getFullYear()} Bargain Hunters Kenya. All rights reserved.
        </p>
      </footer>
    </div>
  )
}
