"""CodeStructure - List functions/classes in a file or directory."""

import asyncio
from typing import override

from kosong.tooling import CallableTool2, ToolReturnValue, ToolOk, ToolError
from pydantic import BaseModel, Field

from axe_cli.soul.agent import Runtime
from axe_cli.tools.utils import ToolResultBuilder


class CodeStructureParams(BaseModel):
    """Parameters for CodeStructure tool."""
    
    path: str = Field(
        description="File or directory path to analyze structure."
    )
    lang: str | None = Field(
        description="Programming language filter (auto-detected if not specified). Options: python, typescript, javascript, go, rust, java, c, cpp, ruby, php.",
        default=None
    )


class CodeStructure(CallableTool2[CodeStructureParams]):
    """
    List functions, classes, and methods in a file or directory using axe-dig.
    
    Runs: `chop structure <path> [--lang <language>]`
    
    Provides a quick overview of code structure without reading entire files.
    """
    
    name: str = "CodeStructure"
    params: type[CodeStructureParams] = CodeStructureParams
    
    def __init__(self, runtime: Runtime):
        description = """List functions, classes, and methods in a file/directory.

Runs: `chop structure <path> [--lang <language>]`

Returns a structured overview of the codebase including:
- Function names and signatures
- Class definitions
- Method listings
- File organization

**When to use:**
- Getting an overview of unfamiliar code
- Finding where specific functionality might be
- Understanding project organization
- Before using CodeSearch or CodeContext

**Supported Languages:** Python, TypeScript, JavaScript, Go, Rust, Java, C, C++, Ruby, PHP, C#, Kotlin, Scala, Swift, Lua, Elixir

Example:
```json
{"path": "src/auth/"}
```

```json
{"path": "main.py", "lang": "python"}
```
"""
        super().__init__(description=description)
        self._runtime = runtime
        self._work_dir = runtime.builtin_args.AXE_WORK_DIR
    
    @override
    async def __call__(self, params: CodeStructureParams) -> ToolReturnValue:
        builder = ToolResultBuilder()
        
        if not params.path.strip():
            return ToolError(
                message="Path cannot be empty.",
                brief="Empty path"
            )
        
        builder.write(f"📂 Analyzing structure: {params.path}\n\n")
        
        try:
            cmd = f"chop structure {params.path}"
            if params.lang:
                cmd += f" --lang {params.lang}"
            
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
                    return builder.ok(brief="Structure analysis complete")
                else:
                    return ToolOk(
                        message=f"No symbols found in '{params.path}'. The path may be empty or contain no parseable code.",
                        brief="No symbols"
                    )
            else:
                error_msg = stderr.decode().strip() or stdout.decode().strip()
                if "not found" in error_msg.lower() or "does not exist" in error_msg.lower():
                    return ToolError(
                        message=f"Path '{params.path}' not found.",
                        brief="Path not found"
                    )
                return ToolError(
                    message=f"Structure analysis failed: {error_msg}",
                    brief="Failed"
                )
                
        except FileNotFoundError:
            return ToolError(
                message="chop command not found. Make sure axe-dig is installed: pip install axe-dig",
                brief="axe-dig not installed"
            )
        except Exception as e:
            return ToolError(
                message=f"Structure analysis failed: {str(e)}",
                brief="Error"
            )
