# Project Management MVP implementation plan

## Scope and guiding decisions

- The application runs locally as one Docker container.
- FastAPI serves both the API and the statically exported Next.js frontend from the same origin.
- The only MVP credentials are `user` / `password`. Authentication uses a server-managed session cookie; passwords are never returned to the browser.
- SQLite stores users, the single board owned by each user, its fixed set of renameable columns, and cards. The schema remains capable of holding multiple users.
- The browser owns the current AI conversation history for the MVP and sends it with each AI request. Chat history is not persisted across page reloads.
- OpenRouter is called only by the backend with `openai/gpt-oss-120b`; the API key is never exposed to the frontend.
- AI board changes use the same validated backend operations as direct UI changes. The server remains the source of truth, and the frontend reloads the board after an AI update.
- Each part is completed and verified before starting the next. Material design decisions that require approval have an explicit approval gate.

## Definition of done for every implementation part

- [ ] The scoped implementation tasks are complete.
- [ ] New and existing relevant automated tests pass.
- [ ] Linting and production builds pass for affected code.
- [ ] Documentation reflects commands, configuration, and deliberate limitations.
- [ ] No secrets, generated build output, local database files, or test artifacts are committed.

## Part 1: Plan

### Tasks

- [x] Review the root project instructions and the existing frontend.
- [x] Expand the high-level plan into ordered implementation checklists.
- [x] Define tests and success criteria for every part.
- [x] Record the MVP boundaries and major cross-cutting decisions.
- [x] Add `frontend/AGENTS.md` describing the existing frontend and its conventions.
- [ ] Obtain user approval for this plan before beginning Part 2.

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

- [ ] Configure Next.js for static export and ensure it does not require a Node.js runtime.
- [ ] Extend the Docker build with a frontend build stage and copy the static export into the runtime image.
- [ ] Replace the placeholder page with the existing Kanban frontend at `/` while preserving its current design and behavior.
- [ ] Configure FastAPI static-file hosting with an SPA-compatible fallback that does not shadow `/api` routes.
- [ ] Keep frontend API URLs same-origin and configurable only if tests require it.
- [ ] Add production-loading and static-asset checks.

### Tests

- [ ] Frontend unit tests cover rendering, column rename, card creation/removal, and card reorder/move logic.
- [ ] Playwright covers board load, card creation, column rename, removal, and drag-and-drop between columns.
- [ ] Production build test runs lint, Vitest, static export, and backend tests.
- [ ] Container integration test verifies `/`, Next.js assets, and `/api` are all served by FastAPI.

### Success criteria

- The current five-column demo works at `/` from the production container.
- Refreshing any supported frontend route returns the frontend rather than a server 404.
- No Next.js development server or Node.js process is needed at runtime.

## Part 4: Add the MVP sign-in experience

### Tasks

- [ ] Add backend login, logout, and current-session endpoints.
- [ ] Validate only the exact MVP credentials `user` / `password`.
- [ ] Store an opaque session identifier in an `HttpOnly`, `SameSite=Lax` cookie; set `Secure` only when served over HTTPS.
- [ ] Keep session state in process for this local single-instance MVP and document that restarting the container signs users out.
- [ ] Add a frontend login screen, authenticated loading state, logout control, and clear invalid-credential feedback.
- [ ] Require authentication for Kanban and future AI API routes.

### Tests

- [ ] Backend tests cover valid login, invalid login, current session, logout, and protected-route rejection.
- [ ] Frontend unit tests cover form submission, validation feedback, authenticated rendering, and logout.
- [ ] Playwright covers redirect/display behavior for a signed-out user, successful login, failed login, refresh with a valid session, and logout.

### Success criteria

- A signed-out visitor sees only the login experience.
- `user` / `password` opens the board; incorrect credentials do not.
- Protected APIs consistently return `401` without a valid session.
- Logout invalidates the session and returns the UI to sign-in.

## Part 5: Database modeling

### Tasks

