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

test("library empty state and keyboard focus remain usable", async ({ page }) => {
  await page.goto("#/library?target=couple&q=__no_such_title__");
  await expect(page.getByRole("heading", { name: "С такими фильтрами пусто" })).toBeVisible();
  await expectNoSeriousA11yViolations(page);

  await page.goto("#/today");
  await page.keyboard.press("Tab");
  const firstFocus = await page.evaluate(() => document.activeElement?.textContent?.trim() ?? "");
  expect(firstFocus.length).toBeGreaterThan(0);
  const outlineStyle = await page.evaluate(() => getComputedStyle(document.activeElement as Element).outlineStyle);
  expect(outlineStyle).not.toBe("none");
});
