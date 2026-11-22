// Talks to the backend, and keeps the user signed in.
//
// The access token lives only in memory (gone when the tab closes) and is sent
// with every request. The refresh token is kept in localStorage, so a reload
// doesn't sign you out. When a request comes back 401 (access token missing
// or expired), the client swaps the refresh token for a new pair once and
// repeats the request. If that fails too, you're signed out.

import type { TokenPair } from "./types";

const REFRESH_KEY = "easyweight.refreshToken";
const BASE = "/api/v1";

export class ApiError extends Error {
  constructor(
    readonly status: number,
    message: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

let accessToken: string | null = null;
let refreshing: Promise<boolean> | null = null;
const signOutListeners = new Set<() => void>();

function storedRefreshToken(): string | null {
  try {
    return localStorage.getItem(REFRESH_KEY);
  } catch {
    return null;
  }
}

export function hasSession(): boolean {
  return accessToken !== null || storedRefreshToken() !== null;
}

export function setTokens(tokens: TokenPair): void {
  accessToken = tokens.access_token;
  try {
    localStorage.setItem(REFRESH_KEY, tokens.refresh_token);
  } catch {
    // Private mode: stays signed in until the tab closes
  }
}

export function clearTokens(): void {
  accessToken = null;
  try {
    localStorage.removeItem(REFRESH_KEY);
  } catch {
    // nothing stored
  }
}

/** Called when the session ends by itself (the refresh token stopped working) */
export function onSignedOut(listener: () => void): () => void {
  signOutListeners.add(listener);
  return () => signOutListeners.delete(listener);
}

async function errorMessage(response: Response): Promise<string> {
  try {
    const body = await response.json();
    if (typeof body.detail === "string") return body.detail;
    // FastAPI's validation errors: a list of {loc, msg}
    if (Array.isArray(body.detail) && body.detail[0]?.msg) return body.detail[0].msg;
  } catch {
    // not JSON
  }
  return `Request failed (HTTP ${response.status})`;
}

/** Swap the refresh token for a new pair. Several requests failing at once
 * share one refresh, because each refresh token works only once */
function refreshTokens(): Promise<boolean> {
  refreshing ??= (async () => {
    const token = storedRefreshToken();
    if (!token) return false;
    try {
      const response = await fetch(`${BASE}/auth/refresh`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ refresh_token: token }),
      });
      if (!response.ok) return false;
      setTokens(await response.json());
      return true;
    } catch {
      return false;
    }
  })().finally(() => {
    refreshing = null;
  });
  return refreshing;
}

/** An access token for the live connection, refreshed when `renew` is true
 * (the last one was turned away) or there is none yet. Null when signed out */
export async function accessTokenFor(renew = false): Promise<string | null> {
  if (renew || !accessToken) {
    if (!(await refreshTokens())) return accessToken && !renew ? accessToken : null;
  }
  return accessToken;
}

interface RequestOptions {
  method?: string;
  json?: unknown;
  form?: Record<string, string>;
  /** false for sign-in requests, which must not trigger a refresh */
  auth?: boolean;
}

export async function api<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { method = "GET", json, form, auth = true } = options;
  const send = () => {
    const headers: Record<string, string> = { Accept: "application/json" };
    let body: BodyInit | undefined;
    if (json !== undefined) {
      headers["Content-Type"] = "application/json";
      body = JSON.stringify(json);
    } else if (form) {
      body = new URLSearchParams(form);
    }
    if (auth && accessToken) headers.Authorization = `Bearer ${accessToken}`;
    return fetch(`${BASE}${path}`, { method, headers, body });
  };

  let response = await send();
  if (response.status === 401 && auth) {
    if (await refreshTokens()) {
      response = await send();
    } else {
      clearTokens();
      signOutListeners.forEach((listener) => listener());
    }
  }
  if (!response.ok) throw new ApiError(response.status, await errorMessage(response));
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

// Sign-in

export async function login(email: string, password: string): Promise<void> {
  setTokens(
    await api<TokenPair>("/auth/login", {
      method: "POST",
      form: { username: email, password },
      auth: false,
    }),
  );
}

export async function register(email: string, password: string): Promise<void> {
  setTokens(
    await api<TokenPair>("/auth/register", {
      method: "POST",
      json: { email, password },
      auth: false,
    }),
  );
}

/** The read-only demo account, with made-up workouts */
export async function demo(): Promise<void> {
  setTokens(await api<TokenPair>("/auth/demo", { method: "POST", auth: false }));
}

export async function logout(): Promise<void> {
  const token = storedRefreshToken();
  clearTokens();
  if (token) {
    await api("/auth/logout", { method: "POST", json: { refresh_token: token }, auth: false })
      .catch(() => undefined); // signed out here either way
  }
}
