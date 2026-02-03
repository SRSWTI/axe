"""
Axe-Dig Tools for Axe CLI

These tools integrate the axe-dig codebase intelligence engine (`chop` CLI v1.6.0+)
with Axe CLI, providing semantic code search, impact analysis, and structural analysis.

## Auto-Initialization

When axe-cli starts, it automatically:
1. Checks if the codebase is indexed
2. Prompts you to select an embedding model (MiniLM or BGE-Large)
3. Builds structural and semantic indexes
4. Starts the background daemon

You don't need to manually run indexing commands.

## Quick Reference: `chop` Commands

| Tool          | chop Command              | Purpose                                    |
|---------------|---------------------------|--------------------------------------------|
| CodeSearch    | `chop semantic search`    | Natural language code search               |
| CodeContext   | `chop context <symbol>`   | LLM-optimized context extraction           |
| CodeStructure | `chop structure <path>`   | List functions/classes in files            |
| CodeImpact    | `chop impact <symbol>`    | Find all callers (reverse call graph)      |

## Workflow

1. **Search code:** Use `CodeSearch` with natural language queries
2. **Understand a function:** Use `CodeContext` for token-optimized summary
3. **Before refactoring:** Use `CodeImpact` to see what might break
4. **Explore structure:** Use `CodeStructure` to list functions/classes

## Additional `chop` Commands (run via terminal)

- `chop warm <path>` - Rebuild structural index after file changes
- `chop semantic index <path>` - Rebuild semantic embeddings
- `chop tree <path>` - Show file tree
- `chop extract <file>` - Full AST info for a file
- `chop cycles <path>` - Detect recursive loops
- `chop path <from> <to> <path>` - Find shortest call path between functions
- `chop dead <path> --entry <func>` - Find dead code unreachable from entry
- `chop cfg <file> <func>` - Control flow graph for a function
- `chop slice <file> <func> <line>` - Program slicing (backward slice)
- `chop daemon start/stop/status` - Background daemon management

## Troubleshooting

**Indexes are stale:**
- Run `chop warm .` in terminal to rebuild structural index
- Run `chop semantic index .` to rebuild semantic embeddings

**Re-initialize from scratch:**
- Delete the `.dig` folder and restart Axe-cli
"""

from .prewarm import CodePrewarm
from .warm import CodeWarm
from .index import CodeIndex
from .search import CodeSearch
from .context import CodeContext
from .structure import CodeStructure
from .impact import CodeImpact
from .auto_init import ensure_codebase_initialized, is_codebase_warmed, is_chop_available

# Only export the tools that should be available to the LLM agent
# CodePrewarm, CodeWarm, and CodeIndex are kept as files but not exposed
# since auto-initialization handles indexing on startup
__all__ = [
    "CodeSearch",
    "CodeContext",
    "CodeStructure",
    "CodeImpact",
    "ensure_codebase_initialized",
    "is_codebase_warmed",
    "is_chop_available",
]
