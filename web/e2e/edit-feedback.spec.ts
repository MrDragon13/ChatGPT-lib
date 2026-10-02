import AxeBuilder from "@axe-core/playwright";
import { expect, test, type Locator, type Page } from "@playwright/test";

const brokerOrigin = "https://broker.test";
const appOrigin = "http://127.0.0.1:4173";
const operationId = "11111111-2222-4333-8444-555555555555";

async function openFirstPrimaryDetail(page: Page): Promise<string> {
  await page.goto("#/library?target=primary");
  const first = page.locator(".library-card").first();
  await expect(first).toBeVisible();
  const href = await first.getAttribute("href");
  expect(href).toBeTruthy();
  await page.goto(href ?? "#/library?target=primary");
  await expect(page.locator(".detail-page")).toBeVisible();
  const match = page.url().match(/#\/work\/([^?]+)/);
  expect(match?.[1]).toBeTruthy();
  return decodeURIComponent(match?.[1] ?? "");
}

function primaryFeedbackCard(page: Page): Locator {
  return page.getByRole("heading", { name: "Я" }).locator("xpath=ancestor::article[1]");
}

function primaryFeedbackForm(page: Page): Locator {
  return page.getByRole("form", { name: "Редактирование впечатления — Я" });
}

async function installBrokerMocks(page: Page) {
  let statusCalls = 0;
  let editedWorkId = "";
  let submittedRating = 9.5;

  await page.context().route(`${brokerOrigin}/v1/auth/start`, async (route) => {
    await route.fulfill({
      contentType: "text/html",
      body: `<!doctype html><script>window.opener.postMessage({type:'media-broker-auth',token:'broker-token'}, '${appOrigin}'); window.close();</script>`,
    });
  });

  await page.route(`${brokerOrigin}/v1/feedback`, async (route) => {
    const body = route.request().postDataJSON() as { work_id: string; rating?: number };
    editedWorkId = body.work_id;
    submittedRating = body.rating ?? submittedRating;
    await route.fulfill({
      status: 202,
      contentType: "application/json",
      body: JSON.stringify({ operation_id: operationId, pr_number: 42, status: "submitted" }),
    });
  });

  await page.route(`${brokerOrigin}/v1/operations/${operationId}`, async (route) => {
    statusCalls += 1;
    const status = statusCalls === 1 ? "checking" : "published";
    await route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({ status, pr_number: 42, ...(status === "published" ? { merge_sha: "merge-sha" } : {}) }),
    });
  });

  await page.route(/\/ChatGPT-lib\/data\/manifest\.json\?rev=.*/, async (route) => {
    const response = await route.fetch({ url: `${appOrigin}/ChatGPT-lib/data/manifest.json` });
    const manifest = await response.json() as {
      works: Array<{
        id: string;
        viewer_signals: Record<string, Record<string, unknown>>;
      }>;
    };
    const work = manifest.works.find((candidate) => candidate.id === editedWorkId);
    if (work) {
      const signal = { ...(work.viewer_signals.primary ?? {}) };
      signal.rating = { score: submittedRating, source: "explicit", confidence: "exact" };
      work.viewer_signals.primary = signal;
    }
    await route.fulfill({ response, json: manifest });
  });
}

test("owner can login, edit rating, observe progress and receive refreshed canonical value", async ({ page }) => {
  await installBrokerMocks(page);
  const workId = await openFirstPrimaryDetail(page);
  const card = primaryFeedbackCard(page);

  const edit = card.getByRole("button", { name: "Изменить моё впечатление" });
  await expect(edit).toBeVisible();
  const popupPromise = page.waitForEvent("popup");
  await edit.click();
  await popupPromise;

  const form = primaryFeedbackForm(page);
  const panel = page.locator(".feedback-editor-panel");
  await expect(form).toBeVisible();
  await expect(panel).toBeVisible();
  await expect(card.locator("form")).toHaveCount(0);

  const panelBox = await panel.boundingBox();
  const gridBox = await page.locator(".signal-grid").boundingBox();
  expect(panelBox).not.toBeNull();
  expect(gridBox).not.toBeNull();
  expect(Math.abs((panelBox?.width ?? 0) - (gridBox?.width ?? 0))).toBeLessThanOrEqual(2);

  const rating = form.getByLabel("Оценка");
  await expect(rating).toBeVisible();
  const current = await rating.inputValue();
  const next = current === "9.5" ? "9" : "9.5";
  await rating.fill(next);
  await form.getByRole("button", { name: "Сохранить" }).click();

  await expect(page.getByText("Изменение отправлено")).toBeVisible();
  await expect(page.getByText("Проверяется")).toBeVisible({ timeout: 8_000 });
  await expect(page.getByText("Опубликовано")).toBeVisible({ timeout: 8_000 });
  await expect(page.getByText(`${next}/10`)).toBeVisible({ timeout: 8_000 });
  await expect(page.getByText("Опубликовано")).toHaveCount(0, { timeout: 8_000 });
  expect(workId).toBeTruthy();
});

