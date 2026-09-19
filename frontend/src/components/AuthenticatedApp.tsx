"use client";

import { useEffect, useState } from "react";
import { KanbanBoard } from "@/components/KanbanBoard";
import { LoginForm } from "@/components/LoginForm";
import { getCurrentUser, logout, type User } from "@/lib/api";

export const AuthenticatedApp = () => {
  const [user, setUser] = useState<User | null>(null);
  const [isCheckingSession, setIsCheckingSession] = useState(true);
  const [sessionError, setSessionError] = useState("");
  const [isLoggingOut, setIsLoggingOut] = useState(false);

  const checkSession = async () => {
    setIsCheckingSession(true);
    setSessionError("");
    try {
      setUser(await getCurrentUser());
    } catch (error) {
      setSessionError(
        error instanceof Error ? error.message : "Unable to check your session"
      );
    } finally {
      setIsCheckingSession(false);
    }
  };

  useEffect(() => {
    let isActive = true;
    void getCurrentUser()
      .then((currentUser) => {
        if (isActive) setUser(currentUser);
      })
      .catch((error) => {
        if (isActive) {
          setSessionError(
            error instanceof Error
              ? error.message
              : "Unable to check your session"
          );
        }
      })
      .finally(() => {
        if (isActive) setIsCheckingSession(false);
      });
    return () => {
      isActive = false;
    };
  }, []);

  const handleLogout = async () => {
    setIsLoggingOut(true);
    try {
      await logout();
      setUser(null);
    } finally {
      setIsLoggingOut(false);
    }
  };

  if (isCheckingSession) {
    return (
      <main className="flex min-h-screen items-center justify-center text-sm font-semibold uppercase tracking-[0.2em] text-[var(--gray-text)]">
        Checking session...
      </main>
    );
  }

  if (sessionError) {
    return (
      <main className="flex min-h-screen flex-col items-center justify-center gap-4 px-6 text-center">
        <p className="text-[var(--navy-dark)]" role="alert">
          {sessionError}
        </p>
        <button
          className="rounded-full bg-[var(--secondary-purple)] px-5 py-3 text-sm font-semibold text-white"
          onClick={() => void checkSession()}
          type="button"
        >
          Try again
        </button>
      </main>
    );
  }

  if (!user) {
    return <LoginForm onLogin={setUser} />;
  }

  return (
    <div className="relative">
      <div className="absolute right-6 top-4 z-10 flex items-center gap-3 rounded-full border border-[var(--stroke)] bg-white/90 px-4 py-2 text-xs shadow-sm backdrop-blur">
        <span className="font-semibold text-[var(--gray-text)]">
          Signed in as {user.username}
        </span>
        <button
          className="font-semibold text-[var(--secondary-purple)] hover:underline disabled:opacity-60"
          disabled={isLoggingOut}
          onClick={() => void handleLogout()}
          type="button"
        >
          {isLoggingOut ? "Signing out..." : "Log out"}
        </button>
      </div>
      <KanbanBoard />
    </div>
  );
};
