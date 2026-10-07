import { expect, test } from "@playwright/test";

test("desktop primary surface and navigation fit the first viewport", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto("#/today");

  const hero = page.getByTestId("cinema-hero");
  if (await hero.count()) {
    await expect(hero).toBeVisible();
    await expect(hero.getByRole("heading", { level: 1 })).toBeVisible();
    await expect(hero.getByRole("link", { name: "Подробнее" })).toBeVisible();

    const heroBox = await hero.boundingBox();
    const actionBox = await hero.getByRole("link", { name: "Подробнее" }).boundingBox();
    expect(heroBox).not.toBeNull();
    expect(actionBox).not.toBeNull();
    expect((actionBox?.y ?? 9999) + (actionBox?.height ?? 0)).toBeLessThanOrEqual(900);
  } else {
    const empty = page.getByTestId("home-empty");
    await expect(empty).toBeVisible();
    await expect(empty.getByRole("heading", { name: "Пока без готовой рекомендации" })).toBeVisible();
    await expect(empty.getByRole("link", { name: "Открыть медиатеку" })).toBeVisible();
  }

  const navBox = await page.getByRole("navigation", { name: "Основная навигация" }).boundingBox();
  expect(navBox).not.toBeNull();
  expect(navBox?.height ?? 999).toBeLessThanOrEqual(64);
});

test("mobile empty and populated pages do not overflow", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("#/today");
  await expect(page.getByRole("heading", { level: 1 })).toBeVisible();

  const todayOverflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
  expect(todayOverflow).toBeLessThanOrEqual(1);

  await page.goto("#/history?target=primary");
  await expect(page.getByRole("heading", { name: "История" })).toBeVisible();
  const historyOverflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
  expect(historyOverflow).toBeLessThanOrEqual(1);

  await page.goto("#/library?target=couple");
  await expect(page.getByRole("heading", { name: "Медиатека" })).toBeVisible();
  const libraryOverflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
  expect(libraryOverflow).toBeLessThanOrEqual(1);

  const cards = page.locator(".library-card");
  if (await cards.count()) {
    const columnCount = await page.locator(".library-grid").evaluate((element) => {
      const value = getComputedStyle(element).gridTemplateColumns;
      return value.split(" ").filter(Boolean).length;
    });
    expect(columnCount).toBe(2);

    const firstWorkHref = await cards.first().getAttribute("href");
    expect(firstWorkHref).toBeTruthy();
    await page.goto(firstWorkHref ?? "#/library?target=couple");
    await expect(page.locator(".detail-page")).toBeVisible();
    const detailOverflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
    expect(detailOverflow).toBeLessThanOrEqual(1);
  } else {
    await expect(page.getByRole("heading", { name: "Медиатека пока пуста" })).toBeVisible();
  }

  for (const link of await page.locator(".site-header a").all()) {
    const box = await link.boundingBox();
    expect(box?.height ?? 0).toBeGreaterThanOrEqual(44);
  }
});

test("site header stays pinned to the top while scrolling", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 700 });
  await page.goto("#/library?target=primary");
  await expect(page.getByRole("heading", { name: "Медиатека" })).toBeVisible();

  const header = page.locator(".site-header");
  await expect(header).toBeVisible();

  // Empty libraries may not be tall enough to scroll; the sticky contract is
  // still directly observable without manufacturing fake canonical data.
  const scrollHeight = await page.evaluate(() => document.documentElement.scrollHeight);
  if (scrollHeight > 700) {
    await page.evaluate(() => window.scrollTo(0, document.documentElement.scrollHeight));
    await expect.poll(() => page.evaluate(() => window.scrollY)).toBeGreaterThan(0);
  }

  const box = await header.boundingBox();
  expect(box).not.toBeNull();
  expect(Math.abs(box?.y ?? 9999)).toBeLessThanOrEqual(1);
  await expect(header).toHaveCSS("position", "sticky");
  await expect(header).toHaveCSS("top", "0px");
});
