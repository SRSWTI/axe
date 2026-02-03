from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Literal, cast, get_args

from kosong.chat_provider import ChatProvider
from pydantic import SecretStr

from axe_cli.constant import USER_AGENT

if TYPE_CHECKING:
    from axe_cli.config import LLMModel, LLMProvider

type ProviderType = Literal[
    "kimi",
    "openai_legacy",
    "openai_responses",
    "anthropic",
    "google_genai",  # for backward-compatibility, equals to `gemini`
    "gemini",
    "vertexai",
    "bodega", 
    "_echo",
    "_scripted_echo",
    "_chaos",
]

type ModelCapability = Literal["image_in", "video_in", "thinking", "always_thinking"]
ALL_MODEL_CAPABILITIES: set[ModelCapability] = set(get_args(ModelCapability.__value__))


@dataclass(slots=True)
class LLM:
    chat_provider: ChatProvider
    max_context_size: int
    capabilities: set[ModelCapability]
    model_config: LLMModel | None = None
    provider_config: LLMProvider | None = None

    @property
    def model_name(self) -> str:
        return self.chat_provider.model_name


def model_display_name(model: LLMModel | str | None) -> str:
    """Get display name for a model, using alias if available."""
    if model is None:
        return ""
    if isinstance(model, str):
        return model
    return model.alias or model.model


def augment_provider_with_env_vars(provider: LLMProvider, model: LLMModel) -> dict[str, str]:
    """Override provider/model settings from environment variables.

    Returns:
        Mapping of environment variables that were applied.
    """
    applied: dict[str, str] = {}

    match provider.type:
        case "kimi":
            if base_url := os.getenv("AXE_BASE_URL"):
                provider.base_url = base_url
                applied["AXE_BASE_URL"] = base_url
            if api_key := os.getenv("AXE_API_KEY"):
                provider.api_key = SecretStr(api_key)
                applied["AXE_API_KEY"] = "******"
            if model_name := os.getenv("AXE_MODEL_NAME"):
                model.model = model_name
                applied["AXE_MODEL_NAME"] = model_name
            if max_context_size := os.getenv("AXE_MODEL_MAX_CONTEXT_SIZE"):
                model.max_context_size = int(max_context_size)
                applied["AXE_MODEL_MAX_CONTEXT_SIZE"] = max_context_size
            if capabilities := os.getenv("AXE_MODEL_CAPABILITIES"):
                caps_lower = (cap.strip().lower() for cap in capabilities.split(",") if cap.strip())
                model.capabilities = set(
                    cast(ModelCapability, cap)
                    for cap in caps_lower
                    if cap in get_args(ModelCapability.__value__)
                )
                applied["AXE_MODEL_CAPABILITIES"] = capabilities
        case "openai_legacy" | "openai_responses":
            if base_url := os.getenv("OPENAI_BASE_URL"):
                provider.base_url = base_url
            if api_key := os.getenv("OPENAI_API_KEY"):
                provider.api_key = SecretStr(api_key)
        case "bodega":
            # Bodega environment variable overrides
            if base_url := os.getenv("BODEGA_BASE_URL"):
                provider.base_url = base_url
                applied["BODEGA_BASE_URL"] = base_url
            if model_name := os.getenv("BODEGA_MODEL"):
                model.model = model_name
                applied["BODEGA_MODEL"] = model_name
        case _:
            pass

    return applied


def _kimi_default_headers(provider: LLMProvider) -> dict[str, str]:
    headers = {"User-Agent": USER_AGENT}
    if provider.custom_headers:
        headers.update(provider.custom_headers)
    return headers


