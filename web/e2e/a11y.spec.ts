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
  await page.emulateMedia({ reducedMotion: "reduce" });
});

test("today, history and library remain accessible before and after repopulation", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });

  await page.goto("#/today");
  await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
  await expectNoSeriousA11yViolations(page);

  await page.goto("#/history?target=primary");
  await expect(page.getByRole("heading", { name: "История" })).toBeVisible();
  await expectNoSeriousA11yViolations(page);

  await page.goto("#/library?target=couple");
  await expect(page.getByRole("heading", { name: "Медиатека", exact: true })).toBeVisible();
  await expectNoSeriousA11yViolations(page);

  const first = page.locator(".library-card").first();
  if (await first.count()) {
    const firstWorkHref = await first.getAttribute("href");
    expect(firstWorkHref).toBeTruthy();
    await page.goto(firstWorkHref ?? "#/library?target=couple");
    await expect(page.locator(".detail-page")).toBeVisible();
    await expectNoSeriousA11yViolations(page);
  } else {
    await expect(page.getByRole("heading", { name: "Медиатека пока пуста" })).toBeVisible();
  }
});

test("empty and missing states remain accessible", async ({ page }) => {
  await page.goto("#/library?target=couple&q=__no_such_title__");
  const heading = page.getByRole("heading", { name: /^(С такими фильтрами пусто|Медиатека пока пуста)$/ });
  await expect(heading).toBeVisible();
  await expectNoSeriousA11yViolations(page);

  await page.goto("#/work/__missing__?target=couple");
  await expect(page.getByRole("heading", { name: "Такой записи нет в медиатеке" })).toBeVisible();
  await expectNoSeriousA11yViolations(page);
});

test("keyboard path covers profile and library controls in empty or populated state", async ({ page }) => {
  await page.goto("#/today?target=couple");

  const profileNav = page.getByRole("navigation", { name: "Профиль просмотра" });
  const primaryProfile = profileNav.getByRole("link", { name: "Я" });
  await primaryProfile.focus();
  await expect(primaryProfile).toBeFocused();
  await page.keyboard.press("Enter");
  await expect(page).toHaveURL(/#\/today\?target=primary$/);

  await page.goto("#/history?target=primary");
  const firstHistoryItem = page.locator(".history-item").first();
  if (await firstHistoryItem.count()) {
    await firstHistoryItem.focus();
    await expect(firstHistoryItem).toBeFocused();
    const historyOutline = await firstHistoryItem.evaluate((element) => getComputedStyle(element).outlineStyle);
    expect(historyOutline).not.toBe("none");
  } else {
    await expect(page.getByRole("heading", { name: "Здесь пока пусто" })).toBeVisible();
  }

  await page.goto("#/library?target=primary");
  const search = page.getByRole("searchbox", { name: "Поиск" });
  await search.focus();
  await expect(search).toBeFocused();

  const firstCard = page.locator(".library-card").first();
  if (await firstCard.count()) {
    await firstCard.focus();
    await expect(firstCard).toBeFocused();
    const outlineStyle = await firstCard.evaluate((element) => getComputedStyle(element).outlineStyle);
    expect(outlineStyle).not.toBe("none");
    await page.keyboard.press("Enter");
    await expect(page.locator(".detail-page")).toBeVisible();
  } else {
    await expect(page.getByRole("heading", { name: "Медиатека пока пуста" })).toBeVisible();
  }
});
