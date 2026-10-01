import { expect, test } from "@playwright/test";

test("desktop hero and navigation fit the first viewport", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto("#/today");

  const hero = page.getByTestId("cinema-hero");
  await expect(hero).toBeVisible();
  await expect(hero.getByRole("heading", { level: 1 })).toBeVisible();
  await expect(hero.getByRole("link", { name: "Подробнее" })).toBeVisible();

  const heroBox = await hero.boundingBox();
  const actionBox = await hero.getByRole("link", { name: "Подробнее" }).boundingBox();
  expect(heroBox).not.toBeNull();
  expect(actionBox).not.toBeNull();
  expect((actionBox?.y ?? 9999) + (actionBox?.height ?? 0)).toBeLessThanOrEqual(900);

  const navBox = await page.getByRole("navigation", { name: "Основная навигация" }).boundingBox();
  expect(navBox).not.toBeNull();
  expect(navBox?.height ?? 999).toBeLessThanOrEqual(64);
});

test("mobile pages do not overflow and library keeps two poster columns", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("#/today");
  await expect(page.getByTestId("cinema-hero")).toBeVisible();

  const todayOverflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
  expect(todayOverflow).toBeLessThanOrEqual(1);

  await page.goto("#/library?target=couple");
  await expect(page.getByRole("heading", { name: "Медиатека" })).toBeVisible();
  const libraryOverflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
  expect(libraryOverflow).toBeLessThanOrEqual(1);

  const columnCount = await page.locator(".library-grid").evaluate((element) => {
    const value = getComputedStyle(element).gridTemplateColumns;
    return value.split(" ").filter(Boolean).length;
  });
  expect(columnCount).toBe(2);

  for (const link of await page.locator(".site-header a").all()) {
    const box = await link.boundingBox();
    expect(box?.height ?? 0).toBeGreaterThanOrEqual(44);
  }
});
