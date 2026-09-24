"use client";

import { useState, type FormEvent } from "react";
import { aiChatStream, type AIChatMessage } from "@/lib/api";

type AIChatProps = {
  onBoardChanged: () => void;
};

type FailedMessage = {
  message: string;
  history: AIChatMessage[];
};

export const AIChat = ({ onBoardChanged }: AIChatProps) => {
  const [messages, setMessages] = useState<AIChatMessage[]>([]);
  const [draft, setDraft] = useState("");
  const [isPending, setIsPending] = useState(false);
  const [error, setError] = useState("");
  const [failedMessage, setFailedMessage] = useState<FailedMessage | null>(null);

  const sendMessage = async (
    message: string,
    history: AIChatMessage[],
    showUserMessage: boolean
  ) => {
    setIsPending(true);
    setError("");
    setFailedMessage(null);
    if (showUserMessage) {
      setMessages((current) => [
        ...current,
        { role: "user", content: message },
        { role: "assistant", content: "" },
      ]);
    } else {
      setMessages((current) => {
        const next = [...current];
        if (next.at(-1)?.role === "assistant") next[next.length - 1] = { role: "assistant", content: "" };
        return next;
      });
    }
    try {
      const response = await aiChatStream(message, history, (delta) => {
        setMessages((current) => {
          const next = [...current];
          const last = next.at(-1);
          if (last?.role === "assistant") {
            next[next.length - 1] = { role: "assistant", content: last.content + delta };
          }
          return next;
        });
      });
      setMessages((current) => {
        const next = [...current];
        if (next.at(-1)?.role === "assistant") next[next.length - 1] = { role: "assistant", content: response.assistant_message };
        return next;
      });
      if (response.board_changed) onBoardChanged();
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : "Unable to contact the AI assistant"
      );
      setFailedMessage({ message, history });
    } finally {
      setIsPending(false);
    }
  };

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const message = draft.trim();
    if (!message || isPending) return;
    setDraft("");
    void sendMessage(message, messages, true);
  };

  const handleRetry = () => {
    if (!failedMessage || isPending) return;
    void sendMessage(failedMessage.message, failedMessage.history, false);
  };

  return (
    <aside
      aria-label="AI assistant"
      className="relative mt-8 flex min-h-[520px] w-full flex-col border border-[var(--stroke)] bg-white shadow-[var(--shadow)] lg:fixed lg:inset-y-0 lg:right-0 lg:z-20 lg:mt-0 lg:w-[380px] lg:max-w-[380px] lg:border-y-0 lg:border-r-0 lg:border-l lg:shadow-[-12px_0_32px_rgba(3,33,71,0.12)]"
    >
      <header className="border-b border-[var(--stroke)] bg-[var(--navy-dark)] px-5 py-5 text-white">
        <p className="text-xs font-semibold uppercase tracking-[0.3em] text-[var(--accent-yellow)]">
          Board assistant
        </p>
        <h2 className="mt-2 font-display text-2xl font-semibold">Ask your project</h2>
        <p className="mt-2 text-sm leading-5 text-white/70">
          Ask questions or request a board update. Changes are validated before they are saved.
        </p>
      </header>

      <div
        aria-live="polite"
        aria-label="Assistant conversation"
        className="flex-1 space-y-4 overflow-y-auto px-5 py-5"
      >
        {messages.length === 0 && (
          <p className="rounded-2xl border border-dashed border-[var(--stroke)] bg-[var(--surface)] px-4 py-4 text-sm leading-6 text-[var(--gray-text)]">
            Try “What is in progress?” or “Create a card in Backlog.”
          </p>
        )}
        {messages.map((message, index) => (
          <div
            className={message.role === "user" ? "flex justify-end" : "flex justify-start"}
            key={`${message.role}-${index}`}
          >
            <p
              className={
                message.role === "user"
                  ? "max-w-[90%] rounded-2xl rounded-br-sm bg-[var(--secondary-purple)] px-4 py-3 text-sm leading-5 text-white"
                  : "max-w-[90%] rounded-2xl rounded-bl-sm border border-[var(--stroke)] bg-[var(--surface)] px-4 py-3 text-sm leading-5 text-[var(--navy-dark)]"
              }
            >
              {message.content}
            </p>
          </div>
        ))}
        {isPending && (
          <p className="text-sm font-semibold text-[var(--gray-text)]" role="status">
            <span className="sr-only">Assistant is thinking</span>
            Thinking<span className="inline-block animate-bounce [animation-delay:-0.3s]">.</span><span className="inline-block animate-bounce [animation-delay:-0.15s]">.</span><span className="inline-block animate-bounce">.</span>
          </p>
        )}
        {error && (
          <div className="rounded-2xl bg-red-50 px-4 py-3 text-sm text-red-700" role="alert">
            <p>{error}</p>
            <button
              className="mt-2 font-semibold underline disabled:opacity-60"
              disabled={isPending}
              onClick={handleRetry}
              type="button"
            >
              Retry
            </button>
          </div>
        )}
      </div>

      <form className="border-t border-[var(--stroke)] p-4" onSubmit={handleSubmit}>
        <label className="sr-only" htmlFor="ai-message">
          Message the AI assistant
        </label>
        <textarea
          id="ai-message"
          className="w-full resize-none rounded-2xl border border-[var(--stroke)] px-4 py-3 text-sm text-[var(--navy-dark)] outline-none transition focus:border-[var(--primary-blue)]"
          disabled={isPending}
          onChange={(event) => setDraft(event.target.value)}
          placeholder="Ask about your board..."
          rows={3}
          value={draft}
        />
        <button
          className="mt-3 w-full rounded-full bg-[var(--secondary-purple)] px-4 py-3 text-sm font-semibold uppercase tracking-wide text-white transition hover:brightness-110 disabled:cursor-not-allowed disabled:opacity-60"
          disabled={isPending || !draft.trim()}
          type="submit"
        >
          {isPending ? "Sending..." : "Send message"}
        </button>
      </form>
    </aside>
  );
};
