from __future__ import annotations

import asyncio
import contextlib
import warnings
from collections.abc import AsyncGenerator
from pathlib import Path
from typing import TYPE_CHECKING, Any

import kaos
from kaos.path import KaosPath
from pydantic import SecretStr

from axe_cli.agentspec import DEFAULT_AGENT_FILE
from axe_cli.cli import InputFormat, OutputFormat
from axe_cli.config import Config, LLMModel, LLMProvider, load_config
from axe_cli.llm import augment_provider_with_env_vars, create_llm, model_display_name
from axe_cli.session import Session
from axe_cli.share import get_share_dir
from axe_cli.soul import run_soul
from axe_cli.soul.agent import Runtime, load_agent
from axe_cli.soul.context import Context
from axe_cli.soul.axesoul import AxeSoul
from axe_cli.utils.aioqueue import QueueShutDown
from axe_cli.utils.logging import logger, redirect_stderr_to_logger
from axe_cli.utils.path import shorten_home
from axe_cli.wire import Wire, WireUISide
from axe_cli.wire.types import ContentPart, WireMessage

if TYPE_CHECKING:
    from fastmcp.mcp_config import MCPConfig


def enable_logging(debug: bool = False) -> None:
    logger.remove()  # Remove default stderr handler
    logger.enable("axe_cli")
    if debug:
        logger.enable("kosong")
    logger.add(
        get_share_dir() / "logs" / "axe.log",
        # FIXME: configure level for different modules
        level="TRACE" if debug else "INFO",
        rotation="06:00",
        retention="10 days",
    )
    redirect_stderr_to_logger()


