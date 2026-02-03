Replace specific strings within a specified file.

**Tips:**
- Only use this tool on text files.
- Multi-line strings are supported.
- Can specify a single edit or a list of edits in one call.
- You should prefer this tool over WriteFile tool and Shell `sed` command.
- Ensure `old` content matches the file EXACTLY, including all whitespace and indentation.
- Ensure `old` is unique in the file (or use `replace_all=True`).
