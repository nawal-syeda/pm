import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { AIChat } from "@/components/AIChat";
import { aiChatStream } from "@/lib/api";

vi.mock("@/lib/api", () => ({
  aiChatStream: vi.fn(),
}));

const mockedAIChat = vi.mocked(aiChatStream);

describe("AIChat", () => {
  beforeEach(() => vi.clearAllMocks());

  it("sends a message and renders the assistant reply", async () => {
    mockedAIChat.mockImplementation(async (_message, _history, onDelta) => {
      onDelta("Your board is ");
      onDelta("ready.");
      return { assistant_message: "Your board is ready.", board_changed: false, board: null };
    });
    render(<AIChat onBoardChanged={vi.fn()} />);

    const input = screen.getByLabelText("Message the AI assistant");
    await userEvent.type(input, "What is on my board?");
    await userEvent.click(screen.getByRole("button", { name: "Send message" }));

    expect(await screen.findByText("Your board is ready.")).toBeVisible();
    expect(mockedAIChat).toHaveBeenCalledWith("What is on my board?", [], expect.any(Function));
  });

  it("shows pending state and prevents duplicate submissions", async () => {
    let resolve: ((value: Awaited<ReturnType<typeof aiChatStream>>) => void) | undefined;
    mockedAIChat.mockImplementation(
      () => new Promise((done) => {
        resolve = done;
      })
    );
    render(<AIChat onBoardChanged={vi.fn()} />);
    await userEvent.type(screen.getByLabelText("Message the AI assistant"), "Wait");
    await userEvent.click(screen.getByRole("button", { name: "Send message" }));

    expect(screen.getByRole("status")).toHaveTextContent("Assistant is thinking");
    expect(screen.getByRole("button", { name: "Sending..." })).toBeDisabled();
    resolve?.({ assistant_message: "Done", board_changed: false, board: null });
    await screen.findByText("Done");
  });

  it("shows an error and retries the failed message", async () => {
    mockedAIChat
      .mockRejectedValueOnce(new Error("Temporary AI failure"))
      .mockResolvedValueOnce({ assistant_message: "Recovered", board_changed: false, board: null });
    render(<AIChat onBoardChanged={vi.fn()} />);
    await userEvent.type(screen.getByLabelText("Message the AI assistant"), "Try this");
    await userEvent.click(screen.getByRole("button", { name: "Send message" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Temporary AI failure");
    await userEvent.click(screen.getByRole("button", { name: "Retry" }));
    expect(await screen.findByText("Recovered")).toBeVisible();
    expect(mockedAIChat).toHaveBeenCalledTimes(2);
  });

  it("notifies the board when the assistant changes it", async () => {
    const onBoardChanged = vi.fn();
    mockedAIChat.mockResolvedValue({
      assistant_message: "Created a card.",
      board_changed: true,
      board: { id: "board-1", name: "My Project", updated_at: "now", columns: [] },
    });
    render(<AIChat onBoardChanged={onBoardChanged} />);
    await userEvent.type(screen.getByLabelText("Message the AI assistant"), "Create a card");
    await userEvent.click(screen.getByRole("button", { name: "Send message" }));
    await waitFor(() => expect(onBoardChanged).toHaveBeenCalledTimes(1));
  });
});
