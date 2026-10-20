"""Tests for src/providers.py. The openai client is mocked; nothing touches the network."""

from types import SimpleNamespace

import httpx2
import openai
import pytest

from src import providers


def status_error(error_class: type, status_code: int) -> Exception:
    """Return an openai status error with a fake response, as the client would raise it."""
    request = httpx2.Request("POST", "https://api.groq.com/openai/v1/chat/completions")
    response = httpx2.Response(status_code, request=request)
    return error_class(f"HTTP {status_code}", response=response, body=None)


@pytest.fixture
def fake_openai(monkeypatch):
    """Replace openai.OpenAI with a fake client; set `fake.error` to make create() raise."""
    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    monkeypatch.delenv("GROQ_TEXT_MODEL", raising=False)
    fake = SimpleNamespace(client_kwargs={}, sent={}, error=None, reply='{"title": "x"}')

    def create(**kwargs):
        fake.sent.update(kwargs)
        if fake.error:
            raise fake.error
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=fake.reply))])

    def make_client(**kwargs):
        fake.client_kwargs.update(kwargs)
        return SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))

    monkeypatch.setattr(providers.openai, "OpenAI", make_client)
    return fake


def test_groq_entry_has_expected_settings():
    groq = providers.PROVIDERS["groq"]
    assert groq["base_url"] == "https://api.groq.com/openai/v1"
    assert groq["api_key_env"] == "GROQ_API_KEY"
    assert groq["text_model"] == "openai/gpt-oss-120b"
    assert groq["model_env"] == "GROQ_TEXT_MODEL"


def test_call_openai_compatible_uses_json_mode_base_url_and_key(fake_openai):
    reply = providers.call_openai_compatible("groq", "system text", "user text", temperature=0.2)

    assert reply == '{"title": "x"}'
    assert fake_openai.client_kwargs["base_url"] == "https://api.groq.com/openai/v1"
    assert fake_openai.client_kwargs["api_key"] == "test-key"
    assert fake_openai.sent["model"] == "openai/gpt-oss-120b"
    assert fake_openai.sent["response_format"] == {"type": "json_object"}
    assert fake_openai.sent["temperature"] == 0.2
    assert fake_openai.sent["messages"] == [
        {"role": "system", "content": "system text"},
        {"role": "user", "content": "user text"},
    ]


def test_call_openai_compatible_uses_model_override(fake_openai, monkeypatch):
    monkeypatch.setenv("GROQ_TEXT_MODEL", "llama-3.1-8b-instant")
    providers.call_openai_compatible("groq", "system", "user")
    assert fake_openai.sent["model"] == "llama-3.1-8b-instant"


@pytest.mark.parametrize("key", [None, "", "  ", "your-key-here"])
def test_missing_or_placeholder_key_names_the_env_var(monkeypatch, key):
    if key is None:
        monkeypatch.delenv("GROQ_API_KEY", raising=False)
    else:
        monkeypatch.setenv("GROQ_API_KEY", key)
    with pytest.raises(RuntimeError, match="GROQ_API_KEY is not set"):
        providers.call_openai_compatible("groq", "system", "user")


@pytest.mark.parametrize(
    "error_class, status_code, message",
    [
        (openai.RateLimitError, 429, "Rate limit reached, please wait a minute and try again."),
        (openai.AuthenticationError, 401, "Groq rejected the API key. Please check GROQ_API_KEY."),
        (openai.NotFoundError, 404, "Groq doesn't recognise the model 'openai/gpt-oss-120b'"),
        (openai.InternalServerError, 500, r"Groq returned an error \(500\)"),
    ],
)
def test_api_errors_become_friendly_messages(fake_openai, error_class, status_code, message):
    fake_openai.error = status_error(error_class, status_code)
    with pytest.raises(RuntimeError, match=message):
        providers.call_openai_compatible("groq", "system", "user")


def test_connection_error_becomes_friendly_message(fake_openai):
    request = httpx2.Request("POST", "https://api.groq.com/openai/v1/chat/completions")
    fake_openai.error = openai.APIConnectionError(request=request)
    with pytest.raises(RuntimeError, match="Can't reach Groq"):
        providers.call_openai_compatible("groq", "system", "user")
