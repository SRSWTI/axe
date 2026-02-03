# axe

## Quick commands (use uv)

- `make prepare` (sync deps for all workspace packages and install git hooks)
- `make format`
- `make check`
- `make test`
- `make ai-test`
- `make build` / `make build-bin`

If running tools directly, use `uv run ...`.

## Project overview

axe is a powerful agent for software engineering workflows. it supports an interactive shell UI, acp server mode for ide integrations, and mcp tool loading(suitable for people who are not vibe coders, we hate slop)

## Tech stack

- Python 3.12+ (tooling configured for 3.14)
- CLI framework: Typer
- Async runtime: asyncio
- LLM framework: kosong
- MCP integration: fastmcp
- Logging: loguru
- Package management/build: uv + uv_build; PyInstaller for binaries
- Tests: pytest + pytest-asyncio; lint/format: ruff; types: pyright + ty

## Architecture overview

- **CLI entry**: `src/axe_cli/cli.py` (Typer) parses flags (UI mode, agent spec, config, MCP)
  and routes into `AxeCLI` in `src/axe_cli/app.py`.
- **App/runtime setup**: `AxeCLI.create` loads config (`src/axe_cli/config.py`), chooses a
  model/provider (`src/axe_cli/llm.py`), builds a `Runtime` (`src/axe_cli/soul/agent.py`),
  loads an agent spec, restores `Context`, then constructs `AxeSoul`.
- **Agent specs**: YAML under `src/axe_cli/agents/` loaded by `src/axe_cli/agentspec.py`.
  Specs can `extend` base agents, select tools by import path, and define fixed subagents.
  System prompts live alongside specs; builtin args include `AXE_NOW`, `AXE_WORK_DIR`,
  `AXE_WORK_DIR_LS`, `AXE_AGENTS_MD`, `AXE_SKILLS` (this file is injected via
  `AXE_AGENTS_MD`).
- **Tooling**: `src/axe_cli/soul/toolset.py` loads tools by import path, injects dependencies,
  and runs tool calls. Built-in tools live in `src/axe_cli/tools/` (shell, file, web, todo,
  multiagent, dmail, think). MCP tools are loaded via `fastmcp`; CLI management is in
  `src/axe_cli/mcp.py` and stored in the share dir.
- **Subagents**: `LaborMarket` in `src/axe_cli/soul/agent.py` manages fixed and dynamic
  subagents. The Task tool (`src/axe_cli/tools/multiagent/`) spawns them.
- **Core loop**: `src/axe_cli/soul/axesoul.py` is the main agent loop. It accepts user input,
  handles slash commands (`src/axe_cli/soul/slash.py`), appends to `Context`
  (`src/axe_cli/soul/context.py`), calls the LLM (kosong), runs tools, and performs compaction
  (`src/axe_cli/soul/compaction.py`) when needed.
- **Approvals**: `src/axe_cli/soul/approval.py` mediates user approvals for tool actions; the
  soul forwards approval requests over `Wire` for UI handling.
- **UI/Wire**: `src/axe_cli/soul/run_soul` connects `AxeSoul` to a `Wire`
  (`src/axe_cli/wire/`) so UI loops can stream events. UIs live in `src/axe_cli/ui/`
  (shell/print/acp/wire).
- **Shell UI**: `src/axe_cli/ui/shell/` handles interactive TUI input, shell command mode,
  and slash command autocomplete; it is the default interactive experience.
- **Slash commands**: Soul-level commands live in `src/axe_cli/soul/slash.py`; shell-level
  commands live in `src/axe_cli/ui/shell/slash.py`. The shell UI exposes both and dispatches
  based on the registry. Standard skills register `/skill:<skill-name>` and load `SKILL.md`
  as a user prompt; flow skills register `/flow:<skill-name>` and execute the embedded flow.

## Major modules and interfaces

- `src/axe_cli/app.py`: `AxeCLI.create(...)` and `AxeCLI.run(...)` are the main programmatic
  entrypoints; this is what UI layers use.
- `src/axe_cli/soul/agent.py`: `Runtime` (config, session, builtins), `Agent` (system prompt +
  toolset), and `LaborMarket` (subagent registry).
- `src/axe_cli/soul/axesoul.py`: `AxeSoul.run(...)` is the loop boundary; it emits Wire
  messages and executes tools via `AxeToolset`.
- `src/axe_cli/soul/context.py`: conversation history + checkpoints; used by DMail for
  checkpointed replies.
- `src/axe_cli/soul/toolset.py`: load tools, run tool calls, bridge to MCP tools.
- `src/axe_cli/ui/*`: shell/print/acp frontends; they consume `Wire` messages.
- `src/axe_cli/wire/*`: event types and transport used between soul and UI.

## Repo map

- `src/axe_cli/agents/`: built-in agent YAML specs and prompts
- `src/axe_cli/prompts/`: shared prompt templates
- `src/axe_cli/soul/`: core runtime/loop, context, compaction, approvals
- `src/axe_cli/tools/`: built-in tools
- `src/axe_cli/ui/`: UI frontends (shell/print/acp/wire)
- `src/axe_cli/acp/`: ACP server components
- `packages/kosong/`, `packages/kaos/`: workspace deps
  + Kosong is an LLM abstraction layer designed for modern AI agent applications.
    It unifies message structures, asynchronous tool orchestration, and pluggable
    chat providers so you can build agents with ease and avoid vendor lock-in.
  + PyKAOS is a lightweight Python library providing an abstraction layer for agents
    to interact with operating systems. File operations and command executions via KAOS
    can be easily switched between local environment and remote systems over SSH.
- `tests/`, `tests_ai/`: test suites
- `klips`: Axe Code CLI Improvement Proposals

## Conventions and quality

- Python >=3.12 (ty config uses 3.14); line length 100.
- Ruff handles lint + format (rules: E, F, UP, B, SIM, I); pyright + ty for type checks.
- Tests use pytest + pytest-asyncio; files are `tests/test_*.py`.
- CLI entry points: `axe` -> `src/axe_cli/cli.py`.
- User config: `~/.axe/config.toml`; logs, sessions, and MCP config live in `~/.axe/`.

## Git commit messages

Conventional Commits format:

```
<type>(<scope>): <subject>
```

Allowed types:
`feat`, `fix`, `test`, `refactor`, `chore`, `style`, `docs`, `perf`, `build`, `ci`, `revert`.

## Release workflow

1. Ensure `main` is up to date (pull latest).
2. Create a release branch, e.g. `bump-0.68` or `bump-pykaos-0.5.3`.
3. Update `CHANGELOG.md`: rename `[Unreleased]` to `[0.68] - YYYY-MM-DD`.
4. Update `pyproject.toml` version.
5. Run `uv sync` to align `uv.lock`.
6. Commit the branch and open a PR.
7. Merge the PR, then switch back to `main` and pull latest.
8. Tag and push:
   - `git tag 0.68` or `git tag pykaos-0.5.3`
   - `git push --tags`
9. GitHub Actions handles the release after tags are pushed.
