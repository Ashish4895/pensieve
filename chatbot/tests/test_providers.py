from unittest.mock import MagicMock, patch
import pytest
from chatbot.providers.base import ChatMessage
from chatbot.providers.factory import get_provider
from chatbot.providers.gemini import GeminiProvider

def test_factory_unknown_provider():
    with pytest.raises(Exception):
        get_provider("anthropic")

def test_gemini_complete_returns_text():
    provider = GeminiProvider()
    messages = [ChatMessage(role="user", content="hi")]
    fake_response = MagicMock()
    fake_response.text = "hello"
    with patch("chatbot.providers.gemini.genai.Client") as Client:
        client = Client.return_value
        chat = client.chats.create.return_value
        chat.send_message.return_value = fake_response
        out = provider.complete(messages, system="be brief", api_key="AIza-test", model="gemini-2.5-flash")
    assert out == "hello"
    Client.assert_called()  # constructed with api key wiring

def test_openai_compatible_maps_roles():
    from chatbot.providers.openai_compatible import OpenAICompatibleProvider
    provider = OpenAICompatibleProvider()
    messages = [
        ChatMessage(role="user", content="q1"),
        ChatMessage(role="model", content="a1"),
        ChatMessage(role="user", content="q2"),
    ]
    with patch("chatbot.providers.openai_compatible.OpenAI") as OpenAI:
        client = OpenAI.return_value
        client.chat.completions.create.return_value.choices = [
            MagicMock(message=MagicMock(content="ok"))
        ]
        out = provider.complete(messages, system="sys", api_key="sk-test", model="gpt-4o-mini")
    assert out == "ok"
    kwargs = client.chat.completions.create.call_args.kwargs
    assert kwargs["messages"][0] == {"role": "system", "content": "sys"}
    assert kwargs["messages"][2]["role"] == "assistant"  # model -> assistant

def test_factory_openrouter():
    from chatbot.providers.openai_compatible import OPENROUTER_BASE
    p = get_provider("openrouter")
    assert p is not None
    assert p.base_url == OPENROUTER_BASE
