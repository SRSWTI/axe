from __future__ import annotations

import tempfile
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import TYPE_CHECKING

from kosong.message import Message
from loguru import logger

import axe_cli.prompts as prompts
from axe_cli.soul import wire_send
from axe_cli.soul.agent import load_agents_md
from axe_cli.soul.context import Context
from axe_cli.soul.message import system
from axe_cli.utils.slashcmd import SlashCommandRegistry
from axe_cli.wire.types import TextPart

if TYPE_CHECKING:
    from axe_cli.soul.axesoul import AxeSoul

type SoulSlashCmdFunc = Callable[[AxeSoul, str], None | Awaitable[None]]
"""
A function that runs as a AxeSoul-level slash command.

Raises:
    Any exception that can be raised by `Soul.run`.
"""

registry = SlashCommandRegistry[SoulSlashCmdFunc]()


@registry.command
async def init(soul: AxeSoul, args: str):
    """Analyze the codebase and generate an `AGENTS.md` file"""
    from axe_cli.soul.axesoul import AxeSoul

    with tempfile.TemporaryDirectory() as temp_dir:
        tmp_context = Context(file_backend=Path(temp_dir) / "context.jsonl")
        tmp_soul = AxeSoul(soul.agent, context=tmp_context)
        await tmp_soul.run(prompts.INIT)

    agents_md = load_agents_md(soul.runtime.builtin_args.AXE_WORK_DIR)
    system_message = system(
        "The user just ran `/init` slash command. "
        "The system has analyzed the codebase and generated an `AGENTS.md` file. "
        f"Latest AGENTS.md file content:\n{agents_md}"
    )
    await soul.context.append_message(Message(role="user", content=[system_message]))


@registry.command
async def compact(soul: AxeSoul, args: str):
    """Compact the context"""
    if soul.context.n_checkpoints == 0:
        wire_send(TextPart(text="The context is empty."))
        return

    logger.info("Running `/compact`")
    await soul.compact_context()
    wire_send(TextPart(text="The context has been compacted."))


@registry.command(aliases=["reset"])
async def clear(soul: AxeSoul, args: str):
    """Clear the context"""
    logger.info("Running `/clear`")
    await soul.context.clear()
    wire_send(TextPart(text="The context has been cleared."))


@registry.command
async def yolo(soul: AxeSoul, args: str):
    """Toggle YOLO mode (auto-approve all actions)"""
    if soul.runtime.approval.is_yolo():
        soul.runtime.approval.set_yolo(False)
        wire_send(TextPart(text="You only die once! Actions will require approval."))
    else:
        soul.runtime.approval.set_yolo(True)
        wire_send(TextPart(text="You only live once! All actions will be auto-approved."))
