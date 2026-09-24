"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import {
  DndContext,
  DragOverlay,
  PointerSensor,
  closestCorners,
  useSensor,
  useSensors,
  type DragEndEvent,
  type DragStartEvent,
} from "@dnd-kit/core";
import { KanbanColumn } from "@/components/KanbanColumn";
import { KanbanCardPreview } from "@/components/KanbanCardPreview";
import {
  createCard,
  deleteCard,
  getBoard,
  moveCard as moveCardRequest,
  renameColumn,
  updateCard,
} from "@/lib/api";
import { fromApiBoard, moveCard, type BoardData } from "@/lib/kanban";

type KanbanBoardProps = {
  refreshToken?: number;
};

export const KanbanBoard = ({ refreshToken = 0 }: KanbanBoardProps) => {
  const [board, setBoard] = useState<BoardData | null>(null);
  const [activeCardId, setActiveCardId] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState("");
  const [pendingAction, setPendingAction] = useState(false);

  const loadBoard = useCallback(async () => {
    setIsLoading(true);
    setError("");
    try {
      setBoard(fromApiBoard(await getBoard()));
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : "Unable to load board");
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    let active = true;
    getBoard()
      .then((response) => {
        if (active) setBoard(fromApiBoard(response));
      })
      .catch((loadError) => {
        if (active) setError(loadError instanceof Error ? loadError.message : "Unable to load board");
      })
      .finally(() => {
        if (active) setIsLoading(false);
      });
    return () => {
      active = false;
    };
  }, [refreshToken]);

  const applyMutation = async (mutation: () => Promise<BoardData>) => {
    setPendingAction(true);
    setError("");
    try {
      setBoard(await mutation());
    } catch (mutationError) {
      setError(mutationError instanceof Error ? mutationError.message : "Unable to save board change");
      await loadBoard();
    } finally {
      setPendingAction(false);
    }
  };

  const requestBoard = async (request: Promise<Awaited<ReturnType<typeof getBoard>>>) =>
    fromApiBoard(await request);

  const sensors = useSensors(useSensor(PointerSensor, { activationConstraint: { distance: 6 } }));
  const cardsById = useMemo(() => board?.cards ?? {}, [board?.cards]);

  const handleDragStart = (event: DragStartEvent) => setActiveCardId(event.active.id as string);

  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event;
    setActiveCardId(null);
    if (!over || !board || active.id === over.id) return;

    const targetColumn = board.columns.find(
      (column) => column.id === over.id || column.cardIds.includes(over.id as string)
    );
    if (!targetColumn) return;
    const position = targetColumn.id === over.id
      ? targetColumn.cardIds.length
      : targetColumn.cardIds.indexOf(over.id as string);
    const nextColumns = moveCard(board.columns, active.id as string, over.id as string);
    setBoard({ ...board, columns: nextColumns });
    void applyMutation(() => requestBoard(moveCardRequest(active.id as string, targetColumn.id, Math.max(0, position))));
  };

  const handleRenameColumn = (columnId: string, title: string) => {
    if (!title.trim()) return;
    void applyMutation(() => requestBoard(renameColumn(columnId, title.trim())));
  };

  const handleAddCard = (columnId: string, title: string, details: string) => {
    void applyMutation(() => requestBoard(createCard(columnId, title, details)));
  };

  const handleEditCard = (cardId: string, title: string, details: string) => {
    void applyMutation(() => requestBoard(updateCard(cardId, { title, details })));
  };

  const handleDeleteCard = (columnId: string, cardId: string) => {
    void applyMutation(() => requestBoard(deleteCard(cardId)));
  };

  if (isLoading || !board) {
    return (
      <main className="flex min-h-screen items-center justify-center text-sm font-semibold uppercase tracking-[0.2em] text-[var(--gray-text)]">
        {error || "Loading board..."}
      </main>
    );
  }

  const activeCard = activeCardId ? cardsById[activeCardId] : null;

  return (
    <div className="relative">
      <div className="pointer-events-none absolute left-0 top-0 h-[420px] w-[420px] -translate-x-1/3 -translate-y-1/3 rounded-full bg-[radial-gradient(circle,_rgba(32,157,215,0.25)_0%,_rgba(32,157,215,0.05)_55%,_transparent_70%)]" />
      <div className="pointer-events-none absolute bottom-0 right-0 h-[520px] w-[520px] translate-x-1/4 translate-y-1/4 rounded-full bg-[radial-gradient(circle,_rgba(117,57,145,0.18)_0%,_rgba(117,57,145,0.05)_55%,_transparent_75%)]" />
      <main className="relative mx-auto flex min-h-screen max-w-[1500px] flex-col gap-10 px-6 pb-16 pt-12">
        <header className="flex flex-col gap-6 rounded-[32px] border border-[var(--stroke)] bg-white/80 p-8 shadow-[var(--shadow)] backdrop-blur">
          <div className="flex flex-wrap items-start justify-between gap-6">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.35em] text-[var(--gray-text)]">Single Board Kanban</p>
              <h1 className="mt-3 font-display text-4xl font-semibold text-[var(--navy-dark)]">Kanban Studio</h1>
              <p className="mt-3 max-w-xl text-sm leading-6 text-[var(--gray-text)]">Keep momentum visible. Rename columns, drag cards between stages, and capture quick notes without getting buried in settings.</p>
            </div>
            <div className="rounded-2xl border border-[var(--stroke)] bg-[var(--surface)] px-5 py-4">
              <p className="text-xs font-semibold uppercase tracking-[0.25em] text-[var(--gray-text)]">Focus</p>
              <p className="mt-2 text-lg font-semibold text-[var(--primary-blue)]">One board. Five columns. Zero clutter.</p>
            </div>
          </div>
          {error && <p className="rounded-xl bg-red-50 px-4 py-3 text-sm font-medium text-red-700" role="alert">{error}</p>}
          <div className="flex flex-wrap items-center gap-4">
            {board.columns.map((column) => (
              <div key={column.id} className="flex items-center gap-2 rounded-full border border-[var(--stroke)] px-4 py-2 text-xs font-semibold uppercase tracking-[0.2em] text-[var(--navy-dark)]">
                <span className="h-2 w-2 rounded-full bg-[var(--accent-yellow)]" />
                {column.title}
              </div>
            ))}
          </div>
        </header>
        <DndContext id="kanban-board-dnd-context" sensors={sensors} collisionDetection={closestCorners} onDragStart={handleDragStart} onDragEnd={handleDragEnd}>
          <section className={pendingAction ? "grid gap-6 opacity-70 transition lg:grid-cols-5" : "grid gap-6 lg:grid-cols-5"}>
            {board.columns.map((column) => (
              <KanbanColumn key={column.id} column={column} cards={column.cardIds.map((cardId) => board.cards[cardId])} onRename={handleRenameColumn} onAddCard={handleAddCard} onDeleteCard={handleDeleteCard} onEditCard={handleEditCard} />
            ))}
          </section>
          <DragOverlay>{activeCard ? <div className="w-[260px]"><KanbanCardPreview card={activeCard} /></div> : null}</DragOverlay>
        </DndContext>
      </main>
    </div>
  );
};
