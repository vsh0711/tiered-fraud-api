"use client";

import { useEffect, useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { api } from "@/lib/api";

export default function DriftPage() {
  const [snapshots, setSnapshots] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function refresh() {
    const token = localStorage.getItem("fraud_token") || "";
    const rows = await api.driftSnapshots(token);
    setSnapshots(rows);
  }

  useEffect(() => {
    refresh().catch((e) => setError(e.message));
  }, []);

  async function run() {
    setLoading(true);
    setError("");
    try {
      const token = localStorage.getItem("fraud_token") || "";
      await api.runDrift(token, 0.4);
      await refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Drift run failed");
    } finally {
      setLoading(false);
    }
  }

  const latest = snapshots[0];
  const chartData = Object.entries(latest?.psi_by_feature || {}).map(([feature, psi]) => ({
    feature,
    psi: Number(psi),
  }));

  return (
    <div className="space-y-6">
      <header className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h2 className="text-2xl font-semibold tracking-tight">Drift monitor</h2>
          <p className="text-sm text-[var(--muted)]">Population Stability Index across key features</p>
        </div>
        <button
          onClick={run}
          disabled={loading}
          className="rounded-xl bg-gradient-to-r from-teal-400 to-sky-400 px-4 py-2.5 font-medium text-slate-950 disabled:opacity-60"
        >
          {loading ? "Scanning…" : "Run drift scan"}
        </button>
      </header>

      {error ? <p className="text-rose-300">{error}</p> : null}

      {latest ? (
        <section className="grid gap-4 lg:grid-cols-2">
          <div className="panel rounded-2xl p-4">
            <p className="text-xs uppercase tracking-wider text-[var(--muted)]">Latest summary</p>
            <p className="mt-2 text-lg">{latest.summary}</p>
            <p className={`mt-3 font-mono text-sm ${latest.alert ? "text-rose-300" : "text-emerald-300"}`}>
              {latest.alert ? "ALERT" : "STABLE"} · strength {latest.drift_strength}
            </p>
          </div>
          <div className="panel rounded-2xl p-4">
            <h3 className="mb-4 text-sm text-[var(--muted)]">PSI by feature</h3>
            <div className="h-56">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={chartData}>
                  <CartesianGrid stroke="rgba(120,160,200,0.12)" vertical={false} />
                  <XAxis dataKey="feature" stroke="#8aa0b8" />
                  <YAxis stroke="#8aa0b8" />
                  <Tooltip contentStyle={{ background: "#0d1b2e", border: "1px solid #334155" }} />
                  <Bar dataKey="psi" fill="#fb7185" radius={[8, 8, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
        </section>
      ) : (
        <div className="panel rounded-2xl p-8 text-sm text-[var(--muted)]">No snapshots yet. Run a scan.</div>
      )}

      <div className="panel overflow-x-auto rounded-2xl">
        <table className="min-w-full text-left text-sm">
          <thead className="text-xs uppercase tracking-wider text-[var(--muted)]">
            <tr>
              <th className="px-4 py-3">Time</th>
              <th className="px-4 py-3">Strength</th>
              <th className="px-4 py-3">Samples</th>
              <th className="px-4 py-3">Alert</th>
              <th className="px-4 py-3">Summary</th>
            </tr>
          </thead>
          <tbody>
            {snapshots.map((s) => (
              <tr key={s.id} className="border-t border-white/5">
                <td className="px-4 py-3 font-mono text-xs">{new Date(s.created_at).toLocaleString()}</td>
                <td className="px-4 py-3">{s.drift_strength}</td>
                <td className="px-4 py-3">{s.sample_size}</td>
                <td className="px-4 py-3">{s.alert ? "yes" : "no"}</td>
                <td className="px-4 py-3 text-[var(--muted)]">{s.summary}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
