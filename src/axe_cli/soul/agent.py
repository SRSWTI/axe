from __future__ import annotations

import asyncio
import string
from collections.abc import Mapping
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pydantic
from kaos.path import KaosPath
from kosong.tooling import Toolset

from axe_cli.agentspec import load_agent_spec
from axe_cli.config import Config
from axe_cli.exception import MCPConfigError
from axe_cli.llm import LLM
from axe_cli.session import Session
from axe_cli.skill import Skill, discover_skills_from_roots, index_skills, resolve_skills_roots
from axe_cli.soul.approval import Approval
from axe_cli.soul.denwarenji import DenwaRenji
from axe_cli.soul.toolset import AxeToolset
from axe_cli.utils.environment import Environment
from axe_cli.utils.logging import logger
from axe_cli.utils.path import list_directory

if TYPE_CHECKING:
    from fastmcp.mcp_config import MCPConfig


@dataclass(frozen=True, slots=True, kw_only=True)
class BuiltinSystemPromptArgs:
    """Builtin system prompt arguments."""

    AXE_NOW: str
    """The current datetime."""
    AXE_WORK_DIR: KaosPath
    """The absolute path of current working directory."""
    AXE_WORK_DIR_LS: str
    """The directory listing of current working directory."""
    AXE_AGENTS_MD: str  # TODO: move to first message from system prompt
    """The content of AGENTS.md."""
    AXE_SKILLS: str
    """Formatted information about available skills."""


async def load_agents_md(work_dir: KaosPath) -> str | None:
    paths = [
        work_dir / "AGENTS.md",
        work_dir / "agents.md",
    ]
    for path in paths:
        if await path.is_file():
            logger.info("Loaded agents.md: {path}", path=path)
            return (await path.read_text()).strip()
    logger.info("No AGENTS.md found in {work_dir}", work_dir=work_dir)
    return None


