import { createHash, randomBytes } from "node:crypto";

import { expect, test } from "@playwright/test";
import type { APIRequestContext } from "@playwright/test";

// The whole path: sign up, add a mirror, the mirror sends a workout, and it
// shows up on the dashboard.

function newEmail() {
  return `e2e-${Date.now()}-${Math.random().toString(36).slice(2, 8)}@example.com`;
}

/** Sends the events of one workout, as a mirror would: 2 sets of curls, 1 of presses */
async function mirrorSendsAWorkout(request: APIRequestContext, token: string) {
  const start = Date.now() - 20 * 60_000;
  let t = start;
  const at = (seconds = 0) => new Date((t += seconds * 1000)).toISOString();
  const workoutId = crypto.randomUUID();
  const events: object[] = [];
  const event = (type: string, time: string, data: object) =>
    events.push({ id: crypto.randomUUID(), type, at: time, data });

  event("workout_started", at(), { workout_id: workoutId });
  for (const [exercise, number, reps] of [
    ["curl", 1, 10],
    ["curl", 2, 8],
    ["press", 1, 6],
  ] as const) {
    const setId = crypto.randomUUID();
    event("set_started", at(60), { workout_id: workoutId, set_id: setId, exercise, set_number: number });
    for (let count = 1; count <= reps; count++) {
      event("rep", at(2), { set_id: setId, side: "left", count, top: 40 });
    }
    event("set_ended", at(1), { set_id: setId, reps });
  }
  event("workout_ended", at(30), { workout_id: workoutId });

  const response = await request.post("/api/v1/events", {
    data: { events },
    headers: { Authorization: `Bearer ${token}` },
  });
  expect(response.ok()).toBeTruthy();
  expect((await response.json()).applied).toBe(events.length);
}

test("sign up, add a mirror, and see its workout", async ({ page, request }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "Sign in" })).toBeVisible();
  await page.getByRole("link", { name: "Create one" }).click();
  // Wait for the new page: the sign-in form has an Email field too, and typing
  // into it just before the page changes loses the email
  await expect(page.getByRole("heading", { name: "Create an account" })).toBeVisible();

  await page.getByLabel("Email").fill(newEmail());
  await page.getByLabel("Password").fill("a good long password");
  await page.getByRole("button", { name: "Create account" }).click();

  // You start on the Train page. A new account has no mirrors yet
  await expect(page.getByRole("heading", { name: "Train" })).toBeVisible();
  await page.getByRole("link", { name: "Dashboard" }).click();
  await expect(page.getByText("Connect your first mirror")).toBeVisible();
  await page.getByRole("link", { name: "Add a mirror" }).click();

  await page.getByLabel("Name").fill("E2E mirror");
  await page.getByRole("button", { name: "Add mirror" }).click();
  await expect(page.getByText("“E2E mirror” is added")).toBeVisible();
  const config = JSON.parse((await page.locator("pre[aria-label='Mirror settings']").textContent())!);
  expect(config.name).toBe("E2E mirror");

  await mirrorSendsAWorkout(request, config.token);

  await page.getByRole("link", { name: "Dashboard" }).click();
  await expect(page.getByRole("heading", { name: "Dashboard" })).toBeVisible();
  const repsTile = page.locator(".card", { hasText: /^Reps/ }).first();
  await expect(repsTile).toContainText("24");
  await expect(page.getByRole("list", { name: "Reps by exercise" })).toContainText("Bicep curl");

  // Open the workout and check its sets
  await page.getByRole("link", { name: "See all" }).click();
  await page.locator("tbody a").first().click();
  const sets = page.getByRole("listitem");
  await expect(sets).toHaveCount(3);
  await expect(sets.nth(0)).toContainText("10 reps");
  await expect(sets.nth(2)).toContainText("Overhead press");

  // A reload keeps you signed in; signing out doesn't
  await page.reload();
  await expect(page.getByRole("heading", { name: "Sets" })).toBeVisible();
  await page.getByRole("button", { name: "Sign out" }).click();
  await expect(page.getByRole("heading", { name: "Sign in" })).toBeVisible();
});

test("one user can't see another user's workouts", async ({ page, request }) => {
  // Someone else's account, with a workout
  const other = await request.post("/api/v1/auth/register", {
    data: { email: newEmail(), password: "another long password" },
  });
  const { access_token } = await other.json();
  const device = await request.post("/api/v1/devices", {
    data: { name: "Their mirror" },
    headers: { Authorization: `Bearer ${access_token}` },
  });
  await mirrorSendsAWorkout(request, (await device.json()).token);

  await page.goto("/register");
  await page.getByLabel("Email").fill(newEmail());
  await page.getByLabel("Password").fill("a good long password");
  await page.getByRole("button", { name: "Create account" }).click();
  await page.getByRole("link", { name: "Workouts" }).click();
  await expect(page.getByText("No workouts yet")).toBeVisible();
});

