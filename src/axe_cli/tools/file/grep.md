Find exact file locations and content using ripgrep.

**How to use:**
- **Get file + line numbers**: Set `output_mode="content"` and `line_number=True`
- **Literal patterns**: Use exact strings (e.g., `pattern="def validate_token"`)
- **Regex patterns**: Use for complex searches (e.g., `pattern="class \\w+Manager"`)
- **Copy exact content**: The output shows EXACT content with whitespace - copy this for StrReplaceFile

**Examples:**
```json
{"pattern": "def process_data", "output_mode": "content", "line_number": true}
→ Returns: utils/data.py:42:    def process_data(input: str) -> dict:

{"pattern": "import \\w+ from", "output_mode": "content", "line_number": true}
→ Returns: Multiple imports with exact line numbers
```

**Tips:**
- Use ripgrep syntax: escape braces like `\\{` to search for `{`
- Default `output_mode` is `files_with_matches` (no line numbers or content)
- For StrReplaceFile workflow: always use `output_mode="content"` + `line_number=true`
