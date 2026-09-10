from openai import OpenAI, AuthenticationError, APIError
from .base import ChatMessage, ProviderAuthError, ProviderRequestError

OPENROUTER_BASE = "https://openrouter.ai/api/v1"

class OpenAICompatibleProvider:
    def __init__(self, base_url: str | None = None):
        self.base_url = base_url

    def complete(self, messages, system, api_key, model):
        if not api_key or not api_key.strip():
            raise ProviderAuthError("Missing API key")
        try:
            client = OpenAI(
                api_key=api_key.strip(),
                base_url=self.base_url,
                timeout=60.0,
            )
            api_messages = []
            if system:
                api_messages.append({"role": "system", "content": system})
            for m in messages:
                role = "assistant" if m.role in ("model", "assistant") else "user"
                api_messages.append({"role": role, "content": m.content})
            resp = client.chat.completions.create(
                model=model or "gpt-4o-mini",
                messages=api_messages,
            )
            if not resp.choices:
                raise ProviderRequestError("Empty completion response")
            return resp.choices[0].message.content or ""
        except AuthenticationError as e:
            raise ProviderAuthError(str(e)) from e
        except APIError as e:
            raise ProviderRequestError(str(e)) from e
