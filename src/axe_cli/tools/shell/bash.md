Execute a ${SHELL} command. Use this tool to explore the filesystem, run scripts, get system information, install packages, etc.

**IMPORTANT - When to use other tools instead:**
- **For editing text files**: ALWAYS use `StrReplaceFile` tool instead of shell commands like `sed`, `awk`, `perl`, or text redirection. The `StrReplaceFile` tool is more reliable, cross-platform, and shows diffs for approval.
- **For writing new files**: Use `WriteFile` tool instead of shell redirection (`>`, `>>`, `tee`).
- **For reading file contents**: Use `ReadFile` tool instead of `cat`.
- **For searching within files**: Use `Grep` tool instead of `grep` or `rg` commands.

**Output:**
The stdout and stderr will be combined and returned as a string. The output may be truncated if it is too long. If the command failed, the exit code will be provided in a system tag.

**Guidelines for safety and security:**
- Each shell tool call will be executed in a fresh shell environment. The shell variables, current working directory changes, and the shell history is not preserved between calls.
- The tool call will return after the command is finished. You shall not use this tool to execute an interactive command or a command that may run forever. For possibly long-running commands, you shall set `timeout` argument to a reasonable value.
- Avoid using `..` to access files or directories outside of the working directory.
- Avoid modifying files outside of the working directory unless explicitly instructed to do so.
- Never run commands that require superuser privileges unless explicitly instructed to do so.

**Guidelines for efficiency:**
- For multiple related commands, use `&&` to chain them in a single call, e.g. `cd /path && ls -la`
- Use `;` to run commands sequentially regardless of success/failure
- Use `||` for conditional execution (run second command only if first fails)
- Use pipe operations (`|`) and redirections (`>`, `>>`) to chain input and output between commands
- Always quote file paths containing spaces with double quotes (e.g., cd "/path with spaces/")
- Use `if`, `case`, `for`, `while` control flows to execute complex logic in a single call.
- Verify directory structure before create/edit/delete files or directories to reduce the risk of failure.

**Commands available:**
- Shell environment: cd, pwd, export, unset, env
- File system operations: ls, find, mkdir, rm, cp, mv, touch, chmod, chown
- File viewing: cat (use ReadFile tool instead for better results), head, tail, diff, patch
- Text processing: sort, uniq, wc (do NOT use sed, awk, perl for file editing - use StrReplaceFile tool)
- System information/operations: ps, kill, top, df, free, uname, whoami, id, date
- Network operations: curl, wget, ping, telnet, ssh
- Archive operations: tar, zip, unzip
- Package management: pip, npm, apt, brew, etc.
- Build/run commands: make, npm run, python, node, etc.
- Other: Other commands available in the shell environment. Check the existence of a command by running `which <command>` before using it.