- [ ] Propose the normalized SQLite schema in a JSON document under `docs/`.
- [ ] Model users, one board per user, fixed ordered columns, ordered cards, ownership, timestamps, primary keys, foreign keys, and uniqueness constraints.
- [ ] Document initialization, transactions, foreign-key enforcement, ordering behavior, and the local database-file location.
- [ ] Define the seed behavior for the MVP user and initial board, including idempotency.
- [ ] Define the public board JSON shape separately from database rows.
- [ ] Review the schema against direct UI edits and atomic multi-card AI updates.
- [ ] Obtain user approval for the schema before beginning Part 6.

### Tests and review

- [ ] Validate that the schema JSON is syntactically valid.
- [ ] Walk through create, read, rename, edit, move, reorder, delete, and multi-operation AI update cases.
- [ ] Confirm ownership constraints prevent one user from accessing another user's board.
- [ ] Confirm deleting a parent cannot leave orphaned rows.

### Success criteria

- The documented model supports multiple users while enforcing one board per user for the MVP.
- Column and card order can be persisted without ambiguous positions.
- The user explicitly approves the schema and database approach.

## Part 6: Backend board API

### Tasks

- [ ] Implement SQLite connection and schema initialization on application startup.
- [ ] Create the database and idempotently seed the MVP user and board when absent.
- [ ] Add authenticated routes to fetch the current user's board.
- [ ] Add authenticated routes to rename columns and create, edit, move/reorder, and delete cards.
- [ ] Validate request bodies and resource ownership with typed Pydantic models.
- [ ] Make reorder operations and future multi-operation changes transactional.
- [ ] Return a consistent public board representation and appropriate `400`, `401`, `404`, and `422` responses.

### Tests

- [ ] Unit tests cover schema initialization and idempotent seeding against a temporary database.
- [ ] API tests cover every board operation and response shape.
- [ ] Tests cover ordering within a column and moves across columns, including empty columns.
- [ ] Tests cover invalid identifiers, invalid payloads, missing authentication, and ownership isolation.
- [ ] Transaction test proves a failed multi-step update leaves the board unchanged.

### Success criteria

- A missing database is created automatically and contains one usable seeded board for the MVP user.
- Every supported Kanban mutation persists and survives application restart.
- Invalid or unauthorized operations cannot partially mutate the board.

## Part 7: Connect the frontend and backend

### Tasks

- [ ] Replace `initialData` as the runtime source of truth with the authenticated board API.
- [ ] Add a small typed API client for session and board operations.
- [ ] Show intentional loading, empty, and error states.
- [ ] Persist column rename and card create, edit, move/reorder, and delete actions.
- [ ] Add the missing card-editing UI required by the business requirements.
- [ ] Reconcile failed mutations by restoring/refetching server state and showing a concise error.
- [ ] Keep drag-and-drop responsive while ensuring the final displayed order matches the server.

### Tests

- [ ] Frontend unit tests mock the API for initial load, all mutations, and failure recovery.
- [ ] Backend integration tests execute realistic sequences of dependent board operations.
- [ ] Playwright covers login plus create, edit, rename, move, reorder, delete, reload, and persistence.
- [ ] Container end-to-end test confirms data persists across a container restart when its database volume is retained.

### Success criteria

- All visible board changes are saved in SQLite and remain after reload.
- The frontend does not silently diverge from backend state after an API error.
- A user can rename columns and create, edit, move, reorder, and delete cards end to end.

## Part 8: Verify AI connectivity

### Tasks

- [ ] Add backend OpenRouter configuration using `OPENROUTER_API_KEY` from the environment.
- [ ] Add a minimal OpenRouter client targeting `openai/gpt-oss-120b`.
- [ ] Keep the API key server-side and ensure logs and error responses never expose it.
- [ ] Add an authenticated diagnostic endpoint or script that asks `2+2` and returns the model response.
- [ ] Document how to run the live connectivity check separately from the deterministic test suite.

### Tests

