import AxeBuilder from "@axe-core/playwright";
import { expect, test, type Page } from "@playwright/test";

async function expectNoSeriousA11yViolations(page: Page) {
  const result = await new AxeBuilder({ page })
    .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"])
    .analyze();
  const blocking = result.violations.filter((violation) =>
    violation.impact === "serious" || violation.impact === "critical",
  );
  expect(blocking).toEqual([]);
}

test.beforeEach(async ({ page }) => {
  // Audit the stable rendered state. Motion behavior, including the full-motion
  // path, is covered separately in motion.spec.ts.
  await page.emulateMedia({ reducedMotion: "reduce" });
});

test("today, library and detail have no serious WCAG violations", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });

  await page.goto("#/today");
  await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
  await expectNoSeriousA11yViolations(page);

  await page.goto("#/library?target=couple");
  await expect(page.getByRole("heading", { name: "Медиатека" })).toBeVisible();
  await expectNoSeriousA11yViolations(page);

  const firstWorkHref = await page.locator(".library-card").first().getAttribute("href");
  expect(firstWorkHref).toBeTruthy();
  await page.goto(firstWorkHref ?? "#/library?target=couple");
  await expect(page.locator(".detail-page")).toBeVisible();
  await expectNoSeriousA11yViolations(page);
});

test("empty and missing states remain accessible", async ({ page }) => {
  await page.goto("#/library?target=couple&q=__no_such_title__");
  await expect(page.getByRole("heading", { name: "С такими фильтрами пусто" })).toBeVisible();
  await expectNoSeriousA11yViolations(page);

  await page.goto("#/work/__missing__?target=couple");
  await expect(page.getByRole("heading", { name: "Такой записи нет в медиатеке" })).toBeVisible();
  await expectNoSeriousA11yViolations(page);
});

test("keyboard path covers profile, filters and detail navigation", async ({ page }) => {
  await page.goto("#/today?target=couple");

  const profileNav = page.getByRole("navigation", { name: "Профиль просмотра" });
  const primaryProfile = profileNav.getByRole("link", { name: "Я" });
  await primaryProfile.focus();
  await expect(primaryProfile).toBeFocused();
  await page.keyboard.press("Enter");
  await expect(page).toHaveURL(/#\/today\?target=primary$/);

  await page.goto("#/library?target=primary");
  const search = page.getByRole("searchbox", { name: "Поиск" });
  await search.focus();
  await expect(search).toBeFocused();

  const firstCard = page.locator(".library-card").first();
  await firstCard.focus();
  await expect(firstCard).toBeFocused();
  const outlineStyle = await firstCard.evaluate((element) => getComputedStyle(element).outlineStyle);
  expect(outlineStyle).not.toBe("none");
  await page.keyboard.press("Enter");
  await expect(page.locator(".detail-page")).toBeVisible();
});
