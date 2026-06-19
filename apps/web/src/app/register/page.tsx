"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useAuth } from "@/store/auth";
import posthog from "posthog-js";
import { PhoneInput, buildFullPhone } from "@/components/ui/PhoneInput";
import { PasswordInput } from "@/components/ui/PasswordInput";

export default function RegisterPage() {
  const router = useRouter();
  const { register, isAuthenticated, isLoading } = useAuth();

  const [countryCode, setCountryCode] = useState("+254");
  const [phone, setPhone] = useState(""); // local number only
  const [email, setEmail] = useState("");
  const [dob, setDob] = useState("");
  const [firstName, setFirstName] = useState("");
  const [lastName, setLastName] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [consentGiven, setConsentGiven] = useState(false);
  const [consentError, setConsentError] = useState(false);
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
    if (!consentGiven) {
      setConsentError(true);
      return;
    }
    if (password !== confirm) { setError("Passwords do not match."); return; }
    if (password.length < 6) { setError("Password must be at least 6 characters."); return; }
    setLoading(true);
    const fullPhone = buildFullPhone(countryCode, phone);
    try {
      await register(fullPhone, password, email.trim(), dob, firstName.trim(), lastName.trim());
      posthog.identify(fullPhone, {
        email: email.trim() || undefined,
        first_name: firstName.trim() || undefined,
        last_name: lastName.trim() || undefined,
      });
      posthog.capture("user_signed_up", {
        phone: fullPhone,
        has_email: !!email.trim(),
        has_name: !!(firstName.trim() || lastName.trim()),
      });
      router.push("/deals");
    } catch (err: any) {
      const data = err?.response?.data;
      posthog.captureException(err);
      if (!err?.response) {
        setError("Cannot reach the server. Make sure the Django API is running on port 8000.");
      } else if (typeof data?.phone === "object") {
        setError(Array.isArray(data.phone) ? data.phone[0] : String(data.phone));
      } else if (typeof data?.email === "object") {
        setError(Array.isArray(data.email) ? data.email[0] : String(data.email));
      } else if (typeof data?.date_of_birth === "object") {
        setError(Array.isArray(data.date_of_birth) ? data.date_of_birth[0] : String(data.date_of_birth));
      } else if (typeof data?.detail === "string") {
        setError(data.detail);
      } else if (typeof data === "object" && data !== null) {
        const firstKey = Object.keys(data)[0];
        const msg = firstKey ? data[firstKey] : null;
        setError(Array.isArray(msg) ? msg[0] : String(msg ?? "Registration failed."));
      } else {
        setError("Registration failed. Please try again.");
      }
    } finally {
      setLoading(false);
    }
  }

  const field = (
    label: string,
    type: string,
    value: string,
    onChange: (v: string) => void,
    opts?: { placeholder?: string; required?: boolean; min?: string; max?: string }
  ) => (
    <div>
      <label className="block text-sm font-medium text-gray-700 mb-1">
        {label} {opts?.required !== false && <span className="text-red-500">*</span>}
      </label>
      <input
        type={type}
        required={opts?.required !== false}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={opts?.placeholder}
        min={opts?.min}
        max={opts?.max}
        className="w-full border border-gray-200 rounded-lg px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
      />
    </div>
  );

  return (
    <div className="min-h-screen bg-[#FFF9F1] flex flex-col">
      <header className="bg-white border-b border-gray-100">
        <div className="max-w-7xl mx-auto px-6 h-14 flex items-center justify-between">
          <Link href="/" className="flex items-center gap-2 font-bold text-brand-600 text-lg">
            <span>🏷️</span><span>Bargain Hunters</span>
          </Link>
          <Link href="/login" className="text-sm font-medium text-gray-600 hover:text-brand-600 transition">
            Sign in →
          </Link>
        </div>
      </header>

      <div className="flex-1 flex items-center justify-center py-10 px-4">
        <div className="w-full max-w-lg">
          <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-8">
            <div className="text-center mb-7">
              <span className="text-4xl">🏷️</span>
              <h1 className="text-2xl font-bold text-gray-900 mt-3">Create your account</h1>
              <p className="text-gray-500 text-sm mt-1">Start tracking deals for free</p>
            </div>

            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="grid grid-cols-2 gap-3">
                {field("First name", "text", firstName, setFirstName, { placeholder: "Jane", required: false })}
                {field("Last name", "text", lastName, setLastName, { placeholder: "Doe", required: false })}
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Phone number <span className="text-red-500">*</span>
                </label>
                <PhoneInput
                  countryCode={countryCode}
                  localNumber={phone}
                  onCountryChange={setCountryCode}
                  onLocalChange={setPhone}
                />
              </div>
              {field("Email address", "email", email, setEmail, { placeholder: "jane@example.com" })}
              {field("Date of birth", "date", dob, setDob, {
                max: new Date(new Date().setFullYear(new Date().getFullYear() - 13))
                  .toISOString().split("T")[0],
              })}

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Password <span className="text-red-500">*</span>
                </label>
                <PasswordInput value={password} onChange={setPassword} placeholder="At least 6 characters" />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Confirm password <span className="text-red-500">*</span>
                </label>
                <PasswordInput value={confirm} onChange={setConfirm} placeholder="Re-enter password" />
              </div>

              <label className="flex items-start gap-3 text-sm text-gray-600 cursor-pointer">
                <input
                  type="checkbox"
                  checked={consentGiven}
                  onChange={(e) => {
                    setConsentGiven(e.target.checked);
                    if (e.target.checked) setConsentError(false);
                  }}
                  className="mt-0.5 h-4 w-4 rounded border-gray-300 text-brand-600 focus:ring-brand-500"
                />
                <span>
                  I have read and agree to the{" "}
                  <a
                    href="/privacy"
                    className="text-brand-600 underline hover:text-brand-700"
                    target="_blank"
                    rel="noopener noreferrer"
                  >
                    Privacy Policy
                  </a>
                  {" "}and{" "}
                  <a
                    href="/terms"
                    className="text-brand-600 underline hover:text-brand-700"
                    target="_blank"
                    rel="noopener noreferrer"
                  >
                    Terms of Service
                  </a>
                </span>
              </label>
              {consentError && (
                <p className="text-sm text-red-600 -mt-2">
                  Please accept the Privacy Policy and Terms of Service to continue.
                </p>
              )}

              {error && (
                <p className="text-sm text-red-600 bg-red-50 rounded-lg px-3 py-2">{error}</p>
              )}

              <button
                type="submit"
                disabled={loading}
                className="w-full bg-brand-600 hover:bg-brand-700 disabled:opacity-60 text-white font-semibold rounded-lg py-3 transition"
              >
                {loading ? "Creating account…" : "Create Account"}
              </button>

              <p className="text-center text-sm text-gray-500">
                Already have an account?{" "}
                <Link href="/login" className="text-brand-600 font-semibold hover:underline">
                  Sign in
                </Link>
              </p>
            </form>
          </div>
        </div>
      </div>
    </div>
  );
}
