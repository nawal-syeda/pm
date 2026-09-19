export type User = {
  username: string;
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
