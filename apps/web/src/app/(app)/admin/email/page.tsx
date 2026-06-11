"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { adminApi } from "@/lib/api";

interface EmailConfig {
  smtp_host: string;
  smtp_port: number;
  smtp_username: string;
  smtp_password: string;
  use_tls: boolean;
  use_ssl: boolean;
  from_email: string;
  from_name: string;
  is_active: boolean;
  updated_at?: string;
}

export default function AdminEmailPage() {
  const qc = useQueryClient();
  const [successMsg, setSuccessMsg] = useState("");
  const [errorMsg, setErrorMsg] = useState("");

  // Test email
  const [testTo, setTestTo] = useState("");
  const [testResult, setTestResult] = useState<{ ok: boolean; msg: string } | null>(null);

  const { data: config, isLoading } = useQuery<EmailConfig>({
    queryKey: ["admin-email-config"],
    queryFn: () => adminApi.getEmailConfig().then((r) => r.data),
  });

  const { data: digestStats } = useQuery({
    queryKey: ["admin-email-digest-stats"],
    queryFn: () => adminApi.emailDigestStats().then((r) => r.data),
  });

  const [form, setForm] = useState<EmailConfig | null>(null);

  // Sync form when config loads
  if (config && !form) setForm(config);

  const saveConfig = useMutation({
    mutationFn: (data: EmailConfig) => adminApi.updateEmailConfig(data),
    onSuccess: (res) => {
      qc.invalidateQueries({ queryKey: ["admin-email-config"] });
      setForm(res.data);
      setSuccessMsg("Email configuration saved.");
      setErrorMsg("");
      setTimeout(() => setSuccessMsg(""), 4000);
    },
    onError: (err: any) => {
      setErrorMsg(err?.response?.data?.detail ?? "Failed to save configuration.");
    },
  });

  const sendTest = useMutation({
    mutationFn: (to: string) => adminApi.testEmail(to),
    onSuccess: (res) => {
      setTestResult({ ok: true, msg: res.data.detail });
    },
    onError: (err: any) => {
      setTestResult({ ok: false, msg: err?.response?.data?.detail ?? "Send failed — check server logs." });
    },
  });

  function field(key: keyof EmailConfig) {
    return (e: React.ChangeEvent<HTMLInputElement>) =>
      setForm((prev) => prev ? { ...prev, [key]: e.target.type === 'checkbox' ? e.target.checked : e.target.value } : prev);
  }

  if (isLoading || !form) {
    return (
      <div className="space-y-4">
        {Array.from({ length: 6 }).map((_, i) => (
          <div key={i} className="h-12 bg-gray-100 rounded-xl animate-pulse" />
        ))}
      </div>
    );
  }

  return (
    <div className="max-w-3xl">
      <div className="mb-6">
        <h1 className="text-3xl font-bold text-gray-900">Email Settings</h1>
        <p className="text-gray-500 text-sm mt-1">
          Configure your SMTP server, set sender details, and manage deal digest subscriptions.
        </p>
      </div>

      {successMsg && (
        <div className="mb-4 bg-green-50 border border-green-200 text-green-700 text-sm font-medium rounded-lg px-4 py-3">
          ✓ {successMsg}
        </div>
      )}
      {errorMsg && (
        <div className="mb-4 bg-red-50 border border-red-200 text-red-700 text-sm font-medium rounded-lg px-4 py-3">
          ✕ {errorMsg}
        </div>
      )}

      {/* ── Digest stats ── */}
      {digestStats && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-6">
          {[
            { label: "Total users", value: digestStats.total_users },
            { label: "Opted in", value: digestStats.opted_in },
            { label: "Daily digest", value: digestStats.daily_subscribers },
            { label: "Weekly digest", value: digestStats.weekly_subscribers },
          ].map((s) => (
            <div key={s.label} className="bg-white rounded-xl border border-gray-100 p-4 text-center">
              <p className="text-2xl font-bold text-brand-600">{s.value}</p>
              <p className="text-xs text-gray-500 mt-1">{s.label}</p>
            </div>
          ))}
        </div>
      )}

      {/* ── SMTP config form ── */}
      <div className="bg-white rounded-2xl border border-gray-100 p-6 mb-6 space-y-5">
        <div className="flex items-center justify-between">
          <h2 className="text-base font-semibold text-gray-900">SMTP Configuration</h2>
          {config?.updated_at && (
            <span className="text-xs text-gray-400">
              Last updated: {new Date(config.updated_at).toLocaleString()}
            </span>
          )}
        </div>

        {/* Active toggle */}
        <label className="flex items-center gap-3 p-4 bg-gray-50 rounded-xl cursor-pointer">
          <div className="relative">
            <input
              type="checkbox"
              checked={form.is_active}
              onChange={field('is_active')}
              className="sr-only"
            />
            <div className={`w-10 h-6 rounded-full transition ${form.is_active ? 'bg-brand-600' : 'bg-gray-300'}`} />
            <div className={`absolute top-1 w-4 h-4 bg-white rounded-full shadow transition-all ${form.is_active ? 'left-5' : 'left-1'}`} />
          </div>
          <div>
            <p className="text-sm font-semibold text-gray-900">Use this SMTP configuration</p>
            <p className="text-xs text-gray-500">
              {form.is_active
                ? "Emails will use the settings below"
                : "Emails use settings.py env vars (EMAIL_HOST, EMAIL_HOST_USER, etc.)"}
            </p>
          </div>
        </label>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div className="sm:col-span-2">
            <label className="block text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1.5">
              SMTP Host
            </label>
            <input
              type="text"
              value={form.smtp_host}
              onChange={field('smtp_host')}
              placeholder="smtp.gmail.com"
              className="w-full border border-gray-200 rounded-lg px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-brand-400"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1.5">
              Port
            </label>
            <input
              type="number"
              value={form.smtp_port}
              onChange={(e) => setForm((p) => p ? { ...p, smtp_port: Number(e.target.value) } : p)}
              className="w-full border border-gray-200 rounded-lg px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-brand-400"
            />
          </div>

          <div className="flex items-end gap-4">
            <label className="flex items-center gap-2 cursor-pointer">
              <input type="checkbox" checked={form.use_tls} onChange={field('use_tls')} className="w-4 h-4 accent-brand-600" />
              <span className="text-sm font-medium text-gray-700">TLS</span>
            </label>
            <label className="flex items-center gap-2 cursor-pointer">
              <input type="checkbox" checked={form.use_ssl} onChange={field('use_ssl')} className="w-4 h-4 accent-brand-600" />
              <span className="text-sm font-medium text-gray-700">SSL</span>
            </label>
          </div>

          <div>
            <label className="block text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1.5">
              Username / Email
            </label>
            <input
              type="email"
              value={form.smtp_username}
              onChange={field('smtp_username')}
              placeholder="youremail@gmail.com"
              className="w-full border border-gray-200 rounded-lg px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-brand-400"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1.5">
              Password / App password
            </label>
            <input
              type="password"
              value={form.smtp_password}
              onChange={field('smtp_password')}
              placeholder="Leave blank to keep existing"
              className="w-full border border-gray-200 rounded-lg px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-brand-400"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1.5">
              From name
            </label>
            <input
              type="text"
              value={form.from_name}
              onChange={field('from_name')}
              placeholder="Bargain Hunters"
              className="w-full border border-gray-200 rounded-lg px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-brand-400"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1.5">
              From email
            </label>
            <input
              type="email"
              value={form.from_email}
              onChange={field('from_email')}
              placeholder="noreply@bargainhunters.co.ke"
              className="w-full border border-gray-200 rounded-lg px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-brand-400"
            />
          </div>
        </div>

        <button
          onClick={() => saveConfig.mutate(form)}
          disabled={saveConfig.isPending}
          className="bg-brand-600 hover:bg-brand-700 text-white font-semibold text-sm px-6 py-2.5 rounded-lg transition disabled:opacity-60"
        >
          {saveConfig.isPending ? "Saving…" : "Save Configuration"}
        </button>
      </div>

      {/* ── Test email ── */}
      <div className="bg-white rounded-2xl border border-gray-100 p-6 mb-6">
        <h2 className="text-base font-semibold text-gray-900 mb-4">Send Test Email</h2>
        <p className="text-sm text-gray-500 mb-4">
          Verify your SMTP settings are working by sending a test email.
          <br />
          <span className="text-xs text-gray-400">Save your configuration above before testing.</span>
        </p>
        <div className="flex gap-3">
          <input
            type="email"
            value={testTo}
            onChange={(e) => setTestTo(e.target.value)}
            placeholder="recipient@example.com"
            className="flex-1 border border-gray-200 rounded-lg px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-brand-400"
          />
          <button
            onClick={() => { setTestResult(null); sendTest.mutate(testTo); }}
            disabled={sendTest.isPending || !testTo}
            className="shrink-0 bg-gray-900 hover:bg-gray-700 text-white font-semibold text-sm px-5 py-2.5 rounded-lg transition disabled:opacity-50"
          >
            {sendTest.isPending ? "Sending…" : "Send Test"}
          </button>
        </div>
        {testResult && (
          <div className={`mt-3 text-sm font-medium px-4 py-3 rounded-lg ${
            testResult.ok
              ? "bg-green-50 border border-green-200 text-green-700"
              : "bg-red-50 border border-red-200 text-red-700"
          }`}>
            {testResult.ok ? "✓" : "✕"} {testResult.msg}
          </div>
        )}
      </div>

      {/* ── Digest info ── */}
      <div className="bg-brand-50 border border-brand-100 rounded-2xl p-6">
        <h2 className="text-base font-semibold text-brand-800 mb-2">Deal Digest Emails</h2>
        <p className="text-sm text-brand-700 mb-3">
          Users can opt in to receive automated deal digests from their account preferences.
          Digests are sent automatically via Celery Beat:
        </p>
        <ul className="space-y-1.5">
          {[
            { label: "Daily digest", desc: "Every day at 09:00 EAT — top deals from the past 24 hours" },
            { label: "Weekly digest", desc: "Every Monday at 09:00 EAT — best deals from the past 7 days" },
          ].map((item) => (
            <li key={item.label} className="flex items-start gap-2 text-sm text-brand-700">
              <span className="mt-0.5 w-1.5 h-1.5 rounded-full bg-brand-600 shrink-0 mt-1.5" />
              <div><strong>{item.label}</strong> — {item.desc}</div>
            </li>
          ))}
        </ul>
        <p className="text-xs text-brand-500 mt-3">
          Only users with an email address on their account will receive digests.
          Currently <strong>{digestStats?.with_email_address ?? 0}</strong> opted-in users have a valid email.
        </p>
      </div>
    </div>
  );
}
