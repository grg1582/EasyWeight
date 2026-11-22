import { vi } from "vitest";

type Handler = (init: RequestInit & { url: string }) => { status?: number; body?: unknown };

/** Replaces fetch with a tiny fake backend: {"GET /users/me": handler} */
export function fakeApi(routes: Record<string, Handler>) {
  const calls: { method: string; path: string; headers: Record<string, string>; body?: string }[] = [];
  const fetchMock = vi.fn(async (input: RequestInfo | URL, init: RequestInit = {}) => {
    const url = String(input);
    const method = init.method ?? "GET";
    const path = url.replace("/api/v1", "").split("?")[0]!;
    const headers = (init.headers ?? {}) as Record<string, string>;
    calls.push({ method, path, headers, body: init.body?.toString() });
    const handler = routes[`${method} ${path}`];
    const { status = 200, body } = handler
      ? handler({ ...init, url })
      : { status: 404, body: { detail: "Not Found" } };
    return new Response(status === 204 ? null : JSON.stringify(body), {
      status,
      headers: { "Content-Type": "application/json" },
    });
  });
  vi.stubGlobal("fetch", fetchMock);
  return { calls, fetchMock };
}

export const tokens = (n = 1) => ({
  access_token: `access-${n}`,
  refresh_token: `refresh-${n}`,
  token_type: "bearer" as const,
});

export const signedIn = (init: { headers?: HeadersInit }) =>
  (init.headers as Record<string, string>)?.Authorization?.startsWith("Bearer access-");
