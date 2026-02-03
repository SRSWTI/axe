---
name: axe-cli-help
description: answer axe cli usage, configuration, and troubleshooting questions. Use when user asks about axe cli installation, setup, configuration, slash commands, keyboard shortcuts, MCP integration, providers, environment variables, how something works internally, or any questions about axe cli itself.
---

# axe cli help

Help users with axe cli questions by consulting documentation and source code.

## Strategy

1. **Prefer official documentation** for most questions
2. **Read local source** when in axe-cli project itself, or when user is developing with axe-cli as a library (e.g., importing from `axe_cli` in their code)
3. **Clone and explore source** for complex internals not covered in docs - **ask user for confirmation first**

## Documentation

Base URL: `https://github.com/SRSWTI/axe-code`

### Topic Mapping

| Topic | Page |
|-------|------|
| Installation, first run | `README.md` |
| Config files | `docs/en/configuration/config-files.md` |
| Providers, models | `docs/en/configuration/providers.md` |
| Environment variables | `docs/en/configuration/env-vars.md` |
| Slash commands | `docs/en/reference/slash-commands.md` |
| CLI flags | `docs/en/reference/axe-command.md` |
| Keyboard shortcuts | `docs/en/reference/keyboard.md` |
| MCP | `docs/en/customization/mcp.md` |
| Agents | `docs/en/customization/agents.md` |
| Skills | `docs/en/customization/skills.md` |
| FAQ | `docs/en/faq.md` |

## Source Code

Repository: `https://github.com/SRSWTI/axe-code`

When to read source:

- In axe-cli project directory (check `pyproject.toml` for `name = "axe-cli"`)
- User is importing `axe_cli` as a library in their project
- Question about internals not covered in docs (ask user before cloning)
