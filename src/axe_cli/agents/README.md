# Agents and Subagents

An agent defines the AI's behavior, including system prompts, available tools, and subagents. You can use built-in agents or create custom agents.

## Lethal Efficiency with Dynamic Subagents

axe isn't limited to one main agent. You can create subagents and tasks for *anything* you want.

Need a dedicated security researcher? A ruthlessly precise code reviewer? A creative copywriter? axe can create and deploy specialized subagents based on your exact requirements. These subagents help you complete tasks better, faster, and more efficiently—operating with lethal precision to divide and conquer complex workflows.

![subagents in action](../../assets/axe_gif_subagents.gif)

**Subagents enable parallel task execution:** Spawn multiple specialized agents to work on different aspects of a problem simultaneously, each with their own context and tools.

## Built-in agents

axe provides two built-in agents. You can select one at startup with the `--agent` flag:

```bash
axe --agent default
```

**default**

The default agent, suitable for general use. Enabled tools:

- Task, SetTodoList, Shell, ReadFile, ReadMediaFile, Glob, Grep, WriteFile, StrReplaceFile
- CodeSearch, CodeContext, CodeStructure, CodeImpact (axe-dig tools)

**okabe**

An experimental agent for testing new prompts and tools. Adds SendDMail on top of default.

## Custom agent files

Agents are defined in YAML format. Load a custom agent with the `--agent-file` flag:

```bash
axe --agent-file /path/to/my-agent.yaml
```

**Basic structure:**

```yaml
version: 1
agent:
  name: my-agent
  system_prompt_path: ./system.md
  tools:
    - "axe_cli.tools.shell:Shell"
    - "axe_cli.tools.file:ReadFile"
    - "axe_cli.tools.file:WriteFile"
```

**Inheritance and overrides:**

Use `extend` to inherit another agent's configuration and only override what you need to change:

```yaml
version: 1
agent:
  extend: default  # Inherit from default agent
  system_prompt_path: ./my-prompt.md  # Override system prompt
  exclude_tools:  # Exclude certain tools
    - "axe_cli.tools.web:SearchWeb"
    - "axe_cli.tools.web:FetchURL"
```

`extend: default` inherits from the built-in default agent. You can also specify a relative path to inherit from another agent file.

**Configuration fields:**

| Field | Description | Required |
|-------|-------------|----------|
| extend | Agent to inherit from, can be `default` or a relative path | No |
| name | Agent name | Yes (optional when inheriting) |
| system_prompt_path | System prompt file path, relative to agent file | Yes (optional when inheriting) |
| system_prompt_args | Custom arguments passed to system prompt, merged when inheriting | No |
| tools | Tool list, format is `module:ClassName` | Yes (optional when inheriting) |
| exclude_tools | Tools to exclude | No |
| subagents | Subagent definitions | No |

### System prompt built-in parameters

The system prompt file is a Markdown template that can use `${VAR}` syntax to reference variables. Built-in variables include:

| Variable | Description |
|----------|-------------|
| ${AXE_NOW} | Current time (ISO format) |
| ${AXE_WORK_DIR} | Working directory path |
| ${AXE_WORK_DIR_LS} | Working directory file list |
| ${AXE_AGENTS_MD} | AGENTS.md file content (if exists) |
| ${AXE_SKILLS} | Loaded skills list |

You can also define custom parameters via `system_prompt_args`:

```yaml
agent:
  system_prompt_args:
    MY_VAR: "custom value"
```

Then use `${MY_VAR}` in the prompt.

**System prompt example:**

```markdown
# My Agent

You are a helpful assistant. Current time: ${AXE_NOW}.

Working directory: ${AXE_WORK_DIR}

${MY_VAR}
```

### Defining subagents in agent files

Subagents can handle specific types of tasks. After defining subagents in an agent file, the main agent can launch them via the Task tool:

```yaml
version: 1
agent:
  extend: default
  subagents:
    coder:
      path: ./coder-sub.yaml
      description: "Handle coding tasks"
    reviewer:
      path: ./reviewer-sub.yaml
      description: "Code review expert"
```

Subagent files are also standard agent format, typically inheriting from the main agent and excluding certain tools:

```yaml
# coder-sub.yaml
version: 1
agent:
  extend: ./agent.yaml  # Inherit from main agent
  system_prompt_args:
    ROLE_ADDITIONAL: |
      You are now running as a subagent...
  exclude_tools:
    - "axe_cli.tools.multiagent:Task"  # Exclude Task tool to avoid nesting
```

### How subagents run

Subagents launched via the Task tool run in an isolated context and return results to the main agent when complete. Advantages of this approach:

- Isolated context, avoiding pollution of main agent's conversation history
- Multiple independent tasks can be processed in parallel
- Subagents can have targeted system prompts

### Dynamic subagent creation

CreateSubagent is an advanced tool that allows AI to dynamically define new subagent types at runtime (not enabled by default). To use it, add to your agent file:

```yaml
agent:
  tools:
    - "axe_cli.tools.multiagent:CreateSubagent"
```
