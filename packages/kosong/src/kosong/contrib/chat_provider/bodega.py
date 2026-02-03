"""
Bodega Inference Engine Chat Provider.

A chat provider for the Bodega inference engine, which provides
OpenAI-compatible endpoints for local language models running on Apple Silicon.

Server Address: http://localhost:44468 (default)
"""

import copy
import json
import re
import uuid
from collections.abc import AsyncIterator, Iterator, Sequence
from typing import TYPE_CHECKING, Any, Self, Unpack

import httpx
from typing_extensions import TypedDict

from kosong.chat_provider import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    ChatProvider,
    ChatProviderError,
    StreamedMessagePart,
    ThinkingEffort,
    TokenUsage,
)
from kosong.message import ContentPart, Message, TextPart, ThinkPart, ToolCall, ToolCallPart
from kosong.tooling import Tool

if TYPE_CHECKING:

    def type_check(bodega: "Bodega"):
        _: ChatProvider = bodega


# Default Bodega server address
DEFAULT_BASE_URL = "http://localhost:44468"

# Regex patterns for parsing unparsed content (when model loaded without parsers)
THINK_TAG_PATTERN = re.compile(r"<think>(.*?)</think>", re.DOTALL)
TOOL_CALL_TAG_PATTERN = re.compile(r"<tool_call>\s*(.*?)\s*</tool_call>", re.DOTALL)


def _parse_content_with_tags(content: str) -> tuple[str | None, str | None, list[dict[str, Any]]]:
    """
    Parse content that may contain <think> and <tool_call> tags.
    
    When Bodega model is loaded without parsers (qwen3, harmony, etc.),
    the model outputs thinking content wrapped in <think></think> tags
    and tool calls wrapped in <tool_call></tool_call> tags.
    
    Args:
        content: The raw content string from the API response.
        
    Returns:
        Tuple of (thinking_content, text_content, tool_calls)
        - thinking_content: Extracted content from <think> tags, or None
        - text_content: Remaining text content after removing tags, or None
        - tool_calls: List of parsed tool call dicts, or empty list
    """
    if not content:
        return None, None, []
    
    thinking_content: str | None = None
    tool_calls: list[dict[str, Any]] = []
    
    # Extract thinking content from <think> tags
    think_matches = THINK_TAG_PATTERN.findall(content)
    if think_matches:
        thinking_content = "\n".join(think_matches)
    
    # Extract tool calls from <tool_call> tags
    tool_call_matches = TOOL_CALL_TAG_PATTERN.findall(content)
    for match in tool_call_matches:
        try:
            tool_call_data = json.loads(match.strip())
            if isinstance(tool_call_data, dict) and "name" in tool_call_data:
                tool_calls.append({
                    "id": f"call_{uuid.uuid4().hex[:16]}",
                    "function": {
                        "name": tool_call_data["name"],
                        "arguments": json.dumps(tool_call_data.get("arguments", {})),
                    },
                })
        except json.JSONDecodeError:
            # If we can't parse the tool call, skip it
            pass
    
    # Remove tags from content to get clean text
    text_content = content
    text_content = THINK_TAG_PATTERN.sub("", text_content)
    text_content = TOOL_CALL_TAG_PATTERN.sub("", text_content)
    text_content = text_content.strip()
    
    # Return None if text content is empty after removing tags
    if not text_content:
        text_content = None
    
    return thinking_content, text_content, tool_calls


