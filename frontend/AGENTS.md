# Frontend guidance

## Existing application

This directory contains the working frontend-only Kanban demo. It uses Next.js 16 with the App Router, React 19, TypeScript, Tailwind CSS 4, and `dnd-kit`. The current board state is held only in React memory and resets on reload.

The app currently renders one board with five fixed columns. A user can rename columns, create and remove cards, and drag cards within or between columns. Card editing, authentication, persistence, backend calls, and AI chat have not been implemented yet.

## Structure

- `src/app/` contains the root layout, page, and global theme styles.
- `src/components/` contains the board, column, card, drag preview, and new-card form components.
- `src/lib/kanban.ts` contains the frontend board types, demo data, ID creation, and pure card-movement logic.
- `src/**/*.test.ts(x)` contains Vitest and Testing Library unit/component tests.
- `tests/` contains Playwright browser tests.
- `public/` contains static assets.

## Commands

Run these from `frontend/`:

- `npm run dev` starts the local Next.js development server.
- `npm run lint` runs ESLint.
- `npm run test:unit` runs Vitest once.
- `npm run test:e2e` runs Playwright.
- `npm run test:all` runs unit and browser tests.
- `npm run build` creates the production build; this will later become a static export served by FastAPI.

## Conventions

- Preserve the existing project color variables in `src/app/globals.css` and the focused single-board visual design.
- Keep the five columns fixed: they may be renamed but must not be added or removed.
- Prefer small typed components and pure state helpers over added abstractions or state-management libraries.
- Keep backend communication in a small typed API module rather than scattering `fetch` calls through components.
- Treat the backend response as canonical once persistence is introduced.
- Maintain accessible labels, keyboard operation, visible focus states, and stable `data-testid` values needed for drag-and-drop browser tests.
- Add or update Vitest tests for component and state behavior, and Playwright tests for user-visible workflows.
- Do not place secrets or `OPENROUTER_API_KEY` in frontend code, Next.js public environment variables, logs, or build output.
- Do not commit `.next/`, `out/`, `test-results/`, Playwright reports, coverage output, or dependency directories.
