"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";

export default function JobsPage() {
  const [jobs, setJobs] = useState<any[]>([]);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function refresh() {
    const token = localStorage.getItem("fraud_token") || "";
    setJobs(await api.jobs(token));
  }

  useEffect(() => {
    refresh().catch((e) => setError(e.message));
    const id = setInterval(() => {
      refresh().catch(() => undefined);
    }, 4000);
    return () => clearInterval(id);
  }, []);

  async function enqueue(job_type: string, payload: Record<string, unknown>) {
    setBusy(true);
    setError("");
    try {
      const token = localStorage.getItem("fraud_token") || "";
      await api.enqueueJob(token, job_type, payload);
      await refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Enqueue failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="space-y-6">
      <header className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h2 className="text-2xl font-semibold tracking-tight">Async jobs</h2>
          <p className="text-sm text-[var(--muted)]">Redis-backed batch scoring and drift scans</p>
        </div>
        <div className="flex gap-2">
          <button
            disabled={busy}
            onClick={() => enqueue("batch_score", { n_samples: 40, routing_mode: "optimized" })}
            className="rounded-xl border px-4 py-2 text-sm hover:bg-white/5 disabled:opacity-60"
          >
            Enqueue batch score
          </button>
          <button
            disabled={busy}
            onClick={() => enqueue("drift_scan", { n_samples: 1500, drift_strength: 0.35 })}
            className="rounded-xl bg-gradient-to-r from-teal-400 to-sky-400 px-4 py-2 text-sm font-medium text-slate-950 disabled:opacity-60"
          >
            Enqueue drift scan
          </button>
        </div>
      </header>

      {error ? <p className="text-rose-300">{error}</p> : null}

      <div className="panel overflow-x-auto rounded-2xl">
        <table className="min-w-full text-left text-sm">
          <thead className="text-xs uppercase tracking-wider text-[var(--muted)]">
            <tr>
              <th className="px-4 py-3">Created</th>
              <th className="px-4 py-3">Type</th>
              <th className="px-4 py-3">Status</th>
              <th className="px-4 py-3">Result / Error</th>
            </tr>
          </thead>
          <tbody>
            {jobs.map((j) => (
              <tr key={j.id} className="border-t border-white/5">
                <td className="px-4 py-3 font-mono text-xs">{new Date(j.created_at).toLocaleString()}</td>
                <td className="px-4 py-3">{j.job_type}</td>
                <td className="px-4 py-3">{j.status}</td>
                <td className="max-w-xl truncate px-4 py-3 font-mono text-xs text-[var(--muted)]">
                  {j.error || JSON.stringify(j.result || {})}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
