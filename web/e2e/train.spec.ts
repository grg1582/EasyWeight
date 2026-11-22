import { expect, test } from "@playwright/test";

// The Train page in a real browser, with the real pose model. Chromium's fake
// camera shows a test pattern, not a person, so nothing gets counted: this
// checks that MediaPipe and the model load and the camera loop runs. Counting
// itself is covered by src/train/counter.test.ts.

test.use({
  permissions: ["camera"],
  launchOptions: {
    args: ["--use-fake-ui-for-media-stream", "--use-fake-device-for-media-stream"],
  },
});

test("train with the camera", async ({ page }) => {
  await page.goto("/register");
  await page.getByLabel("Email").fill(`e2e-train-${Date.now()}-${Math.random().toString(36).slice(2, 8)}@example.com`);
  await page.getByLabel("Password").fill("a good long password");
  await page.getByRole("button", { name: "Create account" }).click();
  await page.getByRole("link", { name: "Train" }).click();
  await expect(page.getByText("Your video stays on your device")).toBeVisible();

  await page.getByRole("button", { name: "Start camera" }).click();
  // Loading MediaPipe and downloading the model take a few seconds the first time
  await expect(page.getByRole("button", { name: "Stop" })).toBeVisible({ timeout: 60_000 });
  await expect(page.getByText("Step into view")).toBeVisible();
  await expect(page.getByLabel("Reps")).toHaveText("0");

  await page.getByRole("button", { name: "Stop" }).click();
  await expect(page.getByRole("region", { name: "Summary" })).toContainText("No reps this time");
});
