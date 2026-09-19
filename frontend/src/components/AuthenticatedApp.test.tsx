import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { AuthenticatedApp } from "@/components/AuthenticatedApp";
import { getCurrentUser, login, logout } from "@/lib/api";

vi.mock("@/lib/api", () => ({
  getCurrentUser: vi.fn(),
  login: vi.fn(),
  logout: vi.fn(),
}));

const mockedGetCurrentUser = vi.mocked(getCurrentUser);
const mockedLogin = vi.mocked(login);
const mockedLogout = vi.mocked(logout);

describe("AuthenticatedApp", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("shows the login form when there is no session", async () => {
    mockedGetCurrentUser.mockResolvedValue(null);

    render(<AuthenticatedApp />);

    expect(await screen.findByRole("heading", { name: "Sign in" })).toBeVisible();
    expect(screen.queryByText("Kanban Studio")).not.toBeInTheDocument();
  });

  it("shows an invalid credential error", async () => {
    mockedGetCurrentUser.mockResolvedValue(null);
    mockedLogin.mockRejectedValue(new Error("Invalid username or password"));
    render(<AuthenticatedApp />);

    await userEvent.type(await screen.findByLabelText("Username"), "wrong");
    await userEvent.type(screen.getByLabelText("Password"), "wrong");
    await userEvent.click(screen.getByRole("button", { name: "Sign in" }));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Invalid username or password"
    );
  });

  it("shows the board for an existing session", async () => {
    mockedGetCurrentUser.mockResolvedValue({ username: "user" });

    render(<AuthenticatedApp />);

    expect(await screen.findByText("Kanban Studio")).toBeVisible();
    expect(screen.getByText("Signed in as user")).toBeVisible();
  });

  it("signs in and logs out", async () => {
    mockedGetCurrentUser.mockResolvedValue(null);
    mockedLogin.mockResolvedValue({ username: "user" });
    mockedLogout.mockResolvedValue({ message: "Logged out" });
    render(<AuthenticatedApp />);

    await userEvent.type(await screen.findByLabelText("Username"), "user");
    await userEvent.type(screen.getByLabelText("Password"), "password");
    await userEvent.click(screen.getByRole("button", { name: "Sign in" }));
    expect(await screen.findByText("Kanban Studio")).toBeVisible();

    await userEvent.click(screen.getByRole("button", { name: "Log out" }));
    expect(await screen.findByRole("heading", { name: "Sign in" })).toBeVisible();
  });
});
