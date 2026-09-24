# OpenRouter connectivity check

The backend keeps `OPENROUTER_API_KEY` server-side and uses
`nvidia/nemotron-3.5-lightning`, pinned to DeepInfra for consistent structured
responses and low latency.
Set the key in the project-root `.env` file, start the container, sign in, then run
`POST /api/ai/diagnostic` from [the API docs](http://localhost:8000/docs). A successful
response contains only the model name and its answer; secrets are never returned.

The deterministic test suite mocks the upstream request and does not consume credits.
The live diagnostic is an explicit opt-in check and requires a valid key.
