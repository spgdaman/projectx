"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useAuth } from "@/store/auth";
import posthog from "posthog-js";
import { PhoneInput, buildFullPhone } from "@/components/ui/PhoneInput";
import { PasswordInput } from "@/components/ui/PasswordInput";

export default function LoginPage() {
  const router = useRouter();
  const { login, isAuthenticated, isLoading } = useAuth();
  const [countryCode, setCountryCode] = useState("+254");
  const [localPhone, setLocalPhone] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!isLoading && isAuthenticated) router.replace("/deals");
  }, [isLoading, isAuthenticated, router]);

  if (isLoading || isAuthenticated) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <div className="w-10 h-10 border-4 border-brand-600 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setLoading(true);
    const fullPhone = buildFullPhone(countryCode, localPhone);
    try {
      await login(fullPhone, password);
      posthog.capture("user_logged_in", { phone: fullPhone });
      router.push("/deals");
    } catch (err: any) {
      posthog.captureException(err);
      setError(
        err?.response?.data?.detail ?? "Login failed. Check your credentials and try again."
      );
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen bg-[#FFF9F1] flex flex-col">
      {/* Top nav back to landing */}
      <header className="bg-white border-b border-gray-100">
        <div className="max-w-7xl mx-auto px-6 h-14 flex items-center justify-between">
          <Link href="/" className="flex items-center gap-2 font-bold text-brand-600 text-lg">
            <span>🏷️</span>
            <span>Bargain Hunters</span>
          </Link>
          <Link
            href="/register"
            className="text-sm font-medium text-gray-600 hover:text-brand-600 transition"
          >
            Create account →
          </Link>
        </div>
      </header>

      <div className="flex-1 flex items-center justify-center py-12 px-4">
        <div className="w-full max-w-md">
          <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-8">
            <div className="text-center mb-8">
              <span className="text-5xl">🏷️</span>
              <h1 className="text-2xl font-bold text-gray-900 mt-3">Welcome back</h1>
              <p className="text-gray-500 text-sm mt-1">Sign in to your account</p>
            </div>

            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Phone number
                </label>
                <PhoneInput
                  countryCode={countryCode}
                  localNumber={localPhone}
                  onCountryChange={setCountryCode}
                  onLocalChange={setLocalPhone}
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Password</label>
                <PasswordInput value={password} onChange={setPassword} />
              </div>

              {error && (
                <p className="text-sm text-red-600 bg-red-50 rounded-lg px-3 py-2">{error}</p>
              )}

              <button
                type="submit"
                disabled={loading}
                className="w-full bg-brand-600 hover:bg-brand-700 disabled:opacity-60 text-white font-semibold rounded-lg py-3 transition"
              >
                {loading ? "Signing in…" : "Sign In"}
              </button>

              <p className="text-center text-sm text-gray-500">
                Don&apos;t have an account?{" "}
                <Link href="/register" className="text-brand-600 font-semibold hover:underline">
                  Create one free
                </Link>
              </p>
            </form>
          </div>
        </div>
      </div>
    </div>
  );
}
