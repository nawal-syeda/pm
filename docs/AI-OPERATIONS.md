# Structured AI board operations

Authenticated clients send `POST /api/ai/chat` with a `message` and optional browser-session `history`.
The backend sends that conversation plus the current canonical board to OpenRouter and requests a strict JSON response.

The response contains an assistant message and zero or more validated operations:

- `rename_column`
- `create_card`
- `edit_card`
- `move_card`
- `delete_card`

Every referenced resource must belong to the signed-in user. All operations are validated before being applied in one SQLite transaction. If any operation is invalid, the complete AI update is rejected and the board remains unchanged.
