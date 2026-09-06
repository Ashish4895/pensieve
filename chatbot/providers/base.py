from dataclasses import dataclass
from typing import Protocol

@dataclass
class ChatMessage:
    role: str  # "user" | "model" | "assistant" (normalize in adapters)
    content: str

class ProviderAuthError(Exception):
    pass

class ProviderRequestError(Exception):
    pass

class UnsupportedProviderError(Exception):
    pass

class ChatProvider(Protocol):
    def complete(
        self,
        messages: list[ChatMessage],
        system: str | None,
        api_key: str,
        model: str,
    ) -> str: ...