class Bodega:
    """
    A chat provider for the Bodega Inference Engine.

    The Bodega Inference Engine provides OpenAI-compatible endpoints for local
    language models running on Apple Silicon via MLX.

    >>> chat_provider = Bodega(model="current", base_url="http://localhost:44468")
    >>> chat_provider.name
    'bodega'
    >>> chat_provider.model_name
    'current'
    """

    name = "bodega"

    class GenerationKwargs(TypedDict, total=False):
        """
        Generation kwargs for Bodega API.
        """

        max_tokens: int | None
        temperature: float | None
        top_p: float | None
        presence_penalty: float | None
        frequency_penalty: float | None
        stop: str | list[str] | None
        seed: int | None
        response_format: dict[str, Any] | None

    class ChatTemplateKwargs(TypedDict, total=False):
        """
        Chat template kwargs specific to Bodega.
        These are passed as `chat_template_kwargs` in the request.
        """

        enable_thinking: bool
        reasoning_effort: str  # "low", "medium", "high"

    def __init__(
        self,
        *,
        model: str = "current",
        base_url: str | None = None,
        api_key: str | None = None,
        stream: bool = True,
        timeout: float = 300.0,
        **client_kwargs: Any,
    ):
        """
        Initialize the Bodega chat provider.

        Args:
            model: Model identifier. Use "current" for the currently loaded model.
            base_url: Bodega server URL. Defaults to http://localhost:44468.
            api_key: API key (optional, Bodega typically doesn't require auth).
            stream: Whether to stream responses. Defaults to True.
            timeout: Request timeout in seconds. Defaults to 300.
            **client_kwargs: Additional kwargs passed to httpx.AsyncClient.
        """
        self.model = model
        self.stream = stream
        self.base_url = (base_url or DEFAULT_BASE_URL).rstrip("/")
        self._api_key = api_key
        self._timeout = timeout
        self._client_kwargs = client_kwargs
        self._thinking_effort: ThinkingEffort | None = None
        self._generation_kwargs: Bodega.GenerationKwargs = {}
        self._chat_template_kwargs: Bodega.ChatTemplateKwargs = {}

    @property
    def model_name(self) -> str:
        return self.model

    @property
    def thinking_effort(self) -> ThinkingEffort | None:
        return self._thinking_effort

    async def generate(
        self,
        system_prompt: str,
        tools: Sequence[Tool],
        history: Sequence[Message],
    ) -> "BodegaStreamedMessage":
        """
        Generate a response from the Bodega inference engine.

        Args:
            system_prompt: The system prompt for the conversation.
            tools: Available tools for the model to use.
            history: Conversation history.

        Returns:
            A BodegaStreamedMessage that yields message parts.

        Raises:
            APIConnectionError: If connection to Bodega server fails.
            APITimeoutError: If the request times out.
            APIStatusError: If Bodega returns an error status.
        """
        # Build messages list
        messages: list[dict[str, Any]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.extend(self._convert_message(message) for message in history)

        # Build request body
        request_body: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "stream": self.stream,
        }

        # Add tools if provided
        if tools:
            request_body["tools"] = [self._tool_to_bodega(tool) for tool in tools]
            request_body["tool_choice"] = "auto"

        # Add generation kwargs
        request_body.update(self._generation_kwargs)

        # Add chat_template_kwargs for thinking/reasoning
        if self._chat_template_kwargs:
            request_body["chat_template_kwargs"] = dict(self._chat_template_kwargs)

        # Apply thinking effort if set
        if self._thinking_effort and self._thinking_effort != "off":
            if "chat_template_kwargs" not in request_body:
                request_body["chat_template_kwargs"] = {}
            request_body["chat_template_kwargs"]["enable_thinking"] = True
            request_body["chat_template_kwargs"]["reasoning_effort"] = self._thinking_effort

        # Build headers
        headers = {"Content-Type": "application/json"}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"

        try:
            async with httpx.AsyncClient(
                timeout=httpx.Timeout(self._timeout),
                **self._client_kwargs,
            ) as client:
                if self.stream:
                    response = await client.post(
                        f"{self.base_url}/v1/chat/completions",
                        json=request_body,
                        headers=headers,
                    )
                    response.raise_for_status()
                    return BodegaStreamedMessage(
                        response=response,
                        is_streaming=True,
                    )
                else:
                    response = await client.post(
                        f"{self.base_url}/v1/chat/completions",
                        json=request_body,
                        headers=headers,
                    )
                    response.raise_for_status()
                    return BodegaStreamedMessage(
                        response=response,
                        is_streaming=False,
                    )
        except httpx.TimeoutException as e:
            raise APITimeoutError(f"Request to Bodega timed out: {e}") from e
        except httpx.ConnectError as e:
            raise APIConnectionError(
                f"Failed to connect to Bodega at {self.base_url}: {e}"
            ) from e
        except httpx.HTTPStatusError as e:
            raise APIStatusError(
                e.response.status_code,
                f"Bodega API error: {e.response.text}",
            ) from e
        except httpx.HTTPError as e:
            raise ChatProviderError(f"HTTP error communicating with Bodega: {e}") from e

    def with_thinking(self, effort: ThinkingEffort) -> Self:
        """
        Return a copy configured with the given thinking effort.
        """
        new_self = copy.copy(self)
        new_self._thinking_effort = effort
        new_self._chat_template_kwargs = copy.deepcopy(self._chat_template_kwargs)
        new_self._generation_kwargs = copy.deepcopy(self._generation_kwargs)
        return new_self

    def with_generation_kwargs(self, **kwargs: Unpack[GenerationKwargs]) -> Self:
        """
        Copy the chat provider with updated generation kwargs.

        Returns:
            A new instance with updated generation kwargs.
        """
        new_self = copy.copy(self)
        new_self._generation_kwargs = copy.deepcopy(self._generation_kwargs)
        new_self._generation_kwargs.update(kwargs)
        new_self._chat_template_kwargs = copy.deepcopy(self._chat_template_kwargs)
        return new_self

    def with_chat_template_kwargs(self, **kwargs: Unpack[ChatTemplateKwargs]) -> Self:
        """
        Copy the chat provider with updated chat template kwargs.

        These are Bodega-specific parameters passed as `chat_template_kwargs`.

        Returns:
            A new instance with updated chat template kwargs.
        """
        new_self = copy.copy(self)
        new_self._chat_template_kwargs = copy.deepcopy(self._chat_template_kwargs)
        new_self._chat_template_kwargs.update(kwargs)
        new_self._generation_kwargs = copy.deepcopy(self._generation_kwargs)
        return new_self

    @property
    def model_parameters(self) -> dict[str, Any]:
        """
        The parameters of the model configuration.

        For tracing/logging purposes.
        """
        params: dict[str, Any] = {"base_url": self.base_url}
        if self._thinking_effort:
            params["thinking_effort"] = self._thinking_effort
        return params

    def _convert_message(self, message: Message) -> dict[str, Any]:
        """Convert a Kosong message to Bodega/OpenAI message format."""
        content: list[ContentPart] = []
        reasoning_content: str = ""

        for part in message.content:
            if isinstance(part, ThinkPart):
                reasoning_content += part.think
            else:
                content.append(part)

        # For simple text-only messages, use string content
        if len(content) == 1 and isinstance(content[0], TextPart):
            result: dict[str, Any] = {
                "role": message.role,
                "content": content[0].text,
            }
        else:
            # For complex messages, serialize properly
            message_copy = message.model_copy(deep=True)
            message_copy.content = content
            dumped = message_copy.model_dump(exclude_none=True)
            result = dumped

        # Add tool_call_id if present (for tool response messages)
        if message.tool_call_id:
            result["tool_call_id"] = message.tool_call_id

        return result

    @staticmethod
    def _tool_to_bodega(tool: Tool) -> dict[str, Any]:
        """Convert a Tool to Bodega/OpenAI tool format."""
        return {
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.parameters,
            },
        }


