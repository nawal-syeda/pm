import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { KanbanBoard } from "@/components/KanbanBoard";
import { getBoard, createCard, deleteCard, renameColumn, updateCard } from "@/lib/api";
import { initialData } from "@/lib/kanban";

vi.mock("@/lib/api", () => ({
  getBoard: vi.fn(),
  createCard: vi.fn(),
  deleteCard: vi.fn(),
  renameColumn: vi.fn(),
  updateCard: vi.fn(),
  moveCard: vi.fn(),
}));

const apiBoard = () => ({
  id: "board-1",
  name: "Product Roadmap",
  updated_at: "2026-01-01T00:00:00Z",
  columns: initialData.columns.map((column, position) => ({
    id: column.id,
    title: column.title,
    position,
    cards: column.cardIds.map((id, cardPosition) => ({
      ...initialData.cards[id],
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
