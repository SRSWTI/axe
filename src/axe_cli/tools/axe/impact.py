"""CodeImpact - Find what calls/depends on a symbol (Reverse Call Graph)."""

import asyncio
from typing import override

from kosong.tooling import CallableTool2, ToolReturnValue, ToolOk, ToolError
from pydantic import BaseModel, Field

from axe_cli.soul.agent import Runtime
from axe_cli.tools.utils import ToolResultBuilder


class CodeImpactParams(BaseModel):
    """Parameters for CodeImpact tool."""
    
    symbol: str = Field(
        description="Function, class, or method name to find callers/dependents of."
    )
    path: str = Field(
        description="Project path. Defaults to current directory.",
        default="."
    )


class CodeImpact(CallableTool2[CodeImpactParams]):
    """
    Find what calls/depends on a symbol using axe-dig (Reverse Call Graph).
    
    Runs: `chop impact <symbol> <path>`
    
    Essential for understanding the impact of changes - shows all callers
    so you know what might break if you modify the symbol.
    """
    
    name: str = "CodeImpact"
    params: type[CodeImpactParams] = CodeImpactParams
    
    def __init__(self, runtime: Runtime):
        description = """Find what calls/depends on a symbol (Reverse Call Graph).

Runs: `chop impact <symbol> <path>`

**CRITICAL: Use this BEFORE refactoring or modifying any function to see what will be affected.**

Shows all places that call or depend on a function/class, helping you understand:
- Impact radius of changes (what will break if you modify this)
- Who uses this functionality (all callers)
- Dependencies and consumers of an API
- Safe refactoring scope

**When to use:**
- **BEFORE refactoring** - See what calls this function before changing it
- **BEFORE modifying** - Understand impact before making changes
- Understanding how a utility is used across the codebase
- Finding all consumers of an API or function
- Assessing change impact and blast radius

**examples:**
```bash
chop impact TokenCounter src/axe_cli/
# Result: Only called by get_global_counter() in same file
# Meaning: Safe to refactor - no external dependencies to break
# Output shows caller_count: 1, with full call chain
```

**Output:** JSON with all callers, their locations, and the full call tree.

**Note:** The codebase is automatically indexed on startup.

Example:
```json
{"symbol": "validate_token", "path": "."}
```
"""
        super().__init__(description=description)
        self._runtime = runtime
        self._work_dir = runtime.builtin_args.AXE_WORK_DIR
    
    @override
    async def __call__(self, params: CodeImpactParams) -> ToolReturnValue:
        builder = ToolResultBuilder()
        
        if not params.symbol.strip():
            return ToolError(
                message="Symbol name cannot be empty.",
                brief="Empty symbol"
            )
        
        path = params.path
        if path == ".":
            path = str(self._work_dir)
        
        builder.write(f"🎯 Finding callers of: {params.symbol}\n\n")
        
        try:
            cmd = f"chop impact {params.symbol} {path}"
            
            process = await asyncio.create_subprocess_shell(
                cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(self._work_dir)
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                output = stdout.decode().strip()
                if output:
                    builder.write(output)
                    builder.write("\n")
                    
                    # Count callers for brief
                    lines = [l for l in output.split('\n') if l.strip()]
                    caller_count = len(lines)
                    
                    return builder.ok(brief=f"{caller_count} caller(s) found")
                else:
                    return ToolOk(
                        message=f"No callers found for '{params.symbol}'. It may be unused, a top-level entry point, or the index needs rebuilding.",
                        brief="No callers"
                    )
            else:
                error_msg = stderr.decode().strip() or stdout.decode().strip()
                if "not found" in error_msg.lower():
                    return ToolError(
                        message=f"Symbol '{params.symbol}' not found. Check the symbol name or try running 'chop warm .' in terminal to rebuild the index.",
                        brief="Symbol not found"
                    )
                return ToolError(
                    message=f"Impact analysis failed: {error_msg}",
                    brief="Failed"
                )
                
        except FileNotFoundError:
            return ToolError(
                message="chop command not found. Make sure axe-dig is installed: pip install axe-dig",
                brief="axe-dig not installed"
            )
        except Exception as e:
            return ToolError(
                message=f"Impact analysis failed: {str(e)}",
                brief="Error"
            )
