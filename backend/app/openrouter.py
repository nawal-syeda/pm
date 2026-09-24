"""Small, server-side OpenRouter client used by the Part 8 diagnostic."""

import json
import os
import urllib.error
import urllib.request
from typing import Any

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
MODEL = "nvidia/nemotron-3.5-lightning"
PROVIDER = {"only": ["deepinfra"]}


class OpenRouterError(Exception):
    """A safe, user-facing error from the upstream model service."""


def _api_key() -> str:
    key = os.environ.get("OPENROUTER_API_KEY", "").strip()
    if not key:
        raise OpenRouterError("OpenRouter is not configured. Set OPENROUTER_API_KEY.")
    return key


def _completion(
    messages: list[dict[str, str]],
    timeout: float = 30.0,
    response_format: dict[str, Any] | None = None,
    max_tokens: int | None = None,
) -> str:
    key = _api_key()
    request_body: dict[str, Any] = {
        "model": MODEL,
        "messages": messages,
        "provider": PROVIDER,
    }
    if response_format is not None:
        request_body["response_format"] = response_format
    if max_tokens is not None:
        request_body["max_tokens"] = max_tokens
    payload = json.dumps(request_body).encode("utf-8")
    request = urllib.request.Request(
        OPENROUTER_URL,
        data=payload,
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "http://localhost:8000",
            "X-Title": "Project Management MVP",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read()
    except urllib.error.HTTPError as error:
        if error.code in (401, 403):
            raise OpenRouterError("OpenRouter authentication failed.") from None
        if error.code == 429:
            raise OpenRouterError("OpenRouter rate limit reached. Try again later.") from None
        raise OpenRouterError("OpenRouter returned an upstream error.") from None
    except (urllib.error.URLError, TimeoutError):
        raise OpenRouterError("OpenRouter could not be reached.") from None

    try:
        body: Any = json.loads(raw)
        answer = body["choices"][0]["message"]["content"]
    except (json.JSONDecodeError, KeyError, IndexError, TypeError):
        raise OpenRouterError("OpenRouter returned an invalid response.") from None
    if not isinstance(answer, str) or not answer.strip():
        raise OpenRouterError("OpenRouter returned an empty response.")
    return answer.strip()


def ask_two_plus_two() -> str:
    return _completion(
        [
            {
                "role": "system",
                "content": "Answer the arithmetic question exactly and concisely.",
            },
            {"role": "user", "content": "What is 2+2?"},
        ]
    )


def ask_structured(
    messages: list[dict[str, str]], schema: dict[str, Any]
) -> str:
    return _completion(
        messages,
        response_format={
            "type": "json_schema",
            "json_schema": {
                "name": "project_management_response",
                "strict": True,
                "schema": schema,
            },
        },
        max_tokens=600,
    )


def stream_structured(
    messages: list[dict[str, str]], schema: dict[str, Any]
):
    key = _api_key()
    payload = json.dumps(
        {
            "model": MODEL,
            "messages": messages,
            "provider": PROVIDER,
            "stream": True,
            "max_tokens": 600,
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": "project_management_response",
                    "strict": True,
                    "schema": schema,
                },
            },
        }
    ).encode("utf-8")
    request = urllib.request.Request(
        OPENROUTER_URL,
        data=payload,
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
            "Accept": "text/event-stream",
            "HTTP-Referer": "http://localhost:8000",
            "X-Title": "Project Management MVP",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=30.0) as response:
            for line in response:
                decoded = line.decode("utf-8").strip()
                if not decoded.startswith("data:"):
                    continue
                data = decoded[5:].strip()
                if data == "[DONE]":
                    break
                try:
                    chunk: Any = json.loads(data)
                    content = chunk["choices"][0].get("delta", {}).get("content", "")
                except (json.JSONDecodeError, KeyError, IndexError, TypeError):
                    raise OpenRouterError("OpenRouter returned an invalid stream.") from None
                if isinstance(content, str) and content:
                    yield content
    except urllib.error.HTTPError as error:
        if error.code in (401, 403):
            raise OpenRouterError("OpenRouter authentication failed.") from None
        if error.code == 429:
            raise OpenRouterError("OpenRouter rate limit reached. Try again later.") from None
        raise OpenRouterError("OpenRouter returned an upstream error.") from None
    except (urllib.error.URLError, TimeoutError):
        raise OpenRouterError("OpenRouter could not be reached.") from None