def create_llm(
    provider: LLMProvider,
    model: LLMModel,
    *,
    thinking: bool | None = None,
    session_id: str | None = None,
) -> LLM | None:
    # Bodega has defaults for base_url and accepts "current" as model
    if provider.type not in {"_echo", "_scripted_echo", "bodega"} and (
        not provider.base_url or not model.model
    ):
        return None
    # For Bodega, only model is required (base_url has a default)
    if provider.type == "bodega" and not model.model:
        return None

    resolved_api_key = provider.api_key.get_secret_value() if provider.api_key else ""

    match provider.type:
        case "kimi":
            from kosong.chat_provider.kimi import Kimi

            chat_provider = Kimi(
                model=model.model,
                base_url=provider.base_url,
                api_key=resolved_api_key,
                default_headers=_kimi_default_headers(provider),
            )

            gen_kwargs: Kimi.GenerationKwargs = {}
            if session_id:
                gen_kwargs["prompt_cache_key"] = session_id
            if temperature := os.getenv("AXE_MODEL_TEMPERATURE"):
                gen_kwargs["temperature"] = float(temperature)
            if top_p := os.getenv("AXE_MODEL_TOP_P"):
                gen_kwargs["top_p"] = float(top_p)
            if max_tokens := os.getenv("AXE_MODEL_MAX_TOKENS"):
                gen_kwargs["max_tokens"] = int(max_tokens)

            if gen_kwargs:
                chat_provider = chat_provider.with_generation_kwargs(**gen_kwargs)
        case "openai_legacy":
            from kosong.contrib.chat_provider.openai_legacy import OpenAILegacy

            chat_provider = OpenAILegacy(
                model=model.model,
                base_url=provider.base_url,
                api_key=resolved_api_key,
                reasoning_key=provider.reasoning_key,
            )
        case "openai_responses":
            from kosong.contrib.chat_provider.openai_responses import OpenAIResponses

            chat_provider = OpenAIResponses(
                model=model.model,
                base_url=provider.base_url,
                api_key=resolved_api_key,
            )
        case "anthropic":
            from kosong.contrib.chat_provider.anthropic import Anthropic

            base_url = provider.base_url
            # Clean up the base_url if it's the default one, to rely on the kosong's url which doesnt work with anthropic
            if base_url and base_url.rstrip("/") == "https://api.anthropic.com/v1":
                base_url = None

            chat_provider = Anthropic(
                model=model.model,
                base_url=base_url,
                api_key=resolved_api_key,
                default_max_tokens=64000,
            )
        case "google_genai" | "gemini":
            from kosong.contrib.chat_provider.google_genai import GoogleGenAI

            chat_provider = GoogleGenAI(
                model=model.model,
                base_url=provider.base_url,
                api_key=resolved_api_key,
            )
        case "vertexai":
            from kosong.contrib.chat_provider.google_genai import GoogleGenAI

            os.environ.update(provider.env or {})
            chat_provider = GoogleGenAI(
                model=model.model,
                base_url=provider.base_url,
                api_key=resolved_api_key,
                vertexai=True,
            )
        case "bodega":
            from kosong.contrib.chat_provider.bodega import Bodega

            # Default to localhost:44468 if no base_url provided
            base_url = provider.base_url or "http://localhost:44468"

            chat_provider = Bodega(
                model=model.model,
                base_url=base_url,
                api_key=resolved_api_key if resolved_api_key else None,
            )

            # Apply generation kwargs from environment
            gen_kwargs: Bodega.GenerationKwargs = {}
            if temperature := os.getenv("BODEGA_TEMPERATURE"):
                gen_kwargs["temperature"] = float(temperature)
            if max_tokens := os.getenv("BODEGA_MAX_TOKENS"):
                gen_kwargs["max_tokens"] = int(max_tokens)

            if gen_kwargs:
                chat_provider = chat_provider.with_generation_kwargs(**gen_kwargs)
        case "_echo":
            from kosong.chat_provider.echo import EchoChatProvider

            chat_provider = EchoChatProvider()
        case "_scripted_echo":
            from kosong.chat_provider.echo import ScriptedEchoChatProvider

            if provider.env:
                os.environ.update(provider.env)
            scripts = _load_scripted_echo_scripts()
            trace_value = os.getenv("AXE_SCRIPTED_ECHO_TRACE", "")
            trace = trace_value.strip().lower() in {"1", "true", "yes", "on"}
            chat_provider = ScriptedEchoChatProvider(scripts, trace=trace)
        case "_chaos":
            from kosong.chat_provider.chaos import ChaosChatProvider, ChaosConfig
            from kosong.chat_provider.kimi import Kimi

            chat_provider = ChaosChatProvider(
                provider=Kimi(
                    model=model.model,
                    base_url=provider.base_url,
                    api_key=resolved_api_key,
                    default_headers=_kimi_default_headers(provider),
                ),
                chaos_config=ChaosConfig(
                    error_probability=0.8,
                    error_types=[429, 500, 503],
                ),
            )

    capabilities = derive_model_capabilities(model)

    # Apply thinking if specified or if model always requires thinking
    if "always_thinking" in capabilities or (thinking is True and "thinking" in capabilities):
        chat_provider = chat_provider.with_thinking("high")
    elif thinking is False:
        chat_provider = chat_provider.with_thinking("off")
    # If thinking is None and model doesn't always think, leave as-is (default behavior)

    return LLM(
        chat_provider=chat_provider,
        max_context_size=model.max_context_size,
        capabilities=capabilities,
        model_config=model,
        provider_config=provider,
    )


def derive_model_capabilities(model: LLMModel) -> set[ModelCapability]:
    capabilities = set(model.capabilities or ())
    # Models with "thinking" in their name are always-thinking models
    if "thinking" in model.model.lower() or "reason" in model.model.lower():
        capabilities.update(("thinking", "always_thinking"))
    # These models support thinking but can be toggled on/off
    elif model.model in {"axe-for-coding", "axe-code"}:
        capabilities.update(("thinking", "image_in", "video_in"))
    return capabilities


def _load_scripted_echo_scripts() -> list[str]:
    script_path = os.getenv("AXE_SCRIPTED_ECHO_SCRIPTS")
    if not script_path:
        raise ValueError("AXE_SCRIPTED_ECHO_SCRIPTS is required for _scripted_echo.")
    path = Path(script_path).expanduser()
    if not path.exists():
        raise ValueError(f"Scripted echo file not found: {path}")
    text = path.read_text(encoding="utf-8")
    try:
        data: object = json.loads(text)
    except json.JSONDecodeError:
        scripts = [chunk.strip() for chunk in text.split("\n---\n") if chunk.strip()]
        if scripts:
            return scripts
        raise ValueError(
            "Scripted echo file must be a JSON array of strings or a text file "
            "split by '\\n---\\n'."
        ) from None
    if isinstance(data, list):
        data_list = cast(list[object], data)
        if all(isinstance(item, str) for item in data_list):
            return cast(list[str], data_list)
    raise ValueError("Scripted echo JSON must be an array of strings.")
