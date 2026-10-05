"use client";

import Link from "next/link";
import { FormEvent, Suspense, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { api } from "@/lib/api";

function ResetForm() {
  const router = useRouter();
  const params = useSearchParams();
  const token = params.get("token") || "";
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    if (!token) {
      setError("Missing reset token. Use the link from your email.");
      return;
    }
    if (password !== confirm) {
      setError("Passwords do not match");
      return;
    }
    setLoading(true);
    setError("");
    try {
      await api.resetPassword(token, password);
      router.push("/?reset=1");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Reset failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="panel w-full max-w-md rounded-2xl p-8 animate-rise">
      <p className="font-mono text-xs uppercase tracking-[0.22em] text-[var(--accent)]">Tiered Fraud API</p>
      <h1 className="mt-2 text-3xl font-semibold tracking-tight">Set new password</h1>
      <p className="mt-2 text-sm text-[var(--muted)]">Choose a new password for your account.</p>
      <form onSubmit={onSubmit} className="mt-8 space-y-4">
        <label className="block text-sm">
          <span className="text-[var(--muted)]">New password</span>
          <input
            type="password"
            className="mt-1 w-full rounded-xl border bg-black/20 px-3 py-2 outline-none focus:border-teal-400/50"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            minLength={8}
            required
          />
        </label>
        <label className="block text-sm">
          <span className="text-[var(--muted)]">Confirm password</span>
          <input
            type="password"
            className="mt-1 w-full rounded-xl border bg-black/20 px-3 py-2 outline-none focus:border-teal-400/50"
            value={confirm}
            onChange={(e) => setConfirm(e.target.value)}
            minLength={8}
            required
          />
        </label>
        {error ? <p className="text-sm text-rose-300">{error}</p> : null}
        <button
          disabled={loading}
          className="w-full rounded-xl bg-gradient-to-r from-teal-400 to-sky-400 px-4 py-2.5 font-medium text-slate-950 disabled:opacity-60"
        >
          {loading ? "Updating…" : "Update password"}
        </button>
      </form>
      <p className="mt-5 text-sm text-[var(--muted)]">
        <Link href="/" className="text-teal-300 hover:underline">
          Back to sign in
        </Link>
      </p>
    </div>
  );
}

export default function ResetPasswordPage() {
  return (
    <div className="grid-fade flex min-h-screen items-center justify-center px-4">
      <Suspense fallback={<div className="text-[var(--muted)]">Loading…</div>}>
        <ResetForm />
      </Suspense>
    </div>
  );
}