- [ ] Unit tests mock OpenRouter success, authentication failure, rate limiting, timeout, and malformed upstream responses.
- [ ] Configuration test gives a clear startup or request-time error when the key is missing.
- [ ] Run the explicit live `2+2` connectivity test with the configured key and record only pass/fail, not the secret.

### Success criteria

- The backend receives a valid answer to `2+2` from the required model through OpenRouter.
- Routine automated tests do not consume credits or require network access.
- Upstream failures produce safe, understandable API errors.

## Part 9: Structured AI board operations

### Tasks

- [ ] Define a minimal structured response schema containing assistant text and an optional ordered list of board operations.
- [ ] Support only the existing Kanban actions: rename a column and create, edit, move/reorder, or delete cards.
- [ ] Send the current canonical board JSON, the user's message, and browser-provided conversation history to the model.
- [ ] Request OpenRouter Structured Outputs using the defined JSON schema.
- [ ] Validate the model response before applying any operation.
- [ ] Apply all AI-requested operations in one database transaction and reject the whole update if any operation is invalid.
- [ ] Return the assistant message, whether the board changed, and the canonical resulting board when changed.
- [ ] Constrain prompt instructions so the model cannot invent unsupported actions or cross user boundaries.

### Tests

- [ ] Unit tests cover valid text-only and board-changing structured responses.
- [ ] Tests cover every supported AI operation individually and representative multi-operation requests.
- [ ] Tests cover invalid JSON, schema violations, unknown IDs, unsupported operations, and upstream errors.
- [ ] Atomicity tests prove one invalid operation prevents all operations in that response.
- [ ] Prompt/request construction test confirms the current board and conversation history are included without the API key.

### Success criteria

- Natural-language requests can produce validated, persistent board changes.
- The model cannot mutate the database outside the explicit operation schema.
- The API always returns a canonical board after a successful AI mutation.

## Part 10: AI chat sidebar

### Tasks

- [ ] Add a responsive, accessible chat sidebar consistent with the project color scheme.
- [ ] Add message history, input submission, pending state, safe error display, and retry behavior.
- [ ] Send the current conversation history with each message while keeping it only for the active browser session.
- [ ] Render assistant text and refresh or replace board state automatically when the response reports a change.
- [ ] Prevent duplicate submissions while a request is pending.
- [ ] Preserve usable Kanban drag-and-drop and chat layouts at desktop and narrow viewport sizes.
- [ ] Keep chat behavior focused on the single current board; do not add unrelated assistant features.

### Tests

- [ ] Frontend unit tests cover text-only replies, pending state, errors, retry, and board-changing replies.
- [ ] Integration tests mock deterministic structured AI responses and verify automatic board refresh.
- [ ] Playwright covers asking the AI to create, edit, move, and delete cards and verifies persistence after reload.
- [ ] Accessibility checks cover labeled controls, keyboard submission, focus behavior, and readable status announcements.
- [ ] Run one opt-in live end-to-end AI smoke test after deterministic tests pass.

### Success criteria

- The signed-in user can hold a multi-turn AI conversation in the sidebar.
- Valid AI-requested board changes appear without a manual page refresh and persist in SQLite.
- Failures leave the existing board intact and allow the user to retry.
- The complete application builds, starts, and passes its deterministic test suite in the production container.

## Final MVP acceptance checklist

- [ ] A fresh database is created automatically.
- [ ] The user can sign in with `user` / `password` and sign out.
- [ ] Each signed-in user is limited to their own single board.
- [ ] The five fixed columns can be renamed but not added or removed.
- [ ] Cards can be created, edited, moved, reordered, and deleted, with changes persisted.
- [ ] The AI chat can answer questions and atomically apply one or more supported board changes.
- [ ] FastAPI serves the static Next.js application and all APIs from one Docker container.
- [ ] Start and stop scripts are present for Windows, macOS, and Linux.
- [ ] Deterministic unit, integration, and end-to-end tests pass; live AI testing remains explicitly opt-in.