test("expired session requires a new login before editing continues", async ({ page }) => {
  let loginCount = 0;
  await page.context().route(`${brokerOrigin}/v1/auth/start`, async (route) => {
    loginCount += 1;
    await route.fulfill({
      contentType: "text/html",
      body: `<!doctype html><script>window.opener.postMessage({type:'media-broker-auth',token:'broker-token-${loginCount}'}, '${appOrigin}'); window.close();</script>`,
    });
  });
  await page.route(`${brokerOrigin}/v1/feedback`, async (route) => {
    if (loginCount === 1) {
      await route.fulfill({ status: 401, contentType: "application/json", body: JSON.stringify({ error: "unauthorized" }) });
    } else {
      await route.fulfill({ status: 202, contentType: "application/json", body: JSON.stringify({ operation_id: operationId, pr_number: 42, status: "submitted" }) });
    }
  });

  await openFirstPrimaryDetail(page);
  const card = primaryFeedbackCard(page);
  const edit = card.getByRole("button", { name: "Изменить моё впечатление" });
  let popup = page.waitForEvent("popup");
  await edit.click();
  await popup;
  let form = primaryFeedbackForm(page);
  const rating = form.getByLabel("Оценка");
  await rating.fill((await rating.inputValue()) === "9" ? "8.5" : "9");
  await form.getByRole("button", { name: "Сохранить" }).click();
  await expect(page.getByText("Сессия истекла. Войдите через GitHub снова.")).toBeVisible();

  await form.getByRole("button", { name: "Отмена" }).click();
  popup = page.waitForEvent("popup");
  await edit.click();
  await popup;
  form = primaryFeedbackForm(page);
  await expect(form.getByLabel("Оценка")).toBeVisible();
  expect(loginCount).toBe(2);
});

test("editor remains usable on mobile, keyboard accessible and reduced-motion safe", async ({ page }) => {
  await installBrokerMocks(page);
  await page.setViewportSize({ width: 390, height: 844 });
  await page.emulateMedia({ reducedMotion: "reduce" });
  await openFirstPrimaryDetail(page);
  const card = primaryFeedbackCard(page);

  const edit = card.getByRole("button", { name: "Изменить моё впечатление" });
  await edit.focus();
  await expect(edit).toBeFocused();
  const popup = page.waitForEvent("popup");
  await page.keyboard.press("Enter");
  await popup;

  const form = primaryFeedbackForm(page);
  await expect(form).toBeVisible();
  await expect(form.getByLabel("Оценка")).toBeVisible();
  await expect(form.getByLabel("Реакция")).toBeVisible();
  await expect(form.getByLabel("Отзыв")).toBeVisible();
  await expect(card.locator("form")).toHaveCount(0);
  await expect(page.locator(".detail-hero")).toHaveAttribute("data-motion", "reduced");

  const result = await new AxeBuilder({ page })
    .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"])
    .analyze();
  expect(result.violations.filter((violation) => violation.impact === "serious" || violation.impact === "critical")).toEqual([]);
});

test("broker failure never breaks public read-only content", async ({ page }) => {
  await page.route(`${brokerOrigin}/**`, (route) => route.abort("failed"));
  await openFirstPrimaryDetail(page);
  await expect(page.locator(".detail-page")).toBeVisible();
  await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
  await primaryFeedbackCard(page).getByRole("button", { name: "Изменить моё впечатление" }).click();
  await expect(page.locator(".detail-page")).toBeVisible();
});
