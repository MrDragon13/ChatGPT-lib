import { mkdirSync } from "node:fs";
import { resolve } from "node:path";

import { expect, test } from "@playwright/test";

const reviewDir = resolve("test-results/review");

test.beforeAll(() => {
  mkdirSync(reviewDir, { recursive: true });
});

test("capture art-direction review surfaces", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto("#/today");
  await expect(page.getByTestId("cinema-hero")).toBeVisible();
  await page.screenshot({ path: resolve(reviewDir, "today-desktop.png"), fullPage: true });

  await page.goto("#/library?target=couple");
  await expect(page.getByRole("heading", { name: "Медиатека" })).toBeVisible();
  await page.screenshot({ path: resolve(reviewDir, "library-desktop.png"), fullPage: true });

  const firstHref = await page.locator(".library-card").first().getAttribute("href");
  expect(firstHref).toBeTruthy();
  await page.goto(firstHref ?? "#/library?target=couple");
  await expect(page.locator(".detail-page")).toBeVisible();
  await page.screenshot({ path: resolve(reviewDir, "detail-desktop.png"), fullPage: true });

  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("#/today");
  await expect(page.getByTestId("cinema-hero")).toBeVisible();
  await page.screenshot({ path: resolve(reviewDir, "today-mobile.png"), fullPage: true });
});
