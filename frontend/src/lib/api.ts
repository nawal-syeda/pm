export type User = {
  username: string;
};

export type BoardCard = {
  id: string;
  title: string;
  details: string;
  position: number;
};

export type BoardColumn = {
  id: string;
  title: string;
  position: number;
  cards: BoardCard[];
};

export type Board = {
  id: string;
  name: string;
  columns: BoardColumn[];
  updated_at: string;
};

export type AIChatMessage = {
  role: "user" | "assistant";
  content: string;
};

export type AIChatResponse = {
  assistant_message: string;
  board_changed: boolean;
  board: Board | null;
};

const request = async <T>(path: string, options?: RequestInit): Promise<T> => {
  const response = await fetch(path, {
    ...options,
    credentials: "same-origin",
    headers: {
      "Content-Type": "application/json",
      ...options?.headers,
    },
  });

  if (!response.ok) {
    const body = (await response.json().catch(() => null)) as {
      detail?: string;
    } | null;
    throw new Error(body?.detail ?? "Request failed");
  }

  return response.json() as Promise<T>;
};

export const getCurrentUser = async (): Promise<User | null> => {
  const response = await fetch("/api/auth/session", {
    credentials: "same-origin",
  });
  if (response.status === 401) {
    return null;
  }
  if (!response.ok) {
    throw new Error("Unable to check your session");
  }
  return response.json() as Promise<User>;
};

export const login = (username: string, password: string) =>
  request<User>("/api/auth/login", {
    method: "POST",
    body: JSON.stringify({ username, password }),
  });

export const logout = () =>
  request<{ message: string }>("/api/auth/logout", { method: "POST" });

export const getBoard = () => request<Board>("/api/board");

export const renameColumn = (columnId: string, title: string) =>
  request<Board>(`/api/board/columns/${columnId}`, {
    method: "PATCH",
    body: JSON.stringify({ title }),
  });

export const createCard = (columnId: string, title: string, details: string) =>
  request<Board>(`/api/board/columns/${columnId}/cards`, {
    method: "POST",
    body: JSON.stringify({ title, details }),
  });

export const updateCard = (
  cardId: string,
  changes: { title?: string; details?: string }
) =>
  request<Board>(`/api/board/cards/${cardId}`, {
    method: "PATCH",
    body: JSON.stringify(changes),
  });

export const moveCard = (cardId: string, columnId: string, position: number) =>
  request<Board>(`/api/board/cards/${cardId}/move`, {
    method: "POST",
    body: JSON.stringify({ column_id: columnId, position }),
  });

export const deleteCard = (cardId: string) =>
  request<Board>(`/api/board/cards/${cardId}`, { method: "DELETE" });

export const aiChat = (message: string, history: AIChatMessage[]) =>
  request<AIChatResponse>("/api/ai/chat", {
    method: "POST",
    body: JSON.stringify({ message, history }),
  });

export const aiChatStream = async (
  message: string,
  history: AIChatMessage[],
  onDelta: (delta: string) => void
): Promise<AIChatResponse> => {
  const response = await fetch("/api/ai/chat/stream", {
    method: "POST",
    credentials: "same-origin",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message, history }),
  });
  if (!response.ok) {
    const body = (await response.json().catch(() => null)) as { detail?: string } | null;
    throw new Error(body?.detail ?? "Request failed");
  }
  if (!response.body) throw new Error("Streaming is not available in this browser");

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let result: AIChatResponse | null = null;

  const processEvent = (event: string) => {
    const data = event
      .split("\n")
      .filter((line) => line.startsWith("data:"))
      .map((line) => line.slice(5).trim())
      .join("\n");
    if (!data) return;
    const payload = JSON.parse(data) as {
      type: "delta" | "done" | "error";
      content?: string;
      detail?: string;
      assistant_message?: string;
      board_changed?: boolean;
      board?: Board | null;
    };
    if (payload.type === "delta") onDelta(payload.content ?? "");
    if (payload.type === "error") throw new Error(payload.detail ?? "AI request failed");
    if (payload.type === "done") {
      result = {
        assistant_message: payload.assistant_message ?? "",
        board_changed: payload.board_changed ?? false,
        board: payload.board ?? null,
      };
    }
  };

  while (true) {
    const chunk = await reader.read();
    buffer += decoder.decode(chunk.value ?? new Uint8Array(), { stream: !chunk.done });
    const events = buffer.split("\n\n");
    buffer = events.pop() ?? "";
    events.forEach(processEvent);
    if (chunk.done) break;
  }
  if (buffer.trim()) processEvent(buffer);
  if (!result) throw new Error("The AI stream ended without a response");
  return result;
};