@dataclass(slots=True, kw_only=True)
class Runtime:
    """Agent runtime."""

    config: Config
    llm: LLM | None  # we do not freeze the `Runtime` dataclass because LLM can be changed
    model_config_name: str | None  # name of the model config from config.toml
    session: Session
    builtin_args: BuiltinSystemPromptArgs
    denwa_renji: DenwaRenji
    approval: Approval
    labor_market: LaborMarket
    environment: Environment
    skills: dict[str, Skill]
    oauth: OAuthManager

    async def create(
        config: Config,
        llm: LLM | None,
        model_config_name: str | None,
        session: Session,
        yolo: bool,
        skills_dir: KaosPath | None = None,
    ) -> Runtime:
        ls_output, agents_md, environment = await asyncio.gather(
            list_directory(session.work_dir),
            load_agents_md(session.work_dir),
            Environment.detect(),
        )

        # Discover and format skills
        skills_roots = await resolve_skills_roots(session.work_dir, skills_dir_override=skills_dir)
        skills = await discover_skills_from_roots(skills_roots)
        skills_by_name = index_skills(skills)
        logger.info("Discovered {count} skill(s)", count=len(skills))
        skills_formatted = "\n".join(
            (
                f"- {skill.name}\n"
                f"  - Path: {skill.skill_md_file}\n"
                f"  - Description: {skill.description}"
            )
            for skill in skills
        )

        from axe_cli.auth.oauth import OAuthManager

        return Runtime(
            config=config,
            llm=llm,
            model_config_name=model_config_name,
            session=session,
            builtin_args=BuiltinSystemPromptArgs(
                AXE_NOW=datetime.now().astimezone().isoformat(),
                AXE_WORK_DIR=session.work_dir,
                AXE_WORK_DIR_LS=ls_output,
                AXE_AGENTS_MD=agents_md or "",
                AXE_SKILLS=skills_formatted or "No skills found.",
            ),
            denwa_renji=DenwaRenji(),
            approval=Approval(yolo=yolo),
            labor_market=LaborMarket(),
            environment=environment,
            skills=skills_by_name,
            oauth=OAuthManager(config),
        )

    def copy_for_fixed_subagent(self) -> Runtime:
        """Clone runtime for fixed subagent."""
        return Runtime(
            config=self.config,
            llm=self.llm,
            model_config_name=self.model_config_name,
            session=self.session,
            builtin_args=self.builtin_args,
            denwa_renji=DenwaRenji(),  # subagent must have its own DenwaRenji
            approval=self.approval.share(),
            labor_market=LaborMarket(),  # fixed subagent has its own LaborMarket
            environment=self.environment,
            skills=self.skills,
            oauth=self.oauth,
        )

    def copy_for_dynamic_subagent(self) -> Runtime:
        """Clone runtime for dynamic subagent."""
        return Runtime(
            config=self.config,
            llm=self.llm,
            model_config_name=self.model_config_name,
            session=self.session,
            builtin_args=self.builtin_args,
            denwa_renji=DenwaRenji(),  # subagent must have its own DenwaRenji
            approval=self.approval.share(),
            labor_market=self.labor_market,  # dynamic subagent shares LaborMarket with main agent
            environment=self.environment,
            skills=self.skills,
            oauth=self.oauth,
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class Agent:
    """The loaded agent."""

    name: str
    system_prompt: str
    toolset: Toolset
    runtime: Runtime
    """Each agent has its own runtime, which should be derived from its main agent."""


class LaborMarket:
    def __init__(self):
        self.fixed_subagents: dict[str, Agent] = {}
        self.fixed_subagent_descs: dict[str, str] = {}
        self.dynamic_subagents: dict[str, Agent] = {}

    @property
    def subagents(self) -> Mapping[str, Agent]:
        """Get all subagents in the labor market."""
        return {**self.fixed_subagents, **self.dynamic_subagents}

    def add_fixed_subagent(self, name: str, agent: Agent, description: str):
        """Add a fixed subagent."""
        self.fixed_subagents[name] = agent
        self.fixed_subagent_descs[name] = description

    def add_dynamic_subagent(self, name: str, agent: Agent):
        """Add a dynamic subagent."""
        self.dynamic_subagents[name] = agent


async def load_agent(
    agent_file: Path,
    runtime: Runtime,
    *,
    mcp_configs: list[MCPConfig] | list[dict[str, Any]],
) -> Agent:
    """
    Load agent from specification file.

    Raises:
        FileNotFoundError: When the agent file is not found.
        AgentSpecError(AxeCLIException, ValueError): When the agent specification is invalid.
        InvalidToolError(AxeCLIException, ValueError): When any tool cannot be loaded.
        MCPConfigError(AxeCLIException, ValueError): When any MCP configuration is invalid.
        MCPRuntimeError(AxeCLIException, RuntimeError): When any MCP server cannot be connected.
    """
    logger.info("Loading agent: {agent_file}", agent_file=agent_file)
    agent_spec = load_agent_spec(agent_file)

    system_prompt = _load_system_prompt(
        agent_spec.system_prompt_path,
        agent_spec.system_prompt_args,
        runtime.builtin_args,
    )

    # load subagents before loading tools because Task tool depends on LaborMarket on initialization
    for subagent_name, subagent_spec in agent_spec.subagents.items():
        logger.debug("Loading subagent: {subagent_name}", subagent_name=subagent_name)
        subagent = await load_agent(
            subagent_spec.path,
            runtime.copy_for_fixed_subagent(),
            mcp_configs=mcp_configs,
        )
        runtime.labor_market.add_fixed_subagent(subagent_name, subagent, subagent_spec.description)

    toolset = AxeToolset()
    tool_deps = {
        AxeToolset: toolset,
        Runtime: runtime,
        # TODO: remove all the following dependencies and use Runtime instead
        Config: runtime.config,
        BuiltinSystemPromptArgs: runtime.builtin_args,
        Session: runtime.session,
        DenwaRenji: runtime.denwa_renji,
        Approval: runtime.approval,
        LaborMarket: runtime.labor_market,
        Environment: runtime.environment,
    }
    tools = agent_spec.tools
    if agent_spec.exclude_tools:
        logger.debug("Excluding tools: {tools}", tools=agent_spec.exclude_tools)
        tools = [tool for tool in tools if tool not in agent_spec.exclude_tools]
    toolset.load_tools(tools, tool_deps)

    if mcp_configs:
        validated_mcp_configs: list[MCPConfig] = []
        if mcp_configs:
            from fastmcp.mcp_config import MCPConfig

            for mcp_config in mcp_configs:
                try:
                    validated_mcp_configs.append(
                        mcp_config
                        if isinstance(mcp_config, MCPConfig)
                        else MCPConfig.model_validate(mcp_config)
                    )
                except pydantic.ValidationError as e:
                    raise MCPConfigError(f"Invalid MCP config: {e}") from e
        await toolset.load_mcp_tools(validated_mcp_configs, runtime)

    return Agent(
        name=agent_spec.name,
        system_prompt=system_prompt,
        toolset=toolset,
        runtime=runtime,
    )


def _load_system_prompt(
    path: Path, args: dict[str, str], builtin_args: BuiltinSystemPromptArgs
) -> str:
    logger.info("Loading system prompt: {path}", path=path)
    system_prompt = path.read_text(encoding="utf-8").strip()
    logger.debug(
        "Substituting system prompt with builtin args: {builtin_args}, spec args: {spec_args}",
        builtin_args=builtin_args,
        spec_args=args,
    )
    return string.Template(system_prompt).substitute(asdict(builtin_args), **args)
