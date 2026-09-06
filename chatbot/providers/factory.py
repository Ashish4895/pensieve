from .base import UnsupportedProviderError
from .gemini import GeminiProvider
from .openai_compatible import OpenAICompatibleProvider, OPENROUTER_BASE

_PROVIDERS = {
    "gemini": GeminiProvider(),
    "openai": OpenAICompatibleProvider(),
    "openrouter": OpenAICompatibleProvider(base_url=OPENROUTER_BASE),
}

def get_provider(name: str):
    key = (name or "").strip().lower()
    if key not in _PROVIDERS:
        raise UnsupportedProviderError(f"Unsupported provider: {name}")
    return _PROVIDERS[key]