class AxeCLI:
    @staticmethod
    async def create(
        session: Session,
        *,
        # Basic configuration
        config: Config | Path | None = None,
        model_name: str | None = None,
        thinking: bool | None = None,
        # Run mode
        yolo: bool = False,
        # Extensions
        agent_file: Path | None = None,
        mcp_configs: list[MCPConfig] | list[dict[str, Any]] | None = None,
        skills_dir: KaosPath | None = None,
        # Loop control
        max_steps_per_turn: int | None = None,
        max_retries_per_step: int | None = None,
        max_ralph_iterations: int | None = None,
    ) -> AxeCLI:
        """
        Create a AxeCLI instance.

        Args:
            session (Session): A session created by `Session.create` or `Session.continue_`.
            config (Config | Path | None, optional): Configuration to use, or path to config file.
                Defaults to None.
            model_name (str | None, optional): Name of the model to use. Defaults to None.
            thinking (bool | None, optional): Whether to enable thinking mode. Defaults to None.
            yolo (bool, optional): Approve all actions without confirmation. Defaults to False.
            agent_file (Path | None, optional): Path to the agent file. Defaults to None.
            mcp_configs (list[MCPConfig | dict[str, Any]] | None, optional): MCP configs to load
                MCP tools from. Defaults to None.
            skills_dir (KaosPath | None, optional): Override skills directory discovery. Defaults
                to None.
            max_steps_per_turn (int | None, optional): Maximum number of steps in one turn.
                Defaults to None.
            max_retries_per_step (int | None, optional): Maximum number of retries in one step.
                Defaults to None.
            max_ralph_iterations (int | None, optional): Extra iterations after the first turn in
                Ralph mode. Defaults to None.

        Raises:
            FileNotFoundError: When the agent file is not found.
            ConfigError(AxeCLIException, ValueError): When the configuration is invalid.
            AgentSpecError(AxeCLIException, ValueError): When the agent specification is invalid.
            InvalidToolError(AxeCLIException, ValueError): When any tool cannot be loaded.
            MCPConfigError(AxeCLIException, ValueError): When any MCP configuration is invalid.
            MCPRuntimeError(AxeCLIException, RuntimeError): When any MCP server cannot be
                connected.
        """
        config = config if isinstance(config, Config) else load_config(config)
        if max_steps_per_turn is not None:
            config.loop_control.max_steps_per_turn = max_steps_per_turn
        if max_retries_per_step is not None:
            config.loop_control.max_retries_per_step = max_retries_per_step
        if max_ralph_iterations is not None:
            config.loop_control.max_ralph_iterations = max_ralph_iterations
        logger.info("Loaded config: {config}", config=config)

        model: LLMModel | None = None
        provider: LLMProvider | None = None
        model_config_name: str | None = None

        # try to use config file
        if not model_name and config.default_model:
            # no --model specified && default model is set in config
            model = config.models[config.default_model]
            provider = config.providers[model.provider]
            model_config_name = config.default_model
        if model_name and model_name in config.models:
            # --model specified && model is set in config
            model = config.models[model_name]
            provider = config.providers[model.provider]
            model_config_name = model_name

        if not model:
            model = LLMModel(provider="", model="", max_context_size=100_000)
            provider = LLMProvider(type="kimi", base_url="", api_key=SecretStr(""))

        # try overwrite with environment variables
        assert provider is not None
        assert model is not None
        env_overrides = augment_provider_with_env_vars(provider, model)

        # determine thinking mode
        thinking = config.default_thinking if thinking is None else thinking

        llm = create_llm(
            provider,
            model,
            thinking=thinking,
            session_id=session.id,
        )
        if llm is not None:
            logger.info("Using LLM provider: {provider}", provider=provider)
            logger.info("Using LLM model: {model}", model=model)
            logger.info("Thinking mode: {thinking}", thinking=thinking)

        runtime = await Runtime.create(config, llm, model_config_name, session, yolo, skills_dir)

        if agent_file is None:
            agent_file = DEFAULT_AGENT_FILE
        agent = await load_agent(agent_file, runtime, mcp_configs=mcp_configs or [])

        context = Context(session.context_file)
        await context.restore()

        soul = AxeSoul(agent, context=context)
        return AxeCLI(soul, runtime, env_overrides, model)

    def __init__(
        self,
        _soul: AxeSoul,
        _runtime: Runtime,
        _env_overrides: dict[str, str],
        _model_config: LLMModel | None = None,
    ) -> None:
        self._soul = _soul
        self._runtime = _runtime
        self._env_overrides = _env_overrides
        self._model_config = _model_config

    @property
    def soul(self) -> AxeSoul:
        """Get the AxeSoul instance."""
        return self._soul

    @property
    def session(self) -> Session:
        """Get the Session instance."""
        return self._runtime.session

    @contextlib.asynccontextmanager
    async def _env(self) -> AsyncGenerator[None]:
        original_cwd = KaosPath.cwd()
        await kaos.chdir(self._runtime.session.work_dir)
        try:
            # to ignore possible warnings from dateparser
            warnings.filterwarnings("ignore", category=DeprecationWarning)
            yield
        finally:
            await kaos.chdir(original_cwd)

    async def run(
        self,
        user_input: str | list[ContentPart],
        cancel_event: asyncio.Event,
        merge_wire_messages: bool = False,
    ) -> AsyncGenerator[WireMessage]:
        """
        Run the Axe Code CLI instance without any UI and yield Wire messages directly.

        Args:
            user_input (str | list[ContentPart]): The user input to the agent.
            cancel_event (asyncio.Event): An event to cancel the run.
            merge_wire_messages (bool): Whether to merge Wire messages as much as possible.

        Yields:
            WireMessage: The Wire messages from the `AxeSoul`.

        Raises:
            LLMNotSet: When the LLM is not set.
            LLMNotSupported: When the LLM does not have required capabilities.
            ChatProviderError: When the LLM provider returns an error.
            MaxStepsReached: When the maximum number of steps is reached.
            RunCancelled: When the run is cancelled by the cancel event.
        """
        async with self._env():
            wire_future = asyncio.Future[WireUISide]()
            stop_ui_loop = asyncio.Event()

            async def _ui_loop_fn(wire: Wire) -> None:
                wire_future.set_result(wire.ui_side(merge=merge_wire_messages))
                await stop_ui_loop.wait()

            soul_task = asyncio.create_task(
                run_soul(self.soul, user_input, _ui_loop_fn, cancel_event)
            )

            try:
                wire_ui = await wire_future
                while True:
                    msg = await wire_ui.receive()
                    yield msg
            except QueueShutDown:
                pass
            finally:
                # stop consuming Wire messages
                stop_ui_loop.set()
                # wait for the soul task to finish, or raise
                await soul_task

    async def run_shell(self, command: str | None = None) -> bool:
        """Run the Axe Code CLI instance with shell UI."""
        from axe_cli.ui.shell import Shell, WelcomeInfoItem
        
        # Auto-initialize axe-dig codebase intelligence
        try:
            from axe_cli.tools.axe.auto_init import ensure_codebase_initialized
            work_dir = self._runtime.session.work_dir.unsafe_to_local_path()
            await ensure_codebase_initialized(work_dir)
        except Exception:
            pass  # Don't let auto-init failures block startup

        welcome_info = [
            WelcomeInfoItem(
                name="Directory", value=str(shorten_home(self._runtime.session.work_dir))
            ),
            WelcomeInfoItem(name="Session", value=self._runtime.session.id),
        ]
        if base_url := self._env_overrides.get("AXE_BASE_URL"):
            welcome_info.append(
                WelcomeInfoItem(
                    name="API URL",
                    value=f"{base_url} (from AXE_BASE_URL)",
                    level=WelcomeInfoItem.Level.WARN,
                )
            )
        if self._env_overrides.get("AXE_API_KEY"):
            welcome_info.append(
                WelcomeInfoItem(
                    name="API Key",
                    value="****** (from AXE_API_KEY)",
                    level=WelcomeInfoItem.Level.WARN,
                )
            )
        if not self._runtime.llm:
            welcome_info.append(
                WelcomeInfoItem(
                    name="Model",
                    value="not set, configure via environment variables or config.toml",
                    level=WelcomeInfoItem.Level.WARN,
                )
            )
        elif "AXE_MODEL_NAME" in self._env_overrides:
            welcome_info.append(
                WelcomeInfoItem(
                    name="Model",
                    value=f"{self._soul.model_name} (from AXE_MODEL_NAME)",
                    level=WelcomeInfoItem.Level.WARN,
                )
            )
        else:
            welcome_info.append(
                WelcomeInfoItem(
                    name="Model",
                    value=model_display_name(self._model_config or self._soul.model_name),
                    level=WelcomeInfoItem.Level.INFO,
                )
            )
        async with self._env():
            shell = Shell(self._soul, welcome_info=welcome_info)
            return await shell.run(command)

    async def run_print(
        self,
        input_format: InputFormat,
        output_format: OutputFormat,
        command: str | None = None,
        *,
        final_only: bool = False,
    ) -> bool:
        """Run the Axe Code CLI instance with print UI."""
        from axe_cli.ui.print import Print

        async with self._env():
            print_ = Print(
                self._soul,
                input_format,
                output_format,
                self._runtime.session.context_file,
                final_only=final_only,
            )
            return await print_.run(command)

    async def run_acp(self) -> None:
        """Run the Axe Code CLI instance as ACP server."""
        from axe_cli.ui.acp import ACP

        async with self._env():
            acp = ACP(self._soul)
            await acp.run()

    async def run_wire_stdio(self) -> None:
        """Run the Axe Code CLI instance as Wire server over stdio."""
        from axe_cli.wire.server import WireServer

        async with self._env():
            server = WireServer(self._soul)
            await server.serve()