test("the demo shows a full dashboard and can't be changed", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("button", { name: "Try the demo" }).click();
  // The first visit on a fresh database simulates two months of workouts,
  // and the other browser waits its turn, so this can take a while on CI
  await expect(page.getByText("You're looking at a demo")).toBeVisible({ timeout: 30_000 });
  await expect(page.getByRole("heading", { name: "Train" })).toBeVisible();

  await page.getByRole("link", { name: "Dashboard" }).click();
  await expect(page.getByRole("heading", { name: "Reps per day" })).toBeVisible();
  await expect(page.getByRole("list", { name: "Reps by exercise" })).toContainText("Lateral raise");

  await page.getByRole("link", { name: "Mirrors" }).click();
  await expect(page.getByText("Demo mirror")).toBeVisible();
  await expect(page.getByRole("button", { name: "Remove" })).toHaveCount(0);
  await expect(page.getByRole("heading", { name: "This is the demo" })).toBeVisible();
});

test("the dashboard shows a mirror's set as it happens, without a reload", async ({ page, request }) => {
  await page.goto("/register");
  await page.getByLabel("Email").fill(newEmail());
  await page.getByLabel("Password").fill("a good long password");
  await page.getByRole("button", { name: "Create account" }).click();
  await page.getByRole("link", { name: "Mirrors" }).click();
  await page.getByLabel("Name").fill("Live mirror");
  await page.getByRole("button", { name: "Add mirror" }).click();
  const config = JSON.parse((await page.locator("pre[aria-label='Mirror settings']").textContent())!);

  await page.getByRole("link", { name: "Dashboard" }).click();
  await expect(page.getByText("Live", { exact: true })).toBeVisible();

  // The mirror starts a set of lateral raises: 3 reps so far
  const at = () => new Date().toISOString();
  const workoutId = crypto.randomUUID();
  const setId = crypto.randomUUID();
  const events = [
    { id: crypto.randomUUID(), type: "workout_started", at: at(), data: { workout_id: workoutId } },
    {
      id: crypto.randomUUID(),
      type: "set_started",
      at: at(),
      data: { workout_id: workoutId, set_id: setId, exercise: "raise", set_number: 1 },
    },
    ...[1, 2, 3].map((count) => ({
      id: crypto.randomUUID(),
      type: "rep",
      at: at(),
      data: { set_id: setId, side: "left", count, top: 80 },
    })),
  ];
  const response = await request.post("/api/v1/events", {
    data: { events },
    headers: { Authorization: `Bearer ${config.token}` },
  });
  expect(response.ok()).toBeTruthy();

  const now = page.getByRole("region", { name: "Training now" });
  await expect(now).toContainText("Live mirror");
  await expect(now).toContainText("Lateral raise");
  await expect(now).toContainText("Set 1 · 3 reps");
  // The stats load again by themselves
  await expect(page.locator(".card", { hasText: /^Reps/ }).first()).toContainText("3");
});

test("connect a mirror by scanning its QR code", async ({ page, request }) => {
  // The mirror makes its own token and asks for a code, sending only the hash
  const token = randomBytes(32).toString("base64url");
  const tokenHash = createHash("sha256").update(token).digest("hex");
  const started = await request.post("/api/v1/pairing", { data: { token_hash: tokenHash, name: "Hallway mirror" } });
  expect(started.status()).toBe(201);
  const { code } = await started.json();
  const mirrorAsks = () => request.get(`/api/v1/pairing/${code}`, { headers: { Authorization: `Bearer ${token}` } });
  expect((await (await mirrorAsks()).json()).status).toBe("waiting");

  // The phone opens the QR code's link: sign up first, then straight back to it
  await page.goto(`/pair/${code}`);
  await page.getByRole("link", { name: "Create one" }).click();
  await expect(page.getByRole("heading", { name: "Create an account" })).toBeVisible();
  await page.getByLabel("Email").fill(newEmail());
  await page.getByLabel("Password").fill("a good long password");
  await page.getByRole("button", { name: "Create account" }).click();
  const form = page.getByRole("region", { name: "Connect a mirror" });
  await expect(form).toContainText(`${code.slice(0, 4)}-${code.slice(4)}`);
  await form.getByRole("button", { name: "Connect mirror" }).click();
  await expect(page.getByText("“Hallway mirror” is connected")).toBeVisible();

  // The mirror hears it's connected, and its own token works
  const answer = await (await mirrorAsks()).json();
  expect(answer.status).toBe("paired");
  const me = await request.get("/api/v1/devices/me", { headers: { Authorization: `Bearer ${token}` } });
  expect((await me.json()).name).toBe("Hallway mirror");
  await page.getByRole("link", { name: "Mirrors" }).click();
  await expect(page.getByText("Hallway mirror")).toBeVisible();
});
