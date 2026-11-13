const BASE = import.meta.env.VITE_API_URL || "http://localhost:8000/api/v1";

export function token() {
  return sessionStorage.getItem("access_token");
}

export function setTokens(access: string, refresh?: string | null) {
  sessionStorage.setItem("access_token", access);
  if (refresh) sessionStorage.setItem("refresh_token", refresh);
}

export function clearTokens() {
  sessionStorage.removeItem("access_token");
  sessionStorage.removeItem("refresh_token");
}

async function tryRefresh(): Promise<boolean> {
  const rt = sessionStorage.getItem("refresh_token");
  if (!rt) return false;
  const r = await fetch(`${BASE}/auth/refresh`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refresh_token: rt }),
  });
  if (!r.ok) {
    clearTokens();
    return false;
  }
  const data = await r.json();
  setTokens(data.access_token, data.refresh_token);
  return true;
}

export async function api(path: string, options: RequestInit = {}, retry = true): Promise<any> {
  const headers = new Headers(options.headers);
  headers.set("Content-Type", "application/json");
  if (token()) headers.set("Authorization", `Bearer ${token()}`);
  const r = await fetch(`${BASE}${path}`, { ...options, headers });
  if (r.status === 401 && retry && !path.startsWith("/auth/")) {
    const ok = await tryRefresh();
    if (ok) return api(path, options, false);
  }
  if (!r.ok) {
    const body = await r.json().catch(() => ({}));
    throw new Error(body.detail || `HTTP ${r.status}`);
  }
  return r.status === 204 ? null : r.json();
}

export async function logoutApi() {
  const rt = sessionStorage.getItem("refresh_token");
  if (rt) {
    await fetch(`${BASE}/auth/logout`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: rt }),
    }).catch(() => {});
  }
  clearTokens();
}

export { BASE };
