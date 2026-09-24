# Project Management MVP implementation plan

## Scope and guiding decisions

- The application runs locally as one Docker container.
- FastAPI serves both the API and the statically exported Next.js frontend from the same origin.
- The only MVP credentials are `user` / `password`. Authentication uses a server-managed session cookie; passwords are never returned to the browser.
- SQLite stores users, the single board owned by each user, its fixed set of renameable columns, and cards. The schema remains capable of holding multiple users.
- The browser owns the current AI conversation history for the MVP and sends it with each AI request. Chat history is not persisted across page reloads.
- OpenRouter is called only by the backend with `nvidia/nemotron-3.5-lightning`, pinned to DeepInfra; the API key is never exposed to the frontend.
- AI board changes use the same validated backend operations as direct UI changes. The server remains the source of truth, and the frontend reloads the board after an AI update.
- Each part is completed and verified before starting the next. Material design decisions that require approval have an explicit approval gate.

## Definition of done for every implementation part

- [x] The scoped implementation tasks are complete.
- [x] New and existing relevant automated tests pass.
- [x] Linting and production builds pass for affected code.
- [x] Documentation reflects commands, configuration, and deliberate limitations.
- [x] No secrets, generated build output, local database files, or test artifacts are committed.

## Part 1: Plan

### Tasks

- [x] Review the root project instructions and the existing frontend.
- [x] Expand the high-level plan into ordered implementation checklists.
- [x] Define tests and success criteria for every part.
- [x] Record the MVP boundaries and major cross-cutting decisions.
- [x] Add `frontend/AGENTS.md` describing the existing frontend and its conventions.
- [x] Obtain user approval for this plan before beginning Part 2.

### Tests and review

- [x] Confirm every business requirement is assigned to at least one implementation part.
- [x] Confirm Docker, FastAPI, static Next.js hosting, SQLite, OpenRouter, authentication, scripts, and AI board updates are covered.
- [x] Confirm each implementation part includes objective completion criteria.

### Success criteria

- The plan can be executed sequentially without inventing missing architectural decisions.
- The user explicitly approves the plan before implementation begins.

## Part 2: Scaffolding

### Tasks

- [x] Create a minimal FastAPI application under `backend/` with a health endpoint and an example API endpoint.
- [x] Add Python project metadata and lock dependencies with `uv`.
- [x] Add a placeholder static page served by FastAPI at `/` that calls the example API endpoint.
- [x] Create a production Dockerfile that installs Python dependencies with `uv` and runs the FastAPI application.
- [x] Add `.dockerignore` entries for dependencies, build output, test artifacts, local databases, and secrets.
- [x] Add start and stop scripts for Windows, macOS, and Linux under `scripts/`, using one consistent container name and port.
- [x] Update the backend and scripts guidance files to describe their real contents and commands.
- [x] Add minimal root documentation for prerequisites, environment setup, starting, stopping, and testing.

### Tests

- [x] Backend unit test: the health and example API endpoints return their documented status and payload.
- [x] Container integration test: the Docker image builds and starts without manual intervention.
- [x] Runtime smoke test: `/` serves HTML and the page can successfully call the example API endpoint.
- [x] Script smoke tests: each script is syntax-valid; run the script native to the current platform end to end.

### Success criteria

- A fresh local checkout with Docker and `.env` can build and start one container.
- Visiting `/` displays the placeholder page and a successful response from FastAPI.
- Stop scripts remove or stop only the project container and are safe to rerun.

## Part 3: Add the frontend

### Tasks

- [x] Configure Next.js for static export and ensure it does not require a Node.js runtime.
- [x] Extend the Docker build with a frontend build stage and copy the static export into the runtime image.
- [x] Replace the placeholder page with the existing Kanban frontend at `/` while preserving its current design and behavior.
- [x] Configure FastAPI static-file hosting with an SPA-compatible fallback that does not shadow `/api` routes.
- [x] Keep frontend API URLs same-origin and configurable only if tests require it.
- [x] Add production-loading and static-asset checks.

### Tests

- [x] Frontend unit tests cover rendering, column rename, card creation/removal, and card reorder/move logic.
- [x] Playwright covers board load, card creation, column rename, removal, and drag-and-drop between columns.
- [x] Production build test runs lint, Vitest, static export, and backend tests.
- [x] Container integration test verifies `/`, Next.js assets, and `/api` are all served by FastAPI.

### Success criteria

- The current five-column demo works at `/` from the production container.
- Refreshing any supported frontend route returns the frontend rather than a server 404.
- No Next.js development server or Node.js process is needed at runtime.

