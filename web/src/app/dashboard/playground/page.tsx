"use client";

import { FormEvent, useState } from "react";
import { api, ScorePayload } from "@/lib/api";

const defaults: ScorePayload = {
  request_id: "ui-demo-1",
  amount: 420.5,
  merchant_category: "electronics",
  country: "US",
  device_risk_score: 0.15,
  velocity_1h: 1,
  velocity_24h: 3,
  deadline_ms: 100,
};

export default function PlaygroundPage() {
  const [form, setForm] = useState(defaults);
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError("");
    try {
      const apiKey = localStorage.getItem("fraud_api_key") || "tf_demo_key_change_me";
      const res = await api.compare({ ...form, request_id: `ui-${Date.now()}` }, apiKey);
      setResult(res);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Score failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="space-y-6">
      <header>
        <h2 className="text-2xl font-semibold tracking-tight">Score playground</h2>
        <p className="text-sm text-[var(--muted)]">Side-by-side baseline vs optimized OR cascade</p>
      </header>

      <div className="grid gap-4 lg:grid-cols-2">
        <form onSubmit={onSubmit} className="panel space-y-3 rounded-2xl p-4">
          {(
            [
              ["amount", "Amount"],
              ["merchant_category", "Merchant category"],
              ["country", "Country"],
              ["device_risk_score", "Device risk"],
              ["velocity_1h", "Velocity 1h"],
              ["velocity_24h", "Velocity 24h"],
              ["deadline_ms", "Deadline ms"],
            ] as const
          ).map(([key, label]) => (
            <label key={key} className="block text-sm">
              <span className="text-[var(--muted)]">{label}</span>
              <input
                className="mt-1 w-full rounded-xl border bg-black/20 px-3 py-2 outline-none focus:border-teal-400/50"
                value={String(form[key] ?? "")}
                onChange={(e) =>
                  setForm((prev) => ({
                    ...prev,
                    [key]:
                      key === "merchant_category" || key === "country"
                        ? e.target.value
                        : Number(e.target.value),
                  }))
                }
              />
            </label>
          ))}
          {error ? <p className="text-sm text-rose-300">{error}</p> : null}
          <button
            disabled={loading}
            className="rounded-xl bg-gradient-to-r from-teal-400 to-sky-400 px-4 py-2.5 font-medium text-slate-950 disabled:opacity-60"
          >
            {loading ? "Scoring…" : "Compare modes"}
          </button>
        </form>

        <div className="space-y-4">
          {result ? (
            <>
              <ResultCard title="Optimized" data={result.optimized} accent="teal" />
              <ResultCard title="Baseline" data={result.baseline} accent="sky" />
              <div className="panel rounded-2xl p-4 font-mono text-sm">
                Latency saved: <span className="text-teal-300">{result.latency_delta_ms} ms</span>
                {" · "}
                Early exit: <span className="text-sky-300">{String(result.early_exit_saved_tiers)}</span>
              </div>
            </>
          ) : (
            <div className="panel rounded-2xl p-8 text-sm text-[var(--muted)]">
              Run a compare to see tier paths, fraud probability, and latency.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function ResultCard({ title, data, accent }: { title: string; data: any; accent: "teal" | "sky" }) {
  const color = accent === "teal" ? "text-teal-300" : "text-sky-300";
  return (
    <div className="panel rounded-2xl p-4">
      <div className="flex items-center justify-between">
        <h3 className={`font-medium ${color}`}>{title}</h3>
        <span className="rounded-lg bg-white/5 px-2 py-1 font-mono text-xs uppercase">{data.decision}</span>
      </div>
      <p className="mt-3 font-mono text-2xl">{(data.fraud_probability * 100).toFixed(2)}%</p>
      <p className="text-sm text-[var(--muted)]">fraud probability · {data.cumulative_latency_ms} ms</p>
      <div className="mt-3 flex flex-wrap gap-2">
        {(data.tiers_executed || []).map((t: any) => (
          <span key={`${title}-${t.tier}`} className="rounded-lg border px-2 py-1 font-mono text-xs">
            {t.tier}: {t.score.toFixed(3)} ({t.latency_ms}ms)
          </span>
        ))}
      </div>
      {data.metadata?.early_exit_reason ? (
        <p className="mt-3 text-xs text-[var(--muted)]">Exit: {data.metadata.early_exit_reason}</p>
      ) : null}
    </div>
  );
}
