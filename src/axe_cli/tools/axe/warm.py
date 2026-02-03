"""CodeWarm - Index/re-index the codebase structure."""

import asyncio
from typing import override

from kosong.tooling import CallableTool2, ToolReturnValue, ToolOk, ToolError
from pydantic import BaseModel, Field

from axe_cli.soul.agent import Runtime
from axe_cli.tools.utils import ToolResultBuilder


class CodeWarmParams(BaseModel):
    """Parameters for CodeWarm tool."""
    
    path: str = Field(
        description="Project path to index. Defaults to current directory.",
        default="."
    )


class CodeWarm(CallableTool2[CodeWarmParams]):
    """
    Index/re-index the codebase structure using axe-dig.
    
    Runs: `chop warm <path>`
    
    This builds the 5-layer structural analysis without semantic embeddings.
    Faster than CodePrewarm, use when you only need structural analysis.
    """
    
    name: str = "CodeWarm"
    params: type[CodeWarmParams] = CodeWarmParams
    
    def __init__(self, runtime: Runtime):
        description = """Index/re-index the codebase using axe-dig (fast mode).

Runs: `chop warm <path>`

Builds 5-layer structural analysis:
- Layer 1: AST (functions, classes, methods)
- Layer 2: Call Graph (who calls what)
- Layer 3: Control Flow Graph (complexity)
- Layer 4: Data Flow Graph (variable tracking)
- Layer 5: Program Dependence Graph (slicing)

**Output:** "Indexed N files, found M edges"

**When to use:**
- Quick re-index after file changes
- When you don't need semantic search
- Before using CodeContext or CodeImpact

**Difference from CodePrewarm:** Does NOT build semantic embeddings (faster).

Example:
```json
{"path": "."}
```
"""
        super().__init__(description=description)
        self._runtime = runtime
        self._work_dir = runtime.builtin_args.AXE_WORK_DIR
    
    @override
    async def __call__(self, params: CodeWarmParams) -> ToolReturnValue:
        builder = ToolResultBuilder()
        
        path = params.path
        if path == ".":
            path = str(self._work_dir)
        
        builder.write(f"🔄 Warming codebase: {path}\n\n")
        
        try:
            cmd = f"chop warm {path}"
            
            process = await asyncio.create_subprocess_shell(
                cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
                cwd=str(self._work_dir)
            )
            
            # Stream output
            while True:
                line = await process.stdout.readline()
                if not line:
                    break
                decoded = line.decode().rstrip()
                builder.write(f"{decoded}\n")
            
            await process.wait()
            
            if process.returncode == 0:
                builder.write("\n✅ Indexing complete!\n")
                return builder.ok(brief="Index complete")
            else:
                return builder.error(
                    f"Indexing failed with exit code {process.returncode}",
                    brief="Index failed"
                )
                
        except FileNotFoundError:
            return ToolError(
                message="chop command not found. Make sure axe-dig is installed: pip install axe-dig",
                brief="axe-dig not installed"
            )
        except Exception as e:
            return ToolError(
                message=f"Indexing failed: {str(e)}",
                brief="Error"
            )
