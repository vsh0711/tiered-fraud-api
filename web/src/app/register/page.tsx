"use client";

import Link from "next/link";
import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";

export default function RegisterPage() {
  const router = useRouter();
  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError("");
    try {
      await api.register(username, email, password);
      router.push("/?registered=1");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Registration failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="grid-fade flex min-h-screen items-center justify-center px-4">
      <div className="panel w-full max-w-md rounded-2xl p-8 animate-rise">
        <p className="font-mono text-xs uppercase tracking-[0.22em] text-[var(--accent)]">Tiered Fraud API</p>
        <h1 className="mt-2 text-3xl font-semibold tracking-tight">Create account</h1>
        <p className="mt-2 text-sm text-[var(--muted)]">
          Register with your email. You can reset your password later via that address.
        </p>
        <form onSubmit={onSubmit} className="mt-8 space-y-4">
          <label className="block text-sm">
            <span className="text-[var(--muted)]">Username</span>
            <input
              className="mt-1 w-full rounded-xl border bg-black/20 px-3 py-2 outline-none focus:border-teal-400/50"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              minLength={3}
              required
            />
          </label>
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
          <label className="block text-sm">
            <span className="text-[var(--muted)]">Password</span>
            <input
              type="password"
              className="mt-1 w-full rounded-xl border bg-black/20 px-3 py-2 outline-none focus:border-teal-400/50"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              minLength={8}
              required
            />
          </label>
          {error ? <p className="text-sm text-rose-300">{error}</p> : null}
          <button
            disabled={loading}
            className="w-full rounded-xl bg-gradient-to-r from-teal-400 to-sky-400 px-4 py-2.5 font-medium text-slate-950 disabled:opacity-60"
          >
            {loading ? "Creating…" : "Create account"}
          </button>
        </form>
        <p className="mt-5 text-sm text-[var(--muted)]">
          Already have an account?{" "}
          <Link href="/" className="text-teal-300 hover:underline">
            Sign in
          </Link>
        </p>
      </div>
    </div>
  );
}
