import { mkdirSync } from "node:fs";
import { resolve } from "node:path";

import { expect, test, type Page } from "@playwright/test";

const reviewDir = resolve("test-results/review");
const brokerOrigin = "https://broker.test";
const appOrigin = "http://127.0.0.1:4173";

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

async function openFirstPrimaryDetail(page: Page): Promise<boolean> {
  await page.goto("#/library?target=primary");
  const cards = page.locator(".library-card");
  if (await cards.count() === 0) {
    await expect(page.getByRole("heading", { name: "Медиатека пока пуста" })).toBeVisible();
    return false;
  }
  const href = await cards.first().getAttribute("href");
  expect(href).toBeTruthy();
  await page.goto(href ?? "#/library?target=primary");
  await expect(page.locator(".detail-hero")).toHaveAttribute("data-motion", "reduced");
  return true;
}

async function expectTodaySurface(page: Page) {
  const hero = page.getByTestId("cinema-hero");
  if (await hero.count()) {
    await expect(hero).toHaveAttribute("data-motion", "reduced");
    return;
  }
  await expect(page.getByTestId("home-empty")).toHaveAttribute("data-motion", "reduced");
  await expect(page.getByRole("heading", { name: "Пока без готовой рекомендации" })).toBeVisible();
}

test("capture art-direction review surfaces", async ({ page }) => {
  await page.emulateMedia({ reducedMotion: "reduce" });

  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto("#/today");
  await expectTodaySurface(page);
  await page.screenshot({ path: resolve(reviewDir, "today-desktop.png"), fullPage: true });

  await page.goto("#/library?target=couple");
  await expect(page.getByRole("heading", { name: "Медиатека", exact: true })).toBeVisible();
  await warmLazyArtwork(page);
  await page.screenshot({ path: resolve(reviewDir, "library-desktop.png"), fullPage: true });

  const desktopCards = page.locator(".library-card");
  if (await desktopCards.count()) {
    const firstHref = await desktopCards.first().getAttribute("href");
    expect(firstHref).toBeTruthy();
    await page.goto(firstHref ?? "#/library?target=couple");
    await expect(page.locator(".detail-hero")).toHaveAttribute("data-motion", "reduced");
    await page.screenshot({ path: resolve(reviewDir, "detail-desktop.png"), fullPage: true });
  } else {
    await expect(page.getByRole("heading", { name: "Медиатека пока пуста" })).toBeVisible();
  }

  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("#/today");
  await expectTodaySurface(page);
  await page.screenshot({ path: resolve(reviewDir, "today-mobile.png"), fullPage: true });

  await page.goto("#/library?target=couple");
  await expect(page.getByRole("heading", { name: "Медиатека", exact: true })).toBeVisible();
  await warmLazyArtwork(page);
  await page.screenshot({ path: resolve(reviewDir, "library-mobile.png"), fullPage: true });

  const mobileCards = page.locator(".library-card");
  if (await mobileCards.count()) {
    const mobileFirstHref = await mobileCards.first().getAttribute("href");
    expect(mobileFirstHref).toBeTruthy();
    await page.goto(mobileFirstHref ?? "#/library?target=couple");
    await expect(page.locator(".detail-hero")).toHaveAttribute("data-motion", "reduced");
    await page.screenshot({ path: resolve(reviewDir, "detail-mobile.png"), fullPage: true });
  } else {
    await expect(page.getByRole("heading", { name: "Медиатека пока пуста" })).toBeVisible();
  }
});

test("capture feedback editor review surfaces", async ({ page }) => {
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.context().route(`${brokerOrigin}/v1/auth/start`, async (route) => {
    await route.fulfill({
      contentType: "text/html",
      body: `<!doctype html><script>window.opener.postMessage({type:'media-broker-auth',token:'broker-token'}, '${appOrigin}'); window.close();</script>`,
    });
  });

  await page.setViewportSize({ width: 1440, height: 900 });
  const hasWork = await openFirstPrimaryDetail(page);
  test.skip(!hasWork, "Пустая post-reset медиатека: detail/editor появятся после первого сохранённого фильма.");

  const primaryCard = page.locator(".signal-panel").filter({
    has: page.getByRole("heading", { name: "Я", exact: true }),
  }).first();
  const popup = page.waitForEvent("popup");
  await primaryCard.getByRole("button", { name: "Изменить моё впечатление" }).click();
  await popup;
  await expect(page.getByRole("form", { name: "Редактирование впечатления — Я" })).toBeVisible();
  await page.screenshot({ path: resolve(reviewDir, "detail-editor-desktop.png"), fullPage: true });

  await page.setViewportSize({ width: 390, height: 844 });
  await expect(page.getByRole("form", { name: "Редактирование впечатления — Я" })).toBeVisible();
  await page.screenshot({ path: resolve(reviewDir, "detail-editor-mobile.png"), fullPage: true });
});
