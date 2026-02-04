# Axe CLI Technical Reference

This document covers the technical details of Axe CLI, including configuration, session management, architecture, and advanced features.

## Sessions and Context Management

axe automatically saves your conversation history, allowing you to continue previous work at any time.

### Session resuming

Each time you start axe, a new session is created. If you want to continue a previous conversation, there are several ways:

**Continue the most recent session:**

Use the `--continue` flag to continue the most recent session in the current working directory:

```bash
axe --continue
```

**Switch to a specific session:**

Use the `--session` flag to switch to a session with a specific ID:

```bash
axe --session abc123
```

**Switch sessions during runtime:**

Enter `/sessions` (or `/resume`) to view all sessions in the current working directory, and use arrow keys to select the session you want to switch to:

```
/sessions
```

The list shows each session's title and last update time, helping you find the conversation you want to continue.

### Startup replay

When you continue an existing session, axe will replay the previous conversation history so you can quickly understand the context. During replay, previous messages and AI responses will be displayed.

### Clear and compact

As the conversation progresses, the context grows longer. axe will automatically compress the context when needed to ensure the conversation can continue.

You can also manually manage the context using slash commands:

**Clear context:**

Enter `/clear` to clear all context in the current session and start a fresh conversation:

```
/clear
```

After clearing, the AI will forget all previous conversation content. You usually don't need to use this command; for new tasks, starting a new session is a better choice.

**Compact context:**

Enter `/compact` to have the AI summarize the current conversation and replace the original context with the summary:

```
/compact
```

Compacting preserves key information while reducing token consumption. This is useful when the conversation is long but you still want to retain some context.

## Configuration

axe uses configuration files to manage API providers, models, services, and runtime parameters, supporting both TOML and JSON formats.

### Config file location

The default configuration file is located at `~/.axe/config.toml`. On first run, if the configuration file doesn't exist, axe will automatically create a default configuration file.

You can specify a different configuration file (TOML or JSON format) with the `--config-file` flag:

```bash
axe --config-file /path/to/config.toml
```

When calling axe programmatically, you can also pass the complete configuration content directly via the `--config` flag:

```bash
axe --config '{"default_model": "claude-sonnet-4", "providers": {...}, "models": {...}}'
```

### Config items

The configuration file contains the following top-level configuration items:

| Item | Type | Description |
|------|------|-------------|
| default_model | string | Default model name, must be a model defined in models |
| default_thinking | boolean | Whether to enable thinking mode by default (defaults to false) |
| providers | table | API provider configuration |
| models | table | Model configuration |
| loop_control | table | Agent loop control parameters |
| services | table | External service configuration (search, fetch) |
| mcp | table | MCP client configuration |

**Complete configuration example:**

```toml
default_model = "claude-sonnet-4"
default_thinking = false

[providers.anthropic]
type = "anthropic"
base_url = "https://api.anthropic.com/v1"
api_key = "sk-ant-xxx"

[models.claude-sonnet-4]
provider = "anthropic"
model = "claude-sonnet-4-20250514"
max_context_size = 200000

[loop_control]
max_steps_per_turn = 100
max_retries_per_step = 3
max_ralph_iterations = 0
reserved_context_size = 50000


[mcp.client]
tool_call_timeout_ms = 300000  # 5 minutes
```

### providers

`providers` defines API provider connection information. Each provider uses a unique name as key.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| type | string | Yes | Provider type (e.g., anthropic, openai) |
| base_url | string | Yes | API base URL |
| api_key | string | Yes | API key |
| env | table | No | Environment variables to set before creating provider instance |
| custom_headers | table | No | Custom HTTP headers to attach to requests |

**Example:**

```toml
[providers.anthropic]
type = "anthropic"
base_url = "https://api.anthropic.com/v1"
api_key = "sk-ant-xxx"
custom_headers = { "X-Custom-Header" = "value" }
```

### models

