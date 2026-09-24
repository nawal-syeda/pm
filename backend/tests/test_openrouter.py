import json
import urllib.error

import pytest

from app import openrouter


def response(payload: dict) -> object:
    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return None

        def read(self):
            return json.dumps(payload).encode()

    return FakeResponse()


def test_success_uses_required_model_and_returns_answer(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "secret-test-key")
    calls = []

    def fake_urlopen(request, timeout):
        calls.append((request, timeout))
        return response({"choices": [{"message": {"content": "4"}}]})

    monkeypatch.setattr(openrouter.urllib.request, "urlopen", fake_urlopen)
    assert openrouter.ask_two_plus_two() == "4"
    assert calls[0][0].headers["Authorization"] == "Bearer secret-test-key"
    request_body = json.loads(calls[0][0].data)
    assert request_body["model"] == "nvidia/nemotron-3.5-lightning"
    assert request_body["provider"] == {"only": ["deepinfra"]}


def test_missing_key_is_clear(monkeypatch):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    with pytest.raises(openrouter.OpenRouterError, match="not configured"):
        openrouter.ask_two_plus_two()


@pytest.mark.parametrize(
    ("error", "message"),
    [
        (urllib.error.HTTPError("url", 401, "", {}, None), "authentication failed"),
        (urllib.error.HTTPError("url", 429, "", {}, None), "rate limit"),
        (TimeoutError(), "could not be reached"),
    ],
)
def test_upstream_failures_are_safe(monkeypatch, error, message):
    monkeypatch.setenv("OPENROUTER_API_KEY", "secret-test-key")
    monkeypatch.setattr(openrouter.urllib.request, "urlopen", lambda *_args, **_kwargs: (_ for _ in ()).throw(error))
    with pytest.raises(openrouter.OpenRouterError, match=message):
        openrouter.ask_two_plus_two()


def test_malformed_response_is_safe(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "secret-test-key")
    monkeypatch.setattr(openrouter.urllib.request, "urlopen", lambda *_args, **_kwargs: response({"unexpected": True}))
    with pytest.raises(openrouter.OpenRouterError, match="invalid response"):
        openrouter.ask_two_plus_two()