class StreamTagParser:
    """
    Helper class to parse streaming content with embedded tags.
    """
    def __init__(self):
        self.buffer = ""
        self.in_think = False
        self.in_tool = False
        self.tool_buffer = ""
        # Safe buffer size to avoid splitting tags (longest tag is </tool_call> = 12 chars)
        self.keep_size = 15

    def process(self, chunk: str) -> Iterator[StreamedMessagePart]:
        self.buffer += chunk
        
        while self.buffer:
            if self.in_think:
                # Look for closer </think>
                end_idx = self.buffer.find("</think>")
                if end_idx != -1:
                    # Found end of thinking
                    content = self.buffer[:end_idx]
                    if content:
                        yield ThinkPart(think=content)
                    self.buffer = self.buffer[end_idx + len("</think>"):]
                    self.in_think = False
                else:
                    # Yield content safely (keep enough for potential partial closer)
                    if len(self.buffer) > self.keep_size:
                        yield_content = self.buffer[:-self.keep_size]
                        yield ThinkPart(think=yield_content)
                        self.buffer = self.buffer[-self.keep_size:]
                    break
            
            elif self.in_tool:
                # Look for closer </tool_call>
                end_idx = self.buffer.find("</tool_call>")
                if end_idx != -1:
                    # Found end of tool call, parse accumulated JSON
                    tool_json_str = self.tool_buffer + self.buffer[:end_idx]
                    self.tool_buffer = "" # Reset tool buffer
                    self.buffer = self.buffer[end_idx + len("</tool_call>"):]
                    self.in_tool = False
                    
                    try:
                        tool_data = json.loads(tool_json_str)
                        if isinstance(tool_data, dict) and "name" in tool_data:
                            yield ToolCall(
                                id=f"call_{uuid.uuid4().hex[:16]}",
                                function=ToolCall.FunctionBody(
                                    name=tool_data["name"],
                                    arguments=json.dumps(tool_data.get("arguments", {})),
                                ),
                            )
                    except json.JSONDecodeError:
                        pass # Skip invalid JSON
                else:
                    # Buffer everything for tool parsing (can't stream partial JSON easily)
                    self.tool_buffer += self.buffer
                    self.buffer = ""
                    break

            else:
                # NORMAL state - look for openers
                think_idx = self.buffer.find("<think>")
                tool_idx = self.buffer.find("<tool_call>")
                
                # Determine which tag comes first
                first_tag_idx = -1
                tag_type = None
                
                # Check valid indices
                if think_idx != -1 and (tool_idx == -1 or think_idx < tool_idx):
                    first_tag_idx = think_idx
                    tag_type = "think"
                elif tool_idx != -1:
                    first_tag_idx = tool_idx
                    tag_type = "tool"
                
                if first_tag_idx != -1:
                    # Found a tag! Yield text before it
                    if first_tag_idx > 0:
                        yield TextPart(text=self.buffer[:first_tag_idx])
                    
                    # Advance buffer past the opener
                    tag_len = len(f"<{tag_type}>")
                    self.buffer = self.buffer[first_tag_idx + tag_len:]
                    
                    if tag_type == "think":
                        self.in_think = True
                    else:
                        self.in_tool = True
                else:
                    # No complete start tag found. Yield safe text part.
                    if len(self.buffer) > self.keep_size:
                        yield TextPart(text=self.buffer[:-self.keep_size])
                        self.buffer = self.buffer[-self.keep_size:]
                    break

    def flush(self) -> Iterator[StreamedMessagePart]:
        """Flush remaining buffer at end of stream."""
        if self.in_think:
            # We were in thinking, but stream ended. Yield rest as thinking.
            if self.buffer:
                yield ThinkPart(think=self.buffer)
        elif self.in_tool:
             # We were in tool, but incomplete. Ignore or yield as text?
             # Probably yield as text if it's broken
             if self.tool_buffer:
                 yield TextPart(text=self.tool_buffer)
             if self.buffer:
                 yield TextPart(text=self.buffer)
        else:
            # Normal text remaining
            if self.buffer:
                yield TextPart(text=self.buffer)