`models` defines available models. Each model uses a unique name as key.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| provider | string | Yes | Provider name to use, must be defined in providers |
| model | string | Yes | Model identifier (model name used in API) |
| max_context_size | integer | Yes | Maximum context length (in tokens) |
| capabilities | array | No | Model capability list |

**Example:**

```toml
[models.claude-sonnet-4]
provider = "anthropic"
model = "claude-sonnet-4-20250514"
max_context_size = 200000
capabilities = ["thinking", "image_in", "video_in"]
```

### loop_control

`loop_control` controls agent execution loop behavior.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| max_steps_per_turn | integer | 100 | Maximum steps per turn |
| max_retries_per_step | integer | 3 | Maximum retries per step |
| max_ralph_iterations | integer | 0 | Extra iterations after each user message; 0 disables; -1 is unlimited |
| reserved_context_size | integer | 50000 | Reserved token count for LLM response generation; auto-compaction triggers when context_tokens + reserved_context_size >= max_context_size |

### services

`services` configures external services used by axe.

**search service:**

Configures web search service. When enabled, the SearchWeb tool becomes available.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| base_url | string | Yes | Search service API URL |
| api_key | string | Yes | API key |
| custom_headers | table | No | Custom HTTP headers to attach to requests |

**fetch service:**

Configures web fetch service. When enabled, the FetchURL tool prioritizes using this service to fetch webpage content.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| base_url | string | Yes | Fetch service API URL |
| api_key | string | Yes | API key |
| custom_headers | table | No | Custom HTTP headers to attach to requests |

### mcp

`mcp` configures MCP client behavior.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| client.tool_call_timeout_ms | integer | 300000 | MCP tool call timeout (milliseconds) |

## Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                     YOUR CODEBASE                            │
│  100K lines across 500 files                                 │
└───────────────────────┬──────────────────────────────────────┘
                        │
                        ▼
┌──────────────────────────────────────────────────────────────┐
│                    AXE-DIG ENGINE                            │
│  5-layer analysis + semantic embeddings                      │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌────────┐ │
│  │   AST   │→│  Calls  │→│   CFG   │→│   DFG   │→│  PDG   │ │
│  └─────────┘ └─────────┘ └─────────┘ └─────────┘ └────────┘ │
│                                                              │
│  In-memory daemon: 100ms queries instead of 30s CLI spawns  │
└───────────────────────┬──────────────────────────────────────┘
                        │
                        ▼
┌──────────────────────────────────────────────────────────────┐
│                      AXE AGENT                               │
│  • Understands code semantically (not just text)            │
│  • Extracts minimal context (95% token savings)             │
│  • Executes tools (file ops, shell, multi-agent)            │
│  • Interactive shell UI with Ctrl+X toggle                  │
└──────────────────────────────────────────────────────────────┘
```

**The difference:**
- **Other tools**: Dump 100K lines → Claude figures it out → Burn tokens
- **axe**: Extract 5K tokens of pure signal → Surgical edits → Save money

## Advanced features

### Multi-agent workflows
Spawn subagents for parallel tasks:

```bash
# Main agent delegates to specialists
Task "refactor auth module" --agent refactor-specialist
Task "update tests" --agent test-specialist
Task "update docs" --agent docs-specialist
```

### Skills system
Reusable workflows and domain expertise:

```bash
# Available skills auto-detected from project
/skill:docker-deploy
/skill:api-design
/skill:performance-optimization
```

### Context management
axe maintains conversation history and can checkpoint/restore:

```bash
# Save current context
/checkpoint "before-refactor"

# Restore if things go wrong
/restore "before-refactor"
```

## MCP Integration

For AI tools integration, axe supports Model Context Protocol (MCP).

**Add to your MCP-compatible tool's configuration:**

```json
{
  "mcpServers": {
    "axe-dig": {
      "command": "dig-mcp",
      "args": ["--project", "/path/to/your/project"]
    }
  }
}
```
