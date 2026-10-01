import { expect, test } from "@playwright/test";

test("reduced motion keeps the hero immediately readable without spatial entrance", async ({ browser }) => {
  const context = await browser.newContext({
    reducedMotion: "reduce",
    viewport: { width: 1440, height: 900 },
  });
  const page = await context.newPage();
  await page.goto("#/today");

  const hero = page.getByTestId("cinema-hero");
  await expect(hero).toHaveAttribute("data-motion", "reduced");
  await expect(hero.getByRole("heading", { level: 1 })).toBeVisible();
  await expect(hero.getByRole("link", { name: "Подробнее" })).toBeVisible();

  const transform = await hero.locator(".cinema-hero__content").evaluate((element) => getComputedStyle(element).transform);
  expect(transform === "none" || transform === "matrix(1, 0, 0, 1, 0, 0)").toBeTruthy();

  await context.close();
});

test("full motion lets a secondary candidate preview a new hero frame", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto("#/today");

  const hero = page.getByTestId("cinema-hero");
  await expect(hero).toHaveAttribute("data-motion", "full");
  const initialTitle = await hero.getByRole("heading", { level: 1 }).textContent();
  const alternatives = hero.locator(".candidate-thumb");
  const count = await alternatives.count();
  test.skip(count === 0, "Нет альтернатив для проверки смены hero");

  await alternatives.first().focus();
  await expect(hero.getByRole("heading", { level: 1 })).not.toHaveText(initialTitle ?? "");
});
