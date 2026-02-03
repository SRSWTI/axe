# Built-in Tools

The following are all built-in tools in axe.

## Task
**Path:** `axe_cli.tools.multiagent:Task`  
**Description:** Dispatch a subagent to execute a task. Subagents cannot access the main agent's context; all necessary information must be provided in the prompt.

| Parameter | Type | Description |
|-----------|------|-------------|
| description | string | Short task description (3-5 words) |
| subagent_name | string | Subagent name |
| prompt | string | Detailed task description |

## SetTodoList
**Path:** `axe_cli.tools.todo:SetTodoList`  
**Description:** Manage todo list, track task progress

| Parameter | Type | Description |
|-----------|------|-------------|
| todos | array | Todo list items |
| todos[].title | string | Todo item title |
| todos[].status | string | Status: pending, in_progress, done |

## Shell
**Path:** `axe_cli.tools.shell:Shell`  
**Description:** Execute shell commands. Requires user approval. Uses the appropriate shell for the OS (bash/zsh on Unix, PowerShell on Windows).

| Parameter | Type | Description |
|-----------|------|-------------|
| command | string | Command to execute |
| timeout | int | Timeout in seconds, default 60, max 300 |

## ReadFile
**Path:** `axe_cli.tools.file:ReadFile`  
**Description:** Read text file content. Max 1000 lines per read, max 2000 characters per line. Files outside working directory require absolute paths.

| Parameter | Type | Description |
|-----------|------|-------------|
| path | string | File path |
| line_offset | int | Starting line number, default 1 |
| n_lines | int | Number of lines to read, default/max 1000 |

## ReadMediaFile
**Path:** `axe_cli.tools.file:ReadMediaFile`  
**Description:** Read image or video files. Max file size 100MB. Only available when the model supports image/video input. Files outside working directory require absolute paths.

| Parameter | Type | Description |
|-----------|------|-------------|
| path | string | File path |

## Glob
**Path:** `axe_cli.tools.file:Glob`  
**Description:** Match files and directories by pattern. Returns max 1000 matches, patterns starting with ** not allowed.

| Parameter | Type | Description |
|-----------|------|-------------|
| pattern | string | Glob pattern (e.g., *.py, src/**/*.ts) |
| directory | string | Search directory, defaults to working directory |
| include_dirs | bool | Include directories, default true |

## Grep
**Path:** `axe_cli.tools.file:Grep`  
**Description:** Search file content with regular expressions, based on ripgrep

| Parameter | Type | Description |
|-----------|------|-------------|
| pattern | string | Regular expression pattern |
| path | string | Search path, defaults to current directory |
| glob | string | File filter (e.g., *.js) |
| type | string | File type (e.g., py, js, go) |
| output_mode | string | Output mode: files_with_matches (default), content, count_matches |
| -B | int | Show N lines before match |
| -A | int | Show N lines after match |
| -C | int | Show N lines before and after match |
| -n | bool | Show line numbers |
| -i | bool | Case insensitive |
| multiline | bool | Enable multiline matching |
| head_limit | int | Limit output lines |

## WriteFile
**Path:** `axe_cli.tools.file:WriteFile`  
**Description:** Write files. Requires user approval. Absolute paths are required when writing files outside the working directory.

| Parameter | Type | Description |
|-----------|------|-------------|
| path | string | Absolute path |
| content | string | File content |
| mode | string | overwrite (default) or append |

## StrReplaceFile
**Path:** `axe_cli.tools.file:StrReplaceFile`  
**Description:** Edit files using string replacement. Requires user approval. Absolute paths are required when editing files outside the working directory.

| Parameter | Type | Description |
|-----------|------|-------------|
| path | string | Absolute path |
| edit | object/array | Single edit or list of edits |
| edit.old | string | Original string to replace |
| edit.new | string | Replacement string |
| edit.replace_all | bool | Replace all matches, default false |

## CodeSearch
**Path:** `axe_cli.tools.axe:CodeSearch`  
**Description:** Semantic code search powered by axe-dig. Finds code by behavior, not just text matches.

## CodeContext
**Path:** `axe_cli.tools.axe:CodeContext`  
**Description:** Get LLM-ready function summaries with 95% token savings.

## CodeStructure
**Path:** `axe_cli.tools.axe:CodeStructure`  
**Description:** Navigate functions and classes in files or directories.

## CodeImpact
**Path:** `axe_cli.tools.axe:CodeImpact`  
**Description:** Reverse call graph analysis - see who calls a function before refactoring.

## Tool security boundaries

**Working directory restrictions:**

- File reading and writing are typically done within the working directory
- Absolute paths are required when reading files outside the working directory
- Write and edit operations require user approval; absolute paths are required when operating on files outside the working directory

**Approval mechanism:**

The following operations require user approval:

| Operation | Approval required |
|-----------|-------------------|
| Shell command execution | Each execution |
| File write/edit | Each operation |
| MCP tool calls | Each call |