class BodegaStreamedMessage:
    """
    A streamed message response from Bodega.

    Handles both streaming and non-streaming responses from the Bodega API.
    """

    def __init__(
        self,
        response: httpx.Response,
        is_streaming: bool,
    ):
        self._response = response
        self._is_streaming = is_streaming
        self._id: str | None = None
        self._usage: TokenUsage | None = None
        self._iter: AsyncIterator[StreamedMessagePart] | None = None

    def __aiter__(self) -> AsyncIterator[StreamedMessagePart]:
        if self._iter is None:
            if self._is_streaming:
                self._iter = self._convert_stream_response()
            else:
                self._iter = self._convert_non_stream_response()
        return self._iter

    async def __anext__(self) -> StreamedMessagePart:
        if self._iter is None:
            self._iter = self.__aiter__()
        return await self._iter.__anext__()

    @property
    def id(self) -> str | None:
        return self._id

    @property
    def usage(self) -> TokenUsage | None:
        return self._usage

    async def _convert_non_stream_response(self) -> AsyncIterator[StreamedMessagePart]:
        """Convert a non-streaming response to message parts."""
        data = json.loads(self._response.text)

        self._id = data.get("id")

        # Extract usage
        if usage := data.get("usage"):
            self._usage = TokenUsage(
                input_other=usage.get("prompt_tokens", 0),
                output=usage.get("completion_tokens", 0),
            )

        if not data.get("choices"):
            return

        message = data["choices"][0].get("message", {})
        
        # Get API-parsed fields (when model loaded WITH parsers)
        api_reasoning_content = message.get("reasoning_content")
        api_tool_calls = message.get("tool_calls")
        content = message.get("content")
        
        # If the API already parsed reasoning/tool_calls, use those directly
        if api_reasoning_content:
            yield ThinkPart(think=api_reasoning_content)
        
        if api_tool_calls:
            # API-parsed tool calls
            for tool_call in api_tool_calls:
                yield ToolCall(
                    id=tool_call.get("id") or str(uuid.uuid4()),
                    function=ToolCall.FunctionBody(
                        name=tool_call["function"]["name"],
                        arguments=tool_call["function"]["arguments"],
                    ),
                )
            # If there's content alongside parsed tool_calls, yield it
            if content:
                yield TextPart(text=content)
        elif content:
            # No API-parsed tool calls - check if content has embedded tags
            # This happens when model is loaded WITHOUT parsers
            thinking, text, parsed_tool_calls = _parse_content_with_tags(content)
            
            # Yield thinking from tags (only if not already yielded from API)
            if thinking and not api_reasoning_content:
                yield ThinkPart(think=thinking)
            
            # Yield parsed tool calls from tags
            if parsed_tool_calls:
                for tool_call in parsed_tool_calls:
                    yield ToolCall(
                        id=tool_call["id"],
                        function=ToolCall.FunctionBody(
                            name=tool_call["function"]["name"],
                            arguments=tool_call["function"]["arguments"],
                        ),
                    )
            
            # Yield remaining text content
            if text:
                yield TextPart(text=text)

    async def _convert_stream_response(self) -> AsyncIterator[StreamedMessagePart]:
        """Convert a streaming response to message parts."""
        # Initialize the raw tag parser
        tag_parser = StreamTagParser()
        has_api_parsed_fields = False

        async for line in self._response.aiter_lines():
            line = line.strip()
            if not line:
                continue

            if line.startswith("data: "):
                data_str = line[6:]  # Remove "data: " prefix

                if data_str == "[DONE]":
                    break

                try:
                    chunk = json.loads(data_str)
                except json.JSONDecodeError:
                    continue

                if chunk.get("id"):
                    self._id = chunk["id"]

                # Extract usage from final chunk
                if usage := chunk.get("usage"):
                    self._usage = TokenUsage(
                        input_other=usage.get("prompt_tokens", 0),
                        output=usage.get("completion_tokens", 0),
                    )

                if not chunk.get("choices"):
                    continue

                delta = chunk["choices"][0].get("delta", {})

                # 1. API-PARSED FIELDS (Model loaded with parsers)
                # Yield API-parsed reasoning
                if reasoning_content := delta.get("reasoning_content"):
                    has_api_parsed_fields = True
                    yield ThinkPart(think=reasoning_content)

                # Yield API-parsed tool calls
                for tool_call in delta.get("tool_calls") or []:
                    has_api_parsed_fields = True
                    function = tool_call.get("function", {})

                    if function.get("name"):
                        yield ToolCall(
                            id=tool_call.get("id") or str(uuid.uuid4()),
                            function=ToolCall.FunctionBody(
                                name=function["name"],
                                arguments=function.get("arguments", ""),
                            ),
                        )
                    elif function.get("arguments"):
                        yield ToolCallPart(arguments_part=function["arguments"])
                
                # 2. CONTENT (Text or raw tags)
                if content := delta.get("content"):
                    if has_api_parsed_fields:
                        # If we already have API-parsed fields, content is just text
                        yield TextPart(text=content)
                    else:
                        # No API fields yet - feed to tag parser to check for tags
                        for part in tag_parser.process(content):
                            yield part
        
        # Flush any remaining content in the parser buffer
        if not has_api_parsed_fields:
            for part in tag_parser.flush():
                yield part


