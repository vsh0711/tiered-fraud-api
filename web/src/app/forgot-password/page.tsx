"use client";

import Link from "next/link";
import { FormEvent, useState } from "react";
import { api } from "@/lib/api";

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError("");
    setMessage("");
    try {
      const res = await api.forgotPassword(email);
      setMessage(res.message);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Request failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="grid-fade flex min-h-screen items-center justify-center px-4">
      <div className="panel w-full max-w-md rounded-2xl p-8 animate-rise">
        <p className="font-mono text-xs uppercase tracking-[0.22em] text-[var(--accent)]">Tiered Fraud API</p>
        <h1 className="mt-2 text-3xl font-semibold tracking-tight">Forgot password</h1>
        <p className="mt-2 text-sm text-[var(--muted)]">
          Enter the email on your account. We&apos;ll send a reset link if it matches a registered user.
        </p>
        <form onSubmit={onSubmit} className="mt-8 space-y-4">
          <label className="block text-sm">
            <span className="text-[var(--muted)]">Email</span>
            <input
              type="email"
              className="mt-1 w-full rounded-xl border bg-black/20 px-3 py-2 outline-none focus:border-teal-400/50"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
            />
          </label>
          {error ? <p className="text-sm text-rose-300">{error}</p> : null}
          {message ? <p className="text-sm text-emerald-300">{message}</p> : null}
          <button
            disabled={loading}
            className="w-full rounded-xl bg-gradient-to-r from-teal-400 to-sky-400 px-4 py-2.5 font-medium text-slate-950 disabled:opacity-60"
          >
            {loading ? "Sending…" : "Send reset link"}
          </button>
        </form>
        <p className="mt-5 text-sm text-[var(--muted)]">
          <Link href="/" className="text-teal-300 hover:underline">
            Back to sign in
          </Link>
        </p>
      </div>
    </div>
  );
}
