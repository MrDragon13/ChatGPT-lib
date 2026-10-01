import { mkdirSync } from "node:fs";
import { resolve } from "node:path";

import { expect, test, type Page } from "@playwright/test";

const reviewDir = resolve("test-results/review");

test.beforeAll(() => {
  mkdirSync(reviewDir, { recursive: true });
});

async function warmLazyArtwork(page: Page) {
  const viewportHeight = page.viewportSize()?.height ?? 900;
  const scrollHeight = await page.evaluate(() => document.documentElement.scrollHeight);
  for (let y = 0; y < scrollHeight; y += Math.max(480, Math.floor(viewportHeight * 0.8))) {
    await page.evaluate((nextY) => window.scrollTo(0, nextY), y);
    await page.waitForTimeout(35);
  }
  await page.evaluate(() => window.scrollTo(0, document.documentElement.scrollHeight));
  await page.waitForLoadState("networkidle");
  await page.evaluate(() => window.scrollTo(0, 0));
}

test("capture art-direction review surfaces", async ({ page }) => {
  await page.emulateMedia({ reducedMotion: "reduce" });

  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto("#/today");
  await expect(page.getByTestId("cinema-hero")).toHaveAttribute("data-motion", "reduced");
  await page.screenshot({ path: resolve(reviewDir, "today-desktop.png"), fullPage: true });

  await page.goto("#/library?target=couple");
  await expect(page.getByRole("heading", { name: "Медиатека" })).toBeVisible();
  await warmLazyArtwork(page);
  await page.screenshot({ path: resolve(reviewDir, "library-desktop.png"), fullPage: true });

  const firstHref = await page.locator(".library-card").first().getAttribute("href");
  expect(firstHref).toBeTruthy();
  await page.goto(firstHref ?? "#/library?target=couple");
  await expect(page.locator(".detail-hero")).toHaveAttribute("data-motion", "reduced");
  await page.screenshot({ path: resolve(reviewDir, "detail-desktop.png"), fullPage: true });

  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("#/today");
  await expect(page.getByTestId("cinema-hero")).toHaveAttribute("data-motion", "reduced");
  await page.screenshot({ path: resolve(reviewDir, "today-mobile.png"), fullPage: true });

  await page.goto("#/library?target=couple");
  await expect(page.getByRole("heading", { name: "Медиатека" })).toBeVisible();
  await warmLazyArtwork(page);
  await page.screenshot({ path: resolve(reviewDir, "library-mobile.png"), fullPage: true });

  const mobileFirstHref = await page.locator(".library-card").first().getAttribute("href");
  expect(mobileFirstHref).toBeTruthy();
  await page.goto(mobileFirstHref ?? "#/library?target=couple");
  await expect(page.locator(".detail-hero")).toHaveAttribute("data-motion", "reduced");
  await page.screenshot({ path: resolve(reviewDir, "detail-mobile.png"), fullPage: true });
});
