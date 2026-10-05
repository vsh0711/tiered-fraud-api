const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://127.0.0.1:8742";

export type ScorePayload = {
  request_id: string;
  amount: number;
  merchant_category: string;
  country: string;
  device_risk_score: number;
  velocity_1h: number;
  velocity_24h: number;
  is_international?: boolean;
  hour_of_day?: number;
  deadline_ms?: number;
};

async function request<T>(
  path: string,
  options: RequestInit & { token?: string; apiKey?: string } = {},
): Promise<T> {
  const { token, apiKey, headers, ...rest } = options;
  const res = await fetch(`${API_BASE}${path}`, {
    ...rest,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(apiKey ? { "X-API-Key": apiKey } : {}),
      ...(headers || {}),
    },
    cache: "no-store",
  });
  if (!res.ok) {
    let detail = `HTTP ${res.status}`;
    try {
      const body = await res.json();
      detail = body.detail ? (typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail)) : detail;
    } catch {
      detail = (await res.text()) || detail;
    }
    throw new Error(detail);
  }
  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

export const api = {
  base: API_BASE,
  register: (username: string, email: string, password: string) =>
    request<{ message: string }>("/v1/auth/register", {
      method: "POST",
      body: JSON.stringify({ username, email, password }),
    }),
  login: (username: string, password: string) =>
    request<{ access_token: string; expires_in_minutes: number }>("/v1/auth/login", {
      method: "POST",
      body: JSON.stringify({ username, password }),
    }),
  forgotPassword: (email: string) =>
    request<{ message: string }>("/v1/auth/forgot-password", {
      method: "POST",
      body: JSON.stringify({ email }),
    }),
  resetPassword: (token: string, new_password: string) =>
    request<{ message: string }>("/v1/auth/reset-password", {
      method: "POST",
      body: JSON.stringify({ token, new_password }),
    }),
  createApiKey: (token: string, name: string) =>
    request<{ api_key: string }>("/v1/auth/api-keys", {
      method: "POST",
      token,
      body: JSON.stringify({ name }),
    }),
  health: () => request<{ status: string; models_loaded: boolean; database: string; redis: string }>("/v1/health"),
  compare: (body: ScorePayload, apiKey: string) =>
    request<any>("/v1/score/compare", { method: "POST", body: JSON.stringify(body), apiKey }),
  score: (body: ScorePayload, apiKey: string, mode: "optimized" | "baseline") =>
    request<any>("/v1/score", {
      method: "POST",
      body: JSON.stringify(body),
      apiKey,
      headers: { "X-Routing-Mode": mode },
    }),
  history: (token: string, qs = "") => request<any>(`/v1/history/scores${qs}`, { token }),
  stats: (token: string) => request<any>("/v1/history/stats", { token }),
  metrics: (token: string) => request<any>("/v1/metrics/dashboard", { token }),
  driftSnapshots: (token: string) => request<any[]>("/v1/drift/snapshots", { token }),
  runDrift: (token: string, drift_strength = 0.35) =>
    request<any>("/v1/drift/run", {
      method: "POST",
      token,
      body: JSON.stringify({ n_samples: 2000, drift_strength }),
    }),
  enqueueJob: (token: string, job_type: string, payload: Record<string, unknown>) =>
    request<any>("/v1/jobs", {
      method: "POST",
      token,
      body: JSON.stringify({ job_type, payload }),
    }),
  jobs: (token: string) => request<any[]>("/v1/jobs", { token }),
  captureReport: (token: string) => request<any>("/v1/eval/capture-report", { token }),
  runCaptureReport: (token: string, n_samples = 1200) =>
    request<any>(`/v1/eval/capture-report?n_samples=${n_samples}`, {
      method: "POST",
      token,
    }),
  uploadCaptureReport: async (token: string, file: File) => {
    const form = new FormData();
    form.append("file", file);
    const res = await fetch(`${API_BASE}/v1/eval/capture-report/upload`, {
      method: "POST",
      headers: { Authorization: `Bearer ${token}` },
      body: form,
      cache: "no-store",
    });
    if (!res.ok) {
      let detail = `HTTP ${res.status}`;
      try {
        const body = await res.json();
        detail = body.detail ? (typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail)) : detail;
      } catch {
        detail = (await res.text()) || detail;
      }
      throw new Error(detail);
    }
    return res.json();
  },
  holdoutTemplateUrl: `${API_BASE}/v1/eval/holdout-template.csv`,
};
