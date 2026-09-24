# Frontend guidance

## Existing application

This directory contains the Kanban frontend. It uses Next.js 16 with the App Router, React 19, TypeScript, Tailwind CSS 4, and `dnd-kit`. It is configured as a static export that FastAPI serves in the production container. The current board state is held only in React memory and resets on reload.

The app requires the MVP login before rendering one board with five fixed columns. A user can log out, rename columns, create, edit, move, and remove cards, and use the AI assistant sidebar for the current board. Board data is persisted through the backend API; chat history remains in browser memory for the active session.

## Structure

- `src/app/` contains the root layout, page, and global theme styles.
- `src/components/` contains the board, column, card, drag preview, and new-card form components.
- `src/lib/kanban.ts` contains the frontend board types, demo data, ID creation, and pure card-movement logic.
- `src/lib/api.ts` contains same-origin authentication API calls.
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
- `npm run build` creates the static production export in `out/` for FastAPI to serve.

## Conventions

- Preserve the existing project color variables in `src/app/globals.css` and the focused single-board visual design.
- Keep the five columns fixed: they may be renamed but must not be added or removed.
- Prefer small typed components and pure state helpers over added abstractions or state-management libraries.
- Keep backend communication in a small typed API module rather than scattering `fetch` calls through components.
- Treat the backend response as canonical once persistence is introduced.
- Keep authentication cookies server-managed; frontend code should only request the current user and never read session tokens.
- Maintain accessible labels, keyboard operation, visible focus states, and stable `data-testid` values needed for drag-and-drop browser tests.
- Add or update Vitest tests for component and state behavior, and Playwright tests for user-visible workflows.
- Do not place secrets or `OPENROUTER_API_KEY` in frontend code, Next.js public environment variables, logs, or build output.
- Do not commit `.next/`, `out/`, `test-results/`, Playwright reports, coverage output, or dependency directories.

<!-- BEGIN:nextjs-agent-rules -->

# This is NOT the Next.js you know

This version has breaking changes — APIs, conventions, and file structure may all differ from your training data. Read the relevant guide in `node_modules/next/dist/docs/` (resolved from this file's directory; in monorepos the `next` package may not be visible from the repo root) before writing any code. Heed deprecation notices.

This block is written and re-added by `next dev` — verify at `node_modules/next/dist/server/lib/generate-agent-files.js`. Removing it from a diff only re-creates the uncommitted change; committing it with your work keeps the tree clean.

<!-- END:nextjs-agent-rules -->
