from google import genai
from google.genai import types

from .base import ChatMessage, ProviderAuthError, ProviderRequestError

MAX_TOOL_TURNS = 10


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
            client = genai.Client(
                api_key=api_key.strip(),
                http_options=types.HttpOptions(timeout=60_000),
            )
            history = []
            for m in prior:
                role = "user" if m.role == "user" else "model"
                history.append(
                    types.Content(
                        role=role, parts=[types.Part.from_text(text=m.content)]
                    )
                )
            config = types.GenerateContentConfig()
            if system:
                config.system_instruction = system
            chat = client.chats.create(
                model=model or "gemini-2.5-flash", history=history, config=config
            )
            response = chat.send_message(last.content)
            return response.text or ""
        except (ProviderAuthError, ProviderRequestError):
            raise
        except Exception as e:
            msg = str(e).lower()
            if "api key" in msg or "401" in msg or "403" in msg:
                raise ProviderAuthError(str(e)) from e
            raise ProviderRequestError(str(e)) from e

    def complete_with_tools(
        self,
        messages,
        system,
        api_key,
        model,
        *,
        tools: list[dict],
        call_tool,
    ):
        """Gemini function-calling loop. tools: {name, description, input_schema}."""
        if not api_key or not api_key.strip():
            raise ProviderAuthError("Missing Gemini API key")
        if not messages:
            raise ProviderRequestError("messages must not be empty")
        if not tools:
            return self.complete(messages, system, api_key, model)

        try:
            client = genai.Client(
                api_key=api_key.strip(),
                http_options=types.HttpOptions(timeout=120_000),
            )
            declarations = []
            for tool in tools:
                declarations.append(
                    types.FunctionDeclaration(
                        name=tool["name"],
                        description=tool.get("description") or "",
                        parameters=tool.get("input_schema") or {"type": "object"},
                    )
                )
            gemini_tool = types.Tool(function_declarations=declarations)

            contents = []
            for m in messages:
                role = "user" if m.role == "user" else "model"
                contents.append(
                    types.Content(
                        role=role, parts=[types.Part.from_text(text=m.content)]
                    )
                )

            config = types.GenerateContentConfig(tools=[gemini_tool])
            if system:
                config.system_instruction = system

            final_text: list[str] = []
            model_name = model or "gemini-2.5-flash"

            for _ in range(MAX_TOOL_TURNS):
                response = client.models.generate_content(
                    model=model_name,
                    contents=contents,
                    config=config,
                )
                if not response.candidates:
                    break

                model_content = response.candidates[0].content
                contents.append(model_content)

                function_calls = []
                for part in model_content.parts or []:
                    if part.function_call:
                        function_calls.append(part.function_call)
                    elif part.text:
                        final_text.append(part.text)

                if not function_calls:
                    return "\n".join(final_text).strip()

                function_response_parts = []
                for function_call in function_calls:
                    tool_name = function_call.name
                    tool_args = dict(function_call.args or {})
                    try:
                        tool_result_text = call_tool(tool_name, tool_args)
                    except Exception as exc:
                        tool_result_text = f"Tool error: {exc}"
                    function_response_parts.append(
                        types.Part(
                            function_response=types.FunctionResponse(
                                name=tool_name,
                                response={"result": tool_result_text},
                            )
                        )
                    )
                contents.append(
                    types.Content(role="user", parts=function_response_parts)
                )

            if final_text:
                return "\n".join(final_text).strip()
            return f"[Stopped after {MAX_TOOL_TURNS} tool-use turns]"
        except (ProviderAuthError, ProviderRequestError):
            raise
        except Exception as e:
            msg = str(e).lower()
            if "api key" in msg or "401" in msg or "403" in msg:
                raise ProviderAuthError(str(e)) from e
            raise ProviderRequestError(str(e)) from e
