"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";

export default function HistoryPage() {
  const [items, setItems] = useState<any[]>([]);
  const [total, setTotal] = useState(0);
  const [decision, setDecision] = useState("");
  const [mode, setMode] = useState("");
  const [error, setError] = useState("");

  async function load() {
    try {
      const token = localStorage.getItem("fraud_token") || "";
      const qs = new URLSearchParams();
      qs.set("limit", "40");
      if (decision) qs.set("decision", decision);
      if (mode) qs.set("routing_mode", mode);
      const res = await api.history(token, `?${qs.toString()}`);
      setItems(res.items || []);
      setTotal(res.total || 0);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load");
    }
  }

  useEffect(() => {
    load();
  }, [decision, mode]);

  return (
    <div className="space-y-6">
      <header className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h2 className="text-2xl font-semibold tracking-tight">Decision history</h2>
          <p className="text-sm text-[var(--muted)]">{total} persisted events</p>
        </div>
        <div className="flex gap-2">
          <select
            className="rounded-xl border bg-black/20 px-3 py-2 text-sm"
            value={decision}
            onChange={(e) => setDecision(e.target.value)}
          >
            <option value="">All decisions</option>
            <option value="approve">approve</option>
            <option value="review">review</option>
            <option value="decline">decline</option>
          </select>
          <select
            className="rounded-xl border bg-black/20 px-3 py-2 text-sm"
            value={mode}
            onChange={(e) => setMode(e.target.value)}
          >
            <option value="">All modes</option>
            <option value="optimized">optimized</option>
            <option value="baseline">baseline</option>
          </select>
        </div>
      </header>

      {error ? <p className="text-rose-300">{error}</p> : null}

      <div className="panel overflow-x-auto rounded-2xl">
        <table className="min-w-full text-left text-sm">
          <thead className="text-xs uppercase tracking-wider text-[var(--muted)]">
            <tr>
              <th className="px-4 py-3">Time</th>
              <th className="px-4 py-3">Request</th>
              <th className="px-4 py-3">Mode</th>
              <th className="px-4 py-3">Decision</th>
              <th className="px-4 py-3">Prob</th>
              <th className="px-4 py-3">Latency</th>
              <th className="px-4 py-3">Tier</th>
              <th className="px-4 py-3">Amount</th>
            </tr>
          </thead>
          <tbody>
            {items.map((row) => (
              <tr key={row.id} className="border-t border-white/5">
                <td className="px-4 py-3 font-mono text-xs text-[var(--muted)]">
                  {new Date(row.created_at).toLocaleString()}
                </td>
                <td className="px-4 py-3 font-mono text-xs">{row.request_id}</td>
                <td className="px-4 py-3">{row.routing_mode}</td>
                <td className="px-4 py-3">{row.decision}</td>
                <td className="px-4 py-3 font-mono">{(row.fraud_probability * 100).toFixed(2)}%</td>
                <td className="px-4 py-3 font-mono">{row.cumulative_latency_ms}ms</td>
                <td className="px-4 py-3">{row.last_tier}</td>
                <td className="px-4 py-3 font-mono">${Number(row.amount).toFixed(2)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
