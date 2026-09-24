import { expect, test, type Page } from "@playwright/test";

const signIn = async (page: Page) => {
  await page.goto("/");
  await page.getByLabel("Username").fill("user");
  await page.getByLabel("Password").fill("password");
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page.getByRole("heading", { name: "Kanban Studio" })).toBeVisible();
};

test("requires sign in and rejects invalid credentials", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "Sign in" })).toBeVisible();
  await expect(page.getByText("Kanban Studio")).toHaveCount(0);

  await page.getByLabel("Username").fill("user");
  await page.getByLabel("Password").fill("wrong");
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page.getByText("Invalid username or password")).toBeVisible();
});

test("keeps the session across refresh and logs out", async ({ page }) => {
  await signIn(page);
  await page.reload();
  await expect(page.getByRole("heading", { name: "Kanban Studio" })).toBeVisible();
  await expect(page.getByText("Signed in as user")).toBeVisible();

  await page.getByRole("button", { name: "Log out" }).click();
  await expect(page.getByRole("heading", { name: "Sign in" })).toBeVisible();
  await page.reload();
  await expect(page.getByRole("heading", { name: "Sign in" })).toBeVisible();
});

test.describe("authenticated board", () => {
  test.beforeEach(async ({ page }) => {
    await signIn(page);
  });

  test("loads the kanban board", async ({ page }) => {
    await expect(page.locator('[data-testid^="column-"]')).toHaveCount(5);
  });

  test("adds a card to a column", async ({ page }) => {
    const firstColumn = page.locator('[data-testid^="column-"]').first();
    const cardTitle = `Playwright card ${Date.now()}`;
    await firstColumn.getByRole("button", { name: /add a card/i }).click();
    await firstColumn.getByPlaceholder("Card title").fill(cardTitle);
    await firstColumn.getByPlaceholder("Details").fill("Added via e2e.");
    await firstColumn.getByRole("button", { name: /add card/i }).click();
    await expect(firstColumn.getByText(cardTitle, { exact: true })).toBeVisible();
  });

  test("renames a column and removes a card", async ({ page }) => {
    const firstColumn = page.locator('[data-testid^="column-"]').first();
    const title = firstColumn.getByRole("textbox", { name: "Column title" });

    await title.fill("Ideas");
    await expect(title).toHaveValue("Ideas");

    await firstColumn.getByRole("button", { name: /add a card/i }).click();
    await firstColumn.getByPlaceholder("Card title").fill("Disposable browser card");
    await firstColumn.getByRole("button", { name: /add card/i }).click();

    await firstColumn
      .getByRole("button", {
        name: "Delete Disposable browser card",
        exact: true,
      })
      .click();
    await expect(firstColumn.getByText("Disposable browser card")).toHaveCount(0);
  });

  test("edits a card and keeps the change after reload", async ({ page }) => {
    const card = page.getByTestId("card-card-1");
    await card.getByRole("button", { name: /^Edit / }).click();
    await card.getByRole("textbox", { name: "Card title" }).fill("Edited from browser");
    await card.getByRole("textbox", { name: "Card details" }).fill("Saved through the API.");
    await card.getByRole("button", { name: "Save" }).click();
    await expect(card.getByText("Edited from browser")).toBeVisible();
    await page.reload();
    await expect(page.getByText("Edited from browser")).toBeVisible();
  });

  test("keeps a card edit after logout and sign in", async ({ page }) => {
    const card = page.getByTestId("card-card-1");
    await card.getByRole("button", { name: /^Edit / }).click();
    await card.getByRole("textbox", { name: "Card title" }).fill("Edited across logout");
    await card.getByRole("button", { name: "Save" }).click();
    await expect(card.getByText("Edited across logout")).toBeVisible();

    await page.getByRole("button", { name: "Log out" }).click();
    await expect(page.getByRole("heading", { name: "Sign in" })).toBeVisible();
    await page.getByLabel("Username").fill("user");
    await page.getByLabel("Password").fill("password");
    await page.getByRole("button", { name: "Sign in" }).click();
    await expect(page.getByText("Edited across logout")).toBeVisible();
  });

  test("sends a message in the assistant sidebar", async ({ page }) => {
    await page.route("**/api/ai/chat/stream", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "text/event-stream",
        body: `data: ${JSON.stringify({ type: "delta", content: "Your board has five columns." })}\n\ndata: ${JSON.stringify({ type: "done", assistant_message: "Your board has five columns.", board_changed: false, board: null })}\n\n`,
      });
    });
    const chat = page.getByRole("complementary", { name: "AI assistant" });
    await chat.getByLabel("Message the AI assistant").fill("How many columns are there?");
    await chat.getByRole("button", { name: "Send message" }).click();
    await expect(chat.getByText("Your board has five columns.")).toBeVisible();
  });

  test("moves a card between columns", async ({ page }) => {
    const card = page.getByTestId("card-card-1");
    const targetColumn = page.locator('[data-testid^="column-"]').nth(3);
    const cardBox = await card.boundingBox();
    const columnBox = await targetColumn.boundingBox();
    if (!cardBox || !columnBox) {
      throw new Error("Unable to resolve drag coordinates.");
    }

    await page.mouse.move(
      cardBox.x + cardBox.width / 2,
      cardBox.y + cardBox.height / 2
    );
    await page.mouse.down();
    await page.mouse.move(
      columnBox.x + columnBox.width / 2,
      columnBox.y + 120,
      { steps: 12 }
    );
    await page.mouse.up();
    await expect(targetColumn.getByTestId("card-card-1")).toBeVisible();
  });

  test("reorders cards within a column and keeps the order after reload", async ({ page }) => {
    const firstColumn = page.locator('[data-testid^="column-"]').first();
    const firstTitle = `Reorder first ${Date.now()}`;
    const secondTitle = `Reorder second ${Date.now()}`;

    for (const title of [firstTitle, secondTitle]) {
      await firstColumn.getByRole("button", { name: /add a card/i }).click();
      await firstColumn.getByPlaceholder("Card title").fill(title);
      await firstColumn.getByRole("button", { name: /add card/i }).click();
      await expect(firstColumn.getByText(title, { exact: true })).toBeVisible();
    }

    const firstCard = firstColumn.locator("article").filter({ hasText: firstTitle });
    const secondCard = firstColumn.locator("article").filter({ hasText: secondTitle });
    const firstBox = await firstCard.boundingBox();
    const secondBox = await secondCard.boundingBox();
    if (!firstBox || !secondBox) {
      throw new Error("Unable to resolve reorder coordinates.");
    }

    const persistedMove = page.waitForResponse(
      (response) =>
        response.request().method() === "POST" &&
        response.url().includes("/api/board/cards/") &&
        response.url().endsWith("/move")
    );
    await page.mouse.move(
      secondBox.x + secondBox.width / 2,
      secondBox.y + secondBox.height / 2
    );
    await page.mouse.down();
    await page.mouse.move(
      firstBox.x + firstBox.width / 2,
      firstBox.y + firstBox.height / 3,
      { steps: 12 }
    );
    await page.mouse.up();
    await expect((await persistedMove).ok()).toBe(true);

    const cardTitles = firstColumn.locator("article h4");
    await expect.poll(async () => {
      const titles = await cardTitles.allTextContents();
      return titles.indexOf(secondTitle) < titles.indexOf(firstTitle);
    }).toBe(true);

    await page.reload();
    await expect.poll(async () => {
      const titles = await firstColumn.locator("article h4").allTextContents();
      return titles.indexOf(secondTitle) < titles.indexOf(firstTitle);
    }).toBe(true);
  });
});