## Part 4: Add the MVP sign-in experience

### Tasks

- [x] Add backend login, logout, and current-session endpoints.
- [x] Validate only the exact MVP credentials `user` / `password`.
- [x] Store an opaque session identifier in an `HttpOnly`, `SameSite=Lax` cookie; set `Secure` only when served over HTTPS.
- [x] Keep session state in process for this local single-instance MVP and document that restarting the container signs users out.
- [x] Add a frontend login screen, authenticated loading state, logout control, and clear invalid-credential feedback.
- [x] Require authentication for Kanban and future AI API routes.

### Tests

- [x] Backend tests cover valid login, invalid login, current session, logout, and protected-route rejection.
- [x] Frontend unit tests cover form submission, validation feedback, authenticated rendering, and logout.
- [x] Playwright covers redirect/display behavior for a signed-out user, successful login, failed login, refresh with a valid session, and logout.

### Success criteria

- A signed-out visitor sees only the login experience.
- `user` / `password` opens the board; incorrect credentials do not.
- Protected APIs consistently return `401` without a valid session.
- Logout invalidates the session and returns the UI to sign-in.

## Part 5: Database modeling

### Tasks

- [x] Propose the normalized SQLite schema in a JSON document under `docs/`.
- [x] Model users, one board per user, fixed ordered columns, ordered cards, ownership, timestamps, primary keys, foreign keys, and uniqueness constraints.
- [x] Document initialization, transactions, foreign-key enforcement, ordering behavior, and the local database-file location.
- [x] Define the seed behavior for the MVP user and initial board, including idempotency.
- [x] Define the public board JSON shape separately from database rows.
- [x] Review the schema against direct UI edits and atomic multi-card AI updates.
- [x] Obtain user approval for the schema before beginning Part 6.

### Tests and review

- [x] Validate that the schema JSON is syntactically valid.
- [x] Walk through create, read, rename, edit, move, reorder, delete, and multi-operation AI update cases.
- [x] Confirm ownership constraints prevent one user from accessing another user's board.
- [x] Confirm deleting a parent cannot leave orphaned rows.

### Success criteria

- [x] The documented model supports multiple users while enforcing one board per user for the MVP.
- [x] Column and card order can be persisted without ambiguous positions.
- The user explicitly approves the schema and database approach.

## Part 6: Backend board API

### Tasks

- [x] Implement SQLite connection and schema initialization on application startup.
- [x] Create the database and idempotently seed the MVP user and board when absent.
- [x] Add authenticated routes to fetch the current user's board.
- [x] Add authenticated routes to rename columns and create, edit, move/reorder, and delete cards.
- [x] Validate request bodies and resource ownership with typed Pydantic models.
- [x] Make reorder operations and future multi-operation changes transactional.
- [x] Return a consistent public board representation and appropriate `400`, `401`, `404`, and `422` responses.

### Tests

- [x] Unit tests cover schema initialization and idempotent seeding against a temporary database.
- [x] API tests cover every board operation and response shape.
- [x] Tests cover ordering within a column and moves across columns, including empty columns.
- [x] Tests cover invalid identifiers, invalid payloads, missing authentication, and ownership isolation.
- [x] Transaction behavior is covered by the atomic connection boundary and mutation tests.

### Success criteria

- A missing database is created automatically and contains one usable seeded board for the MVP user.
- Every supported Kanban mutation persists within the initialized database.
- Invalid or unauthorized operations cannot partially mutate the board.

## Part 7: Connect the frontend and backend

### Tasks

- [x] Replace `initialData` as the runtime source of truth with the authenticated board API.
- [x] Add a small typed API client for session and board operations.
- [x] Show intentional loading, empty, and error states.
- [x] Persist column rename and card create, edit, move/reorder, and delete actions.
- [x] Add the missing card-editing UI required by the business requirements.
- [x] Reconcile failed mutations by restoring/refetching server state and showing a concise error.
- [x] Keep drag-and-drop responsive while ensuring the final displayed order matches the server.

### Tests

- [x] Frontend unit tests mock the API for initial load and board mutations, including card editing.
- [x] Backend integration tests execute realistic sequences of dependent board operations.
- [x] Playwright covers login plus create, edit, rename, move, reorder, delete, reload, and persistence.
- [x] Container end-to-end test confirms data persists across a container restart when its database volume is retained.

### Success criteria

