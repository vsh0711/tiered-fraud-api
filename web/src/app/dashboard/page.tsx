"use client";

import { useEffect, useRef, useState } from "react";
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

export default function OverviewPage() {
  const [health, setHealth] = useState<any>(null);
  const [stats, setStats] = useState<any>(null);
  const [report, setReport] = useState<any>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [uploadName, setUploadName] = useState("");
  const fileRef = useRef<HTMLInputElement>(null);

  async function load() {
    const token = localStorage.getItem("fraud_token") || "";
    const [h, s] = await Promise.all([api.health(), api.stats(token)]);
    setHealth(h);
    setStats(s);
    try {
      setReport(await api.captureReport(token));
    } catch {
      setReport(null);
    }
  }

  useEffect(() => {
    load().catch((e) => setError(e.message));
  }, []);

  async function runSyntheticReport() {
    setBusy(true);
    setError("");
    try {
      const token = localStorage.getItem("fraud_token") || "";
      const r = await api.runCaptureReport(token, 1200);
      setReport(r);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Report failed");
    } finally {
      setBusy(false);
    }
  }

  async function onUpload(file: File | null) {
    if (!file) return;
    setBusy(true);
    setError("");
    setUploadName(file.name);
    try {
      const token = localStorage.getItem("fraud_token") || "";
      const r = await api.uploadCaptureReport(token, file);
      setReport(r);
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Upload failed");
    } finally {
      setBusy(false);
    }
  }

  async function downloadTemplate() {
    const token = localStorage.getItem("fraud_token") || "";
    const res = await fetch(api.holdoutTemplateUrl, {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!res.ok) {
      setError("Could not download template");
      return;
    }
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "holdout_template.csv";
    a.click();
    URL.revokeObjectURL(url);
  }

  const latencyData = Object.entries(stats?.latency_ms_avg || {}).map(([mode, value]) => ({
    mode,
    latency: Number(value),
  }));
  const decisionData = Object.entries(stats?.by_decision || {}).map(([decision, value]) => ({
    decision,
    count: Number(value),
  }));
  const captureData = report
    ? [
        {
          mode: "baseline",
          capture: report.fraud_capture_at_5pct_fpr?.baseline ?? 0,
          recall: report.operational_flagging?.baseline?.recall_fraud_capture ?? 0,
        },
        {
          mode: "optimized",
          capture: report.fraud_capture_at_5pct_fpr?.optimized ?? 0,
          recall: report.operational_flagging?.optimized?.recall_fraud_capture ?? 0,
        },
      ]
    : [];

  return (
    <div className="space-y-6">
      <header>
        <h2 className="text-2xl font-semibold tracking-tight">Overview</h2>
        <p className="text-sm text-[var(--muted)]">
          Live Postgres stats + holdout reports from your uploaded labeled CSV (or synthetic generator)
        </p>
      </header>

      {error ? <p className="text-rose-300">{error}</p> : null}

      <section className="panel rounded-2xl p-4 text-sm leading-relaxed text-[var(--muted)]">
        <p className="mb-2 font-medium text-teal-200">Sign-in → numbers (what is real)</p>
        <ol className="list-decimal space-y-1 pl-5">
          <li>
            <span className="text-white">Sign in</span> → JWT stored; console creates your own API key (not demo
            creds).
          </li>
          <li>
            <span className="text-white">Health tiles</span> → live `/v1/health` (API/DB/Redis/models).
          </li>
          <li>
            <span className="text-white">Persisted decisions / latency charts / totals</span> → counted from
            Postgres `score_events` via `/v1/history/stats` (every Playground/API score written there).
          </li>
          <li>
            <span className="text-white">Holdout report cards</span> → each row in your file (or synthetic
            set) is scored by the real ML+OR pipeline; capture/recall/mix/latency are computed from those
            scores vs your `is_fraud` labels. Nothing in those cards is hardcoded.
          </li>
        </ol>
      </section>

      <section className="panel space-y-3 rounded-2xl p-4">
        <div className="flex flex-wrap items-end justify-between gap-3">
          <div>
            <h3 className="font-medium text-white">Holdout report from your document</h3>
            <p className="text-sm text-[var(--muted)]">
              Upload CSV with columns: amount, merchant_category, country, device_risk_score, velocity_1h,
              velocity_24h, is_fraud (0/1). Optional: is_international, hour_of_day, request_id.
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <button
              onClick={downloadTemplate}
              className="rounded-xl border px-3 py-2 text-sm hover:bg-white/5"
              type="button"
            >
              Download template CSV
            </button>
            <button
              onClick={() => fileRef.current?.click()}
              disabled={busy}
              className="rounded-xl bg-gradient-to-r from-teal-400 to-sky-400 px-4 py-2 text-sm font-medium text-slate-950 disabled:opacity-60"
              type="button"
            >
              {busy ? "Scoring upload…" : "Upload CSV & score"}
            </button>
            <button
              onClick={runSyntheticReport}
              disabled={busy}
              className="rounded-xl border px-3 py-2 text-sm hover:bg-white/5 disabled:opacity-60"
              type="button"
            >
              Run synthetic holdout
            </button>
          </div>
        </div>
        <input
          ref={fileRef}
          type="file"
          accept=".csv,text/csv"
          className="hidden"
          onChange={(e) => onUpload(e.target.files?.[0] || null)}
        />
        {uploadName ? (
          <p className="font-mono text-xs text-[var(--muted)]">Last selected file: {uploadName}</p>
        ) : null}
        {report ? (
          <p className="font-mono text-xs text-teal-200">
            Active report source: {report.source}
            {report.source_name ? ` · ${report.source_name}` : ""} · n={report.n_samples}
          </p>
        ) : (
          <p className="text-xs text-[var(--muted)]">No holdout report yet — upload a CSV to generate one.</p>
        )}
      </section>

      <section className="grid gap-4 md:grid-cols-4">
        {[
          ["API", health?.status || "…"],
          ["Models", health?.models_loaded ? "loaded" : "pending"],
          ["Database", health?.database || "…"],
          ["Redis", health?.redis || "…"],
        ].map(([label, value]) => (
          <div key={label} className="panel rounded-2xl p-4">
            <p className="text-xs uppercase tracking-wider text-[var(--muted)]">{label}</p>
            <p className="mt-2 font-mono text-lg text-teal-200">{value}</p>
            <p className="mt-1 text-[10px] uppercase tracking-wider text-[var(--muted)]">live health</p>
          </div>
        ))}
      </section>

      {report ? (
        <section className="grid gap-4 lg:grid-cols-3">
          <div className="panel rounded-2xl p-4">
            <p className="text-xs uppercase tracking-wider text-[var(--muted)]">Holdout fraud rate</p>
            <p className="mt-2 font-mono text-3xl">
              {(report.fraud_rate_holdout * 100).toFixed(2)}%
            </p>
            <p className="mt-1 text-sm text-[var(--muted)]">
              {report.n_samples} rows from {report.source === "uploaded_file" ? "your file" : "generator"}
            </p>
          </div>
          <div className="panel rounded-2xl p-4">
            <p className="text-xs uppercase tracking-wider text-[var(--muted)]">Latency savings</p>
            <p className="mt-2 font-mono text-3xl text-teal-300">
              {report.latency_ms_mean?.savings_pct ?? 0}%
            </p>
            <p className="mt-1 text-sm text-[var(--muted)]">
              {report.latency_ms_mean?.optimized}ms opt vs {report.latency_ms_mean?.baseline}ms base
            </p>
          </div>
          <div className="panel rounded-2xl p-4">
            <p className="text-xs uppercase tracking-wider text-[var(--muted)]">Operational recall</p>
            <p className="mt-2 font-mono text-3xl text-sky-300">
              {(
                (report.operational_flagging?.optimized?.recall_fraud_capture ?? 0) * 100
              ).toFixed(1)}
              %
            </p>
            <p className="mt-1 text-sm text-[var(--muted)]">
              flag rate{" "}
              {((report.operational_flagging?.optimized?.flag_rate ?? 0) * 100).toFixed(1)}% · FPR{" "}
              {((report.operational_flagging?.optimized?.fpr ?? 0) * 100).toFixed(1)}%
            </p>
          </div>
        </section>
      ) : null}

      <section className="grid gap-4 lg:grid-cols-2">
        <div className="panel rounded-2xl p-4">
          <h3 className="mb-1 text-sm font-medium text-[var(--muted)]">
            Avg latency by mode (ms) — from Postgres
          </h3>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={latencyData}>
                <CartesianGrid stroke="rgba(120,160,200,0.12)" vertical={false} />
                <XAxis dataKey="mode" stroke="#8aa0b8" />
                <YAxis stroke="#8aa0b8" />
                <Tooltip contentStyle={{ background: "#0d1b2e", border: "1px solid #334155" }} />
                <Bar dataKey="latency" fill="#2dd4bf" radius={[8, 8, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
        <div className="panel rounded-2xl p-4">
          <h3 className="mb-1 text-sm font-medium text-[var(--muted)]">
            Persisted decisions — from Postgres
          </h3>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={decisionData}>
                <CartesianGrid stroke="rgba(120,160,200,0.12)" vertical={false} />
                <XAxis dataKey="decision" stroke="#8aa0b8" />
                <YAxis stroke="#8aa0b8" />
                <Tooltip contentStyle={{ background: "#0d1b2e", border: "1px solid #334155" }} />
                <Bar dataKey="count" fill="#38bdf8" radius={[8, 8, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </section>

      {report ? (
        <section className="grid gap-4 lg:grid-cols-2">
          <div className="panel rounded-2xl p-4">
            <h3 className="mb-4 text-sm font-medium text-[var(--muted)]">
              Holdout capture @ 5% FPR vs operational recall — computed from scored file
            </h3>
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={captureData}>
                  <CartesianGrid stroke="rgba(120,160,200,0.12)" vertical={false} />
                  <XAxis dataKey="mode" stroke="#8aa0b8" />
                  <YAxis stroke="#8aa0b8" />
                  <Tooltip contentStyle={{ background: "#0d1b2e", border: "1px solid #334155" }} />
                  <Bar dataKey="capture" name="capture@5%FPR" fill="#fb7185" radius={[8, 8, 0, 0]} />
                  <Bar dataKey="recall" name="op recall" fill="#fbbf24" radius={[8, 8, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
          <div className="panel rounded-2xl p-4">
            <h3 className="mb-3 text-sm font-medium text-[var(--muted)]">Decision mix (holdout %)</h3>
            <div className="grid grid-cols-2 gap-3 text-sm">
              {(["baseline", "optimized"] as const).map((mode) => (
                <div key={mode} className="rounded-xl border border-white/10 p-3">
                  <p className="mb-2 font-medium capitalize text-teal-200">{mode}</p>
                  {Object.entries(report.decision_mix_pct?.[mode] || {}).map(([k, v]) => (
                    <p key={k} className="font-mono text-[var(--muted)]">
                      {k}: {String(v)}%
                    </p>
                  ))}
                </div>
              ))}
            </div>
            <p className="mt-4 font-mono text-xs text-[var(--muted)]">
              thresholds: approve={report.thresholds?.approve_threshold} decline=
              {report.thresholds?.decline_threshold}
            </p>
          </div>
        </section>
      ) : null}

      <section className="panel rounded-2xl p-4">
        <h3 className="text-sm font-medium text-[var(--muted)]">Totals — Postgres score_events</h3>
        <p className="mt-2 font-mono text-3xl">{stats?.requests_total ?? 0}</p>
        <p className="text-sm text-[var(--muted)]">persisted score events</p>
      </section>
    </div>
  );
}
