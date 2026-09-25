import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { KanbanBoard } from "@/components/KanbanBoard";
import { getBoard, createCard, deleteCard, renameColumn, updateCard } from "@/lib/api";

vi.mock("@/lib/api", () => ({
  getBoard: vi.fn(),
  createCard: vi.fn(),
  deleteCard: vi.fn(),
  renameColumn: vi.fn(),
  updateCard: vi.fn(),
  moveCard: vi.fn(),
}));

const COLUMNS: [string, string, string[]][] = [
  ["col-backlog", "Backlog", ["card-1", "card-2"]],
  ["col-discovery", "Discovery", ["card-3"]],
  ["col-progress", "In Progress", ["card-4", "card-5"]],
  ["col-review", "Review", ["card-6"]],
  ["col-done", "Done", ["card-7", "card-8"]],
];

const CARD_TITLES: Record<string, string> = {
  "card-1": "Align roadmap themes",
  "card-2": "Gather customer signals",
  "card-3": "Prototype analytics view",
  "card-4": "Refine status language",
  "card-5": "Design card layout",
  "card-6": "QA micro-interactions",
  "card-7": "Ship marketing page",
  "card-8": "Close onboarding sprint",
};

const apiBoard = () => ({
  id: "board-1",
  name: "Product Roadmap",
  updated_at: "2026-01-01T00:00:00Z",
  columns: COLUMNS.map(([id, title, cardIds], position) => ({
    id,
    title,
    position,
    cards: cardIds.map((cardId, cardPosition) => ({
      id: cardId,
      title: CARD_TITLES[cardId],
      details: `Details for ${cardId}`,
      position: cardPosition,
    })),
  })),
});

describe("KanbanBoard", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(getBoard).mockResolvedValue(apiBoard());
    vi.mocked(createCard).mockResolvedValue(apiBoard());
    vi.mocked(deleteCard).mockResolvedValue(apiBoard());
    vi.mocked(renameColumn).mockResolvedValue(apiBoard());
    vi.mocked(updateCard).mockResolvedValue(apiBoard());
  });

  it("renders five columns", async () => {
    render(<KanbanBoard />);
    expect(await screen.findAllByTestId(/column-/i)).toHaveLength(5);
  });

  it("renames a column", async () => {
    render(<KanbanBoard />);
    const column = (await screen.findAllByTestId(/column-/i))[0];
    const input = within(column).getByLabelText("Column title");
    await userEvent.clear(input);
    await userEvent.type(input, "New Name");
    expect(input).toHaveValue("New Name");
    await userEvent.tab();
    expect(renameColumn).toHaveBeenCalledWith("col-backlog", "New Name");
  });

  it("does not rename a column when the field is only focused and blurred", async () => {
    render(<KanbanBoard />);
    const column = (await screen.findAllByTestId(/column-/i))[0];
    const input = within(column).getByLabelText("Column title");
    await userEvent.click(input);
    await userEvent.tab();
    expect(renameColumn).not.toHaveBeenCalled();
  });

  it("restores the column title when the field is blurred empty", async () => {
    render(<KanbanBoard />);
    const column = (await screen.findAllByTestId(/column-/i))[0];
    const input = within(column).getByLabelText("Column title");
    await userEvent.clear(input);
    await userEvent.tab();
    expect(renameColumn).not.toHaveBeenCalled();
    expect(input).toHaveValue("Backlog");
  });

  it("stops the card acting as a drag handle while it is being edited", async () => {
    render(<KanbanBoard />);
    const column = (await screen.findAllByTestId(/column-/i))[0];
    const card = within(column).getByTestId("card-card-1");
    expect(card).toHaveAttribute("role", "button");

    await userEvent.click(within(column).getByRole("button", { name: /edit align roadmap themes/i }));
    expect(within(column).getByTestId("card-card-1")).not.toHaveAttribute("role", "button");
  });

  it("adds and removes a card", async () => {
    render(<KanbanBoard />);
    const column = (await screen.findAllByTestId(/column-/i))[0];
    await userEvent.click(within(column).getByRole("button", { name: /add a card/i }));
    await userEvent.type(within(column).getByPlaceholderText(/card title/i), "New card");
    await userEvent.type(within(column).getByPlaceholderText(/details/i), "Notes");
    await userEvent.click(within(column).getByRole("button", { name: /add card/i }));
    expect(createCard).toHaveBeenCalledWith("col-backlog", "New card", "Notes");
  });

  it("edits a card", async () => {
    render(<KanbanBoard />);
    const column = (await screen.findAllByTestId(/column-/i))[0];
    await userEvent.click(within(column).getByRole("button", { name: /edit align roadmap themes/i }));
    const title = within(column).getByRole("textbox", { name: "Card title" });
    await userEvent.clear(title);
    await userEvent.type(title, "Updated card");
    await userEvent.click(within(column).getByRole("button", { name: "Save" }));
    await waitFor(() => expect(updateCard).toHaveBeenCalledWith("card-1", { title: "Updated card", details: expect.any(String) }));
  });
});