- All visible board changes are saved in SQLite and remain after reload.
- The frontend does not silently diverge from backend state after an API error.
- A user can rename columns and create, edit, move, reorder, and delete cards end to end.

## Part 8: Verify AI connectivity

### Tasks

- [x] Add backend OpenRouter configuration using `OPENROUTER_API_KEY` from the environment.
- [x] Add a minimal OpenRouter client targeting `nvidia/nemotron-3.5-lightning` through DeepInfra.
- [x] Keep the API key server-side and ensure logs and error responses never expose it.
- [x] Add an authenticated diagnostic endpoint or script that asks `2+2` and returns the model response.
- [x] Document how to run the live connectivity check separately from the deterministic test suite.

### Tests

- [x] Unit tests mock OpenRouter success, authentication failure, rate limiting, timeout, and malformed upstream responses.
- [x] Configuration test gives a clear request-time error when the key is missing.
- [x] Run the explicit live `2+2` connectivity test with the configured key and record only pass/fail, not the secret.

### Success criteria

- The backend receives a valid answer to `2+2` from the required model through OpenRouter.
- Routine automated tests do not consume credits or require network access.
- Upstream failures produce safe, understandable API errors.

## Part 9: Structured AI board operations

### Tasks

- [x] Define a minimal structured response schema containing assistant text and an optional ordered list of board operations.
- [x] Support only the existing Kanban actions: rename a column and create, edit, move/reorder, or delete cards.
- [x] Send the current canonical board JSON, the user's message, and browser-provided conversation history to the model.
- [x] Request OpenRouter Structured Outputs using the defined JSON schema.
- [x] Validate the model response before applying any operation.
- [x] Apply all AI-requested operations in one database transaction and reject the whole update if any operation is invalid.
- [x] Return the assistant message, whether the board changed, and the canonical resulting board when changed.
- [x] Constrain prompt instructions so the model cannot invent unsupported actions or cross user boundaries.

### Tests

- [x] Unit tests cover valid text-only and board-changing structured responses.
- [x] Tests cover every supported AI operation individually and representative multi-operation requests.
- [x] Tests cover invalid JSON, schema violations, unknown IDs, unsupported operations, and upstream errors.
- [x] Atomicity tests prove one invalid operation prevents all operations in that response.
- [x] Prompt/request construction test confirms the current board and conversation history are included without the API key.

### Success criteria

- Natural-language requests can produce validated, persistent board changes.
- The model cannot mutate the database outside the explicit operation schema.
- The API always returns a canonical board after a successful AI mutation.

## Part 10: AI chat sidebar

### Tasks

- [x] Add a responsive, accessible chat sidebar consistent with the project color scheme.
- [x] Add message history, input submission, pending state, safe error display, and retry behavior.
- [x] Send the current conversation history with each message while keeping it only for the active browser session.
- [x] Render assistant text and refresh or replace board state automatically when the response reports a change.
- [x] Prevent duplicate submissions while a request is pending.
- [x] Preserve usable Kanban drag-and-drop and chat layouts at desktop and narrow viewport sizes.
- [x] Keep chat behavior focused on the single current board; do not add unrelated assistant features.

### Tests

- [x] Frontend unit tests cover text-only replies, pending state, errors, retry, and board-changing replies.
- [x] Integration tests mock deterministic structured AI responses and verify automatic board refresh.
- [x] Playwright covers the assistant sidebar flow and board persistence after reload.
- [x] Accessibility checks cover labeled controls, keyboard submission, focus behavior, and readable status announcements.
- [x] Run one opt-in live end-to-end AI smoke test after deterministic tests pass.

### Success criteria

- The signed-in user can hold a multi-turn AI conversation in the sidebar.
- Valid AI-requested board changes appear without a manual page refresh and persist in SQLite.
- Failures leave the existing board intact and allow the user to retry.
- The complete application builds, starts, and passes its deterministic test suite in the production container.

## Final MVP acceptance checklist

- [x] A fresh database is created automatically.
- [x] The user can sign in with `user` / `password` and sign out.
- [x] Each signed-in user is limited to their own single board.
- [x] The five fixed columns can be renamed but not added or removed.
- [x] Cards can be created, edited, moved, reordered, and deleted, with changes persisted.
- [x] The AI chat can answer questions and atomically apply one or more supported board changes.
- [x] FastAPI serves the static Next.js application and all APIs from one Docker container.
- [x] Start and stop scripts are present for Windows, macOS, and Linux.
- [x] Deterministic unit, integration, and end-to-end tests pass; live AI testing remains explicitly opt-in.
