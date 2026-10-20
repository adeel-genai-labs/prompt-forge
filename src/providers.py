"""OpenAI-compatible LLM providers (e.g. Groq), called through the official openai client.

Add a provider by adding an entry to PROVIDERS; generator.py picks it up by key.
"""

import os

import openai

PROVIDERS: dict[str, dict] = {
    "groq": {
        "label": "Groq",
        "base_url": "https://api.groq.com/openai/v1",
        "api_key_env": "GROQ_API_KEY",
        "text_model": "llama-3.3-70b-versatile",
        "model_env": "GROQ_TEXT_MODEL",
    },
}

PLACEHOLDER_KEYS = {"", "your-key-here"}
RATE_LIMIT_MESSAGE = "Rate limit reached, please wait a minute and try again."


def read_api_key(env_name: str) -> str:
    """Return the API key from env_name, raising RuntimeError naming the variable if it is missing or a placeholder."""
    key = os.getenv(env_name, "").strip()
    if key in PLACEHOLDER_KEYS:
        raise RuntimeError(
            f"{env_name} is not set. Please add your key to the .env file (or Streamlit secrets), then restart the app."
        )
    return key


def provider_model(provider: str) -> str:
    """Return the text model for an OpenAI-compatible provider, from its env override or the default."""
    spec = PROVIDERS[provider]
    return os.getenv(spec["model_env"], spec["text_model"])


def call_openai_compatible(provider: str, system: str, user: str, temperature: float = 0.2) -> str:
    """Send one chat request in JSON mode to an OpenAI-compatible provider and return the reply text."""
    spec = PROVIDERS[provider]
    model = provider_model(provider)
    # One retry only: the client's default backoff on 429 can leave the UI waiting a long time.
    client = openai.OpenAI(api_key=read_api_key(spec["api_key_env"]), base_url=spec["base_url"], max_retries=1)

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
            temperature=temperature,
            response_format={"type": "json_object"},
        )
    except openai.AuthenticationError:
        raise RuntimeError(f"{spec['label']} rejected the API key. Please check {spec['api_key_env']}.") from None
    except openai.RateLimitError:
        raise RuntimeError(RATE_LIMIT_MESSAGE) from None
    except openai.NotFoundError:
        raise RuntimeError(
            f"{spec['label']} doesn't recognise the model '{model}'. Please check {spec['model_env']}."
        ) from None
    except openai.APIConnectionError:
        raise RuntimeError(f"Can't reach {spec['label']}. Please check your internet connection and try again.") from None
    except openai.APIStatusError as error:
        raise RuntimeError(f"{spec['label']} returned an error ({error.status_code}). Please try again shortly.") from None
    return response.choices[0].message.content or ""
