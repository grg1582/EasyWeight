import { afterEach, describe, expect, it, vi } from "vitest";

import { fakeApi, tokens } from "../test/fakeApi";
import { api, clearTokens, hasSession, login, logout, onSignedOut } from "./client";

afterEach(() => {
  clearTokens();
  vi.unstubAllGlobals();
});

describe("api client", () => {
  it("signs in with a form, and sends the access token afterwards", async () => {
    const { calls } = fakeApi({
      "POST /auth/login": () => ({ body: tokens(1) }),
      "GET /users/me": () => ({ body: { email: "roy@example.com" } }),
    });
    await login("roy@example.com", "secret pass");
    expect(calls[0]!.body).toBe("username=roy%40example.com&password=secret+pass");
    expect(localStorage.getItem("easyweight.refreshToken")).toBe("refresh-1");

    await api("/users/me");
    expect(calls[1]!.headers.Authorization).toBe("Bearer access-1");
  });

  it("refreshes once when the access token has expired, then repeats the request", async () => {
    localStorage.setItem("easyweight.refreshToken", "refresh-1"); // after a page reload
    let refreshes = 0;
    const { calls } = fakeApi({
      "POST /auth/refresh": () => {
        refreshes += 1;
        return { body: tokens(2) };
      },
      "GET /stats": (init) =>
        (init.headers as Record<string, string>).Authorization === "Bearer access-2"
          ? { body: { ok: true } }
          : { status: 401, body: { detail: "Not signed in" } },
    });

    // Two requests at once share one refresh: a refresh token works only once
    const [a, b] = await Promise.all([api("/stats"), api("/stats")]);
    expect(a).toEqual({ ok: true });
    expect(b).toEqual({ ok: true });
    expect(refreshes).toBe(1);
    expect(JSON.parse(calls.find((c) => c.path === "/auth/refresh")!.body!)).toEqual({
      refresh_token: "refresh-1",
    });
    expect(localStorage.getItem("easyweight.refreshToken")).toBe("refresh-2");
  });

  it("signs out when the refresh token stops working", async () => {
    localStorage.setItem("easyweight.refreshToken", "stolen-and-used");
    fakeApi({
      "POST /auth/refresh": () => ({ status: 401, body: { detail: "Refresh token was already used" } }),
      "GET /stats": () => ({ status: 401, body: { detail: "Not signed in" } }),
    });
    const signedOut = vi.fn();
    const stop = onSignedOut(signedOut);
    await expect(api("/stats")).rejects.toMatchObject({ status: 401 });
    expect(signedOut).toHaveBeenCalledOnce();
    expect(hasSession()).toBe(false);
    stop();
  });

  it("passes on the server's error message", async () => {
    fakeApi({
      "POST /auth/login": () => ({ status: 401, body: { detail: "Wrong email or password" } }),
    });
    await expect(login("a@example.com", "nope")).rejects.toThrow("Wrong email or password");
  });

  it("signing out forgets the tokens and tells the server", async () => {
    const { calls } = fakeApi({
      "POST /auth/login": () => ({ body: tokens(1) }),
      "POST /auth/logout": () => ({ status: 204 }),
    });
    await login("roy@example.com", "secret pass");
    await logout();
    expect(hasSession()).toBe(false);
    expect(calls.at(-1)!.path).toBe("/auth/logout");
  });
});
