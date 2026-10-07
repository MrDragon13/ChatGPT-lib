import { expect, test } from "@playwright/test";

test("reduced motion keeps primary surfaces immediately readable without spatial entrance", async ({ browser }) => {
  const context = await browser.newContext({
    reducedMotion: "reduce",
    viewport: { width: 1440, height: 900 },
  });
  const page = await context.newPage();

  await page.goto("#/today");
  const hero = page.getByTestId("cinema-hero");
  if (await hero.count()) {
    await expect(hero).toHaveAttribute("data-motion", "reduced");
    await expect(hero.getByRole("heading", { level: 1 })).toBeVisible();
    await expect(hero.getByRole("link", { name: "Подробнее" })).toBeVisible();
    const heroTransform = await hero.locator(".cinema-hero__content").evaluate((element) => getComputedStyle(element).transform);
    expect(heroTransform === "none" || heroTransform === "matrix(1, 0, 0, 1, 0, 0)").toBeTruthy();
  } else {
    const empty = page.getByTestId("home-empty");
    await expect(empty).toHaveAttribute("data-motion", "reduced");
    await expect(empty.getByRole("heading", { level: 1, name: "Пока без готовой рекомендации" })).toBeVisible();
    await expect(empty.getByRole("link", { name: "Открыть медиатеку" })).toBeVisible();
  }

  await page.goto("#/library?target=couple");
  const libraryIntro = page.locator(".library-intro");
  await expect(libraryIntro).toHaveAttribute("data-motion", "reduced");
  await expect(libraryIntro.getByRole("heading", { level: 1 })).toBeVisible();
  const libraryTransform = await libraryIntro.evaluate((element) => getComputedStyle(element).transform);
  expect(libraryTransform === "none" || libraryTransform === "matrix(1, 0, 0, 1, 0, 0)").toBeTruthy();

  const first = page.locator(".library-card").first();
  if (await first.count()) {
    const firstHref = await first.getAttribute("href");
    expect(firstHref).toBeTruthy();
    await page.goto(firstHref ?? "#/library?target=couple");
    const detailHero = page.locator(".detail-hero");
    await expect(detailHero).toHaveAttribute("data-motion", "reduced");
    await expect(detailHero.getByRole("heading", { level: 1 })).toBeVisible();
    const detailTransform = await detailHero.evaluate((element) => getComputedStyle(element).transform);
    expect(detailTransform === "none" || detailTransform === "matrix(1, 0, 0, 1, 0, 0)").toBeTruthy();
  } else {
    await expect(page.getByRole("heading", { name: "Медиатека пока пуста" })).toBeVisible();
  }

  await context.close();
});

test("full motion renders either the recommendation hero or the intentional empty state", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto("#/today");

  const hero = page.getByTestId("cinema-hero");
  if (!(await hero.count())) {
    const empty = page.getByTestId("home-empty");
    await expect(empty).toHaveAttribute("data-motion", "full");
    await expect(empty.getByRole("heading", { level: 1, name: "Пока без готовой рекомендации" })).toBeVisible();
    return;
  }

  await expect(hero).toHaveAttribute("data-motion", "full");
  const initialTitle = await hero.getByRole("heading", { level: 1 }).textContent();
  const alternatives = hero.locator(".candidate-thumb");
  const count = await alternatives.count();
  test.skip(count === 0, "Нет альтернатив для проверки смены hero");

  await alternatives.first().focus();
  await expect(hero.getByRole("heading", { level: 1 })).not.toHaveText(initialTitle ?? "");
});