if __name__ == "__main__":
    import asyncio

    async def _dev_main():
        # Test basic chat
        chat = Bodega(model="current", stream=False)
        system_prompt = "You are a helpful assistant."
        history = [Message(role="user", content="Hello, how are you?")]

        print("Testing non-streaming response:")
        async for part in await chat.generate(system_prompt, [], history):
            print(part.model_dump(exclude_none=True))

        # Test with thinking
        print("\nTesting with thinking enabled:")
        chat_thinking = chat.with_thinking("high")
        async for part in await chat_thinking.generate(system_prompt, [], history):
            print(part.model_dump(exclude_none=True))

        # Test streaming
        print("\nTesting streaming response:")
        chat_stream = Bodega(model="current", stream=True)
        async for part in await chat_stream.generate(system_prompt, [], history):
            print(part.model_dump(exclude_none=True))

        # Test with tools
        print("\nTesting with tools:")
        tools = [
            Tool(
                name="web_search",
                description="Search the web for information",
                parameters={
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "The search query",
                        },
                    },
                    "required": ["query"],
                },
            )
        ]
        history = [Message(role="user", content="What's the weather in Tokyo?")]
        stream = await chat.generate(system_prompt, tools, history)
        async for part in stream:
            print(part.model_dump(exclude_none=True))
        print("usage:", stream.usage)

    asyncio.run(_dev_main())
