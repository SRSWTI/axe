"""CodePrewarm - Full codebase pre-warming with axe-dig indexing."""

import asyncio
import os
from typing import override

from kosong.tooling import CallableTool2, ToolReturnValue, ToolOk, ToolError
from pydantic import BaseModel, Field

from axe_cli.soul.agent import Runtime
from axe_cli.tools.utils import ToolResultBuilder


class CodePrewarmParams(BaseModel):
    """Parameters for CodePrewarm tool."""
    
    path: str = Field(
        description="Project path to prewarm. Defaults to current directory.",
        default="."
    )
    model: str | None = Field(
        description="Embedding model for semantic index. Options: 'bge-large' (default, ~1.3GB), 'minilm' (smaller, ~90MB). Use 'minilm' for faster downloads.",
        default=None
    )


class CodePrewarm(CallableTool2[CodePrewarmParams]):
    """
    PRE-WARM the codebase using axe-dig.
    
    Runs: `chop warm .` + `chop semantic index .`
    
    This runs full structural analysis and builds semantic embeddings.
    Run this on any new/existing project first before using other code analysis tools.
    """
    
    name: str = "CodePrewarm"
    params: type[CodePrewarmParams] = CodePrewarmParams
    
    def __init__(self, runtime: Runtime):
        description = """PRE-WARM the codebase using axe-dig semantic engine.

Runs full analysis pipeline:
1. `chop warm <path>` - Builds 5-layer code analysis (AST, Call Graph, CFG, DFG, PDG)
2. `chop semantic index <path>` - Creates semantic embeddings for natural language search

**Embedding Models:**
- `bge-large` (default): BAAI/bge-large-en-v1.5 (~1.3GB, best quality)
- `minilm`: sentence-transformers/all-MiniLM-L6-v2 (~90MB, faster)

**When to use:**
- On any NEW project before starting work
- After major refactoring or pulling large changes
- When semantic search returns stale results

**Output:** Creates .dig/ directory with:
- `.dig/cache/` - Structural analysis cache
- `.dig/cache/semantic.faiss` - Vector embeddings

Example:
```json
{"path": "."}
```

```json
{"path": ".", "model": "minilm"}
```
"""
        super().__init__(description=description)
        self._runtime = runtime
        self._work_dir = runtime.builtin_args.AXE_WORK_DIR
    
    @override
    async def __call__(self, params: CodePrewarmParams) -> ToolReturnValue:
        builder = ToolResultBuilder()
        
        # Resolve path relative to work directory
        path = params.path
        if path == ".":
            path = str(self._work_dir)
        
        builder.write(f"🔥 Starting pre-warm for: {path}\n")
        builder.write("This may take a few minutes for large codebases...\n\n")
        
        # Set DIG_AUTO_DOWNLOAD=1 to allow auto-download of embedding models
        env = os.environ.copy()
        env["DIG_AUTO_DOWNLOAD"] = "1"
        
        try:
            # Step 1: Run chop warm for structural analysis
            builder.write("📊 Step 1/2: Building structural index (`chop warm`)...\n")
            cmd_warm = f"chop warm {path}"
            
            process = await asyncio.create_subprocess_shell(
                cmd_warm,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
                cwd=str(self._work_dir),
                env=env
            )
            
            while True:
                line = await process.stdout.readline()
                if not line:
                    break
                decoded = line.decode().rstrip()
                builder.write(f"  {decoded}\n")
            
            await process.wait()
            
            if process.returncode != 0:
                return builder.error(
                    f"Structural indexing failed with exit code {process.returncode}",
                    brief="Warm failed"
                )
            
            # Step 2: Run semantic indexing
            builder.write("\n🧠 Step 2/2: Building semantic embeddings (`chop semantic index`)...\n")
            cmd_semantic = f"chop semantic index {path}"
            
            # Add model flag if specified
            if params.model:
                model_map = {
                    "minilm": "sentence-transformers/all-MiniLM-L6-v2",
                    "bge-large": "BAAI/bge-large-en-v1.5",
                }
                model_name = model_map.get(params.model, params.model)
                cmd_semantic += f" --model {model_name}"
                builder.write(f"  Using model: {model_name}\n")
            
            process2 = await asyncio.create_subprocess_shell(
                cmd_semantic,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
                cwd=str(self._work_dir),
                env=env
            )
            
            while True:
                line = await process2.stdout.readline()
                if not line:
                    break
                decoded = line.decode().rstrip()
                # Filter out progress bars and verbose loading messages
                if decoded and not decoded.startswith("Loading weights:") and not "Materializing param" in decoded:
                    builder.write(f"  {decoded}\n")
            
            await process2.wait()
            
            if process2.returncode == 0:
                builder.write("\n✅ Pre-warming complete!\n")
                builder.write("You can now use CodeSearch, CodeContext, and CodeImpact tools.\n")
                return builder.ok(brief="Pre-warm complete")
            else:
                # Semantic indexing failed but structural is done
                builder.write("\n⚠️ Structural index built, but semantic indexing failed.\n")
                builder.write("CodeContext and CodeImpact will work, but CodeSearch may not.\n")
                builder.write("Tip: Try with model='minilm' for smaller download.\n")
                return builder.ok(brief="Partial pre-warm")
                
        except FileNotFoundError:
            return ToolError(
                message="chop command not found. Make sure axe-dig is installed: pip install axe-dig",
                brief="axe-dig not installed"
            )
        except Exception as e:
            return ToolError(
                message=f"Pre-warming failed: {str(e)}",
                brief="Error"
            )

