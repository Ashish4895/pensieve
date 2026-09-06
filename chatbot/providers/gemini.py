from google import genai
from google.genai import types
from .base import ChatMessage, ProviderAuthError, ProviderRequestError

class GeminiProvider:
    def complete(self, messages, system, api_key, model):
        if not api_key or not api_key.strip():
            raise ProviderAuthError("Missing Gemini API key")
        if not messages:
            raise ProviderRequestError("messages must not be empty")
        *prior, last = messages
        if last.role != "user":
            raise ProviderRequestError("Last message must be from user")
        try:
            client = genai.Client(api_key=api_key.strip())
            history = []
            for m in prior:
                role = "user" if m.role == "user" else "model"
                history.append(types.Content(role=role, parts=[types.Part.from_text(text=m.content)]))
            config = types.GenerateContentConfig()
            if system:
                config.system_instruction = system
            chat = client.chats.create(model=model or "gemini-2.5-flash", history=history, config=config)
            response = chat.send_message(last.content)
            return response.text or ""
        except (ProviderAuthError, ProviderRequestError):
            raise
        except Exception as e:
            msg = str(e).lower()
            if "api key" in msg or "401" in msg or "403" in msg:
                raise ProviderAuthError(str(e)) from e
            raise ProviderRequestError(str(e)) from e
