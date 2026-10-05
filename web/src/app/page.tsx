"use client";

import Link from "next/link";
import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";

export default function LoginPage() {
  const router = useRouter();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError("");
    try {
      const res = await api.login(username, password);
      localStorage.setItem("fraud_token", res.access_token);
      const key = await api.createApiKey(res.access_token, "console");
      localStorage.setItem("fraud_api_key", key.api_key);
      router.push("/dashboard");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Login failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="grid-fade flex min-h-screen items-center justify-center px-4">
      <div className="panel w-full max-w-md rounded-2xl p-8 animate-rise">
        <p className="font-mono text-xs uppercase tracking-[0.22em] text-[var(--accent)]">Tiered Fraud API</p>
        <h1 className="mt-2 text-3xl font-semibold tracking-tight">Ops Console</h1>
        <p className="mt-2 text-sm text-[var(--muted)]">
          Sign in with your account to access scoring, history, and drift tools.
        </p>
        <form onSubmit={onSubmit} className="mt-8 space-y-4">
          <label className="block text-sm">
            <span className="text-[var(--muted)]">Username or email</span>
            <input
              autoComplete="username"
              className="mt-1 w-full rounded-xl border bg-black/20 px-3 py-2 outline-none focus:border-teal-400/50"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              required
            />
          </label>
          <label className="block text-sm">
            <span className="text-[var(--muted)]">Password</span>
            <input
              type="password"
              autoComplete="current-password"
              className="mt-1 w-full rounded-xl border bg-black/20 px-3 py-2 outline-none focus:border-teal-400/50"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
          </label>
          {error ? <p className="text-sm text-rose-300">{error}</p> : null}
          <button
            disabled={loading}
            className="w-full rounded-xl bg-gradient-to-r from-teal-400 to-sky-400 px-4 py-2.5 font-medium text-slate-950 transition hover:opacity-90 disabled:opacity-60"
          >
            {loading ? "Signing in…" : "Sign in"}
          </button>
        </form>
        <div className="mt-5 flex items-center justify-between text-sm">
          <Link href="/register" className="text-teal-300 hover:underline">
            Create account
          </Link>
          <Link href="/forgot-password" className="text-[var(--muted)] hover:text-white hover:underline">
            Forgot password?
          </Link>
        </div>
      </div>
    </div>
  );
}
