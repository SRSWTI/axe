"""
Token counter for tracking all tokens going in and out of the LLM.

This module provides local token counting using tiktoken, independent of API-reported
token usage. It tracks:
- Input tokens: user messages, system prompts, tool results, file contents
- Output tokens: assistant messages, tool calls
- Cumulative totals across a session
"""

from __future__ import annotations

import tiktoken
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any

from kosong.message import Message, ToolCall, ContentPart, TextPart, ImageURLPart, VideoURLPart
from kosong.tooling import Tool

from axe_cli.utils.logging import logger


@dataclass
class TokenCount:
    """Token count statistics."""

    input_tokens: int = 0
    """Total input tokens sent to the LLM."""
    output_tokens: int = 0
    """Total output tokens received from the LLM."""
    
    @property
    def total_tokens(self) -> int:
        """Total tokens (input + output)."""
        return self.input_tokens + self.output_tokens
    
    def add_input(self, count: int) -> None:
        """Add to input token count."""
        self.input_tokens += count
    
    def add_output(self, count: int) -> None:
        """Add to output token count."""
        self.output_tokens += count
    
    def __str__(self) -> str:
        return f"Input: {self.input_tokens:,} | Output: {self.output_tokens:,} | Total: {self.total_tokens:,}"


class TokenCounter:
    """
    Token counter using tiktoken for local token counting.
    
    This counter tracks all tokens independently of what the API reports,
    providing accurate local counts for monitoring and debugging.
    """
    
    def __init__(self, model_name: str = "gpt-4"):
        """
        Initialize the token counter.
        
        Args:
            model_name: The model name to use for encoding. Defaults to "gpt-4".
                       Common values: "gpt-4", "gpt-3.5-turbo", "cl100k_base"
        """
        self._session_count = TokenCount()
        self._step_count = TokenCount()
        
        # Try to get encoding for the specific model, fall back to cl100k_base
        try:
            self._encoding = tiktoken.encoding_for_model(model_name)
            logger.debug(f"Token counter initialized with encoding for model: {model_name}")
        except KeyError:
            # If model not found, use cl100k_base (used by gpt-4, gpt-3.5-turbo, etc.)
            self._encoding = tiktoken.get_encoding("cl100k_base")
            logger.debug(f"Model {model_name} not found, using cl100k_base encoding")
    
    @property
    def session_count(self) -> TokenCount:
        """Get the cumulative session token count."""
        return self._session_count
    
    @property
    def step_count(self) -> TokenCount:
        """Get the current step token count."""
        return self._step_count
    
    def reset_step_count(self) -> None:
        """Reset the step counter (call at the start of each step)."""
        self._step_count = TokenCount()
    
    def count_text(self, text: str) -> int:
        """
        Count tokens in a text string.
        
        Args:
            text: The text to count tokens for.
            
        Returns:
            The number of tokens.
        """
        if not text:
            return 0
        try:
            return len(self._encoding.encode(text, disallowed_special=()))
        except Exception as e:
            logger.warning(f"Error counting tokens for text: {e}")
            # Fallback: rough estimate (1 token ≈ 4 characters)
            return len(text) // 4
    
    def count_message(self, message: Message) -> int:
        """
        Count tokens in a message.
        
        Args:
            message: The message to count tokens for.
            
        Returns:
            The number of tokens including role and formatting overhead.
        """
        # Start with overhead for role and message structure
        # OpenAI format: every message has ~4 tokens overhead
        num_tokens = 4
        
        # Add role tokens
        num_tokens += self.count_text(message.role)
        
        # Count content parts
        if isinstance(message.content, str):
            num_tokens += self.count_text(message.content)
        elif isinstance(message.content, list):
            for part in message.content:
                num_tokens += self._count_content_part(part)
        
        # Count tool calls
        if message.tool_calls:
            for tool_call in message.tool_calls:
                num_tokens += self._count_tool_call(tool_call)
        
        return num_tokens
    
    def count_messages(self, messages: Sequence[Message]) -> int:
        """
        Count tokens in a sequence of messages.
        
        Args:
            messages: The messages to count tokens for.
            
        Returns:
            The total number of tokens.
        """
        return sum(self.count_message(msg) for msg in messages)
    
    def count_system_prompt(self, system_prompt: str) -> int:
        """
        Count tokens in a system prompt.
        
        Args:
            system_prompt: The system prompt to count tokens for.
            
        Returns:
            The number of tokens including formatting overhead.
        """
        # System messages have similar overhead as regular messages
        return 4 + self.count_text(system_prompt)
    
    def count_tools(self, tools: Sequence[Tool]) -> int:
        """
        Count tokens in tool definitions.
        
        Args:
            tools: The tools to count tokens for.
            
        Returns:
            The number of tokens.
        """
        total = 0
        for tool in tools:
            # Tool definitions include name, description, and parameters
            total += self.count_text(tool.name)
            total += self.count_text(tool.description or "")
            
            # Count parameter schema (rough estimate)
            if hasattr(tool, 'params') and tool.params:
                try:
                    # Try to get the schema if it's a Pydantic model
                    if hasattr(tool.params, 'model_json_schema'):
                        import json
                        schema_str = json.dumps(tool.params.model_json_schema())
                        total += self.count_text(schema_str)
                    else:
                        # Rough estimate: ~50 tokens per parameter
                        total += 50
                except Exception:
                    total += 50
        
        # Add overhead for tool definitions structure
        total += len(tools) * 10
        return total
    
    def track_input(
        self,
        messages: Sequence[Message] | None = None,
        system_prompt: str | None = None,
        tools: Sequence[Tool] | None = None,
    ) -> int:
        """
        Track input tokens and add to counters.
        
        Args:
            messages: Optional messages to count.
            system_prompt: Optional system prompt to count.
            tools: Optional tools to count.
            
        Returns:
            The number of tokens counted.
        """
        count = 0
        
        if system_prompt:
            count += self.count_system_prompt(system_prompt)
        
        if messages:
            count += self.count_messages(messages)
        
        if tools:
            count += self.count_tools(tools)
        
        if count > 0:
            self._session_count.add_input(count)
            self._step_count.add_input(count)
            logger.debug(f"Tracked {count:,} input tokens")
        
        return count
    
    def track_output(self, message: Message) -> int:
        """
        Track output tokens from an assistant message.
        
        Args:
            message: The assistant message to count.
            
        Returns:
            The number of tokens counted.
        """
        count = self.count_message(message)
        
        if count > 0:
            self._session_count.add_output(count)
            self._step_count.add_output(count)
            logger.debug(f"Tracked {count:,} output tokens")
        
        return count
    
    def _count_content_part(self, part: ContentPart) -> int:
        """Count tokens in a content part."""
        if isinstance(part, TextPart):
            return self.count_text(part.text)
        elif isinstance(part, ImageURLPart):
            # Images: rough estimate based on resolution
            # Standard image ~765 tokens, high-res can be more
            return 765
        elif isinstance(part, VideoURLPart):
            # Videos: estimate based on frames
            # Rough estimate: ~85 tokens per frame, typical video ~100 frames
            return 8500
        else:
            # Unknown content type, use conservative estimate
            return 100
    
    def _count_tool_call(self, tool_call: ToolCall) -> int:
        """Count tokens in a tool call."""
        # Tool calls include function name and arguments
        # ToolCall has a nested function attribute with name and arguments
        count = self.count_text(tool_call.function.name)
        
        if tool_call.function.arguments:
            # Arguments are typically JSON string
            count += self.count_text(tool_call.function.arguments)
        
        # Add overhead for tool call structure
        count += 10
        
        return count


# Global token counter instance (optional singleton pattern)
_global_counter: TokenCounter | None = None


def get_global_counter() -> TokenCounter:
    """Get or create the global token counter instance."""
    global _global_counter
    if _global_counter is None:
        _global_counter = TokenCounter()
    return _global_counter


def set_global_counter(counter: TokenCounter) -> None:
    """Set the global token counter instance."""
    global _global_counter
    _global_counter = counter
