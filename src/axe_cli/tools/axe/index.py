"""CodeIndex - Build/rebuild semantic search embeddings."""

import asyncio
import os
from typing import override

from kosong.tooling import CallableTool2, ToolReturnValue, ToolOk, ToolError
from pydantic import BaseModel, Field

from axe_cli.soul.agent import Runtime
from axe_cli.tools.utils import ToolResultBuilder


class CodeIndexParams(BaseModel):
    """Parameters for CodeIndex tool."""
    
    path: str = Field(
        description="Project path to index semantically. Defaults to current directory.",
        default="."
    )
    model: str | None = Field(
        description="Embedding model to use. Options: 'bge-large' (default, ~1.3GB), 'minilm' (smaller, ~90MB). Use 'minilm' for faster downloads.",
        default=None
    )


class CodeIndex(CallableTool2[CodeIndexParams]):
    """
    Build/rebuild the semantic search index (embeddings) using axe-dig.
    
    Runs: `chop semantic index <path>`
    Creates vector embeddings for natural language code search.
    """
    
    name: str = "CodeIndex"
    params: type[CodeIndexParams] = CodeIndexParams
    
    def __init__(self, runtime: Runtime):
        description = """Build/rebuild semantic search embeddings using axe-dig.

Runs: `chop semantic index <path>`

Creates vector embeddings for natural language code search:
- Indexes function signatures, docstrings, call patterns, and code
- Stores vectors in .dig/cache/semantic.faiss

**Embedding Models:**
- `bge-large` (default): BAAI/bge-large-en-v1.5 (~1.3GB, best quality)
- `minilm`: sentence-transformers/all-MiniLM-L6-v2 (~90MB, faster)

**When to use:**
- After CodeWarm if semantic search returns poor results
- When embeddings are stale after many file changes
- To enable CodeSearch functionality

**Troubleshooting:**
- If model download fails, set env var `DIG_AUTO_DOWNLOAD=1`
- For faster setup, use `model: "minilm"`

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
    async def __call__(self, params: CodeIndexParams) -> ToolReturnValue:
        builder = ToolResultBuilder()
        
        path = params.path
        if path == ".":
            path = str(self._work_dir)
        
        builder.write(f"🧠 Building semantic index: {path}\n")
        
        # Build command with optional model flag
        cmd = f"chop semantic index {path}"
        if params.model:
            model_map = {
                "minilm": "sentence-transformers/all-MiniLM-L6-v2",
                "bge-large": "BAAI/bge-large-en-v1.5",
            }
            model_name = model_map.get(params.model, params.model)
            cmd += f" --model {model_name}"
            builder.write(f"Using model: {model_name}\n")
        
        builder.write("Creating embeddings (this may take a few minutes)...\n\n")
        
        # Set DIG_AUTO_DOWNLOAD=1 to allow auto-download
        env = os.environ.copy()
        env["DIG_AUTO_DOWNLOAD"] = "1"
        
        try:
            process = await asyncio.create_subprocess_shell(
                cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
                cwd=str(self._work_dir),
                env=env
            )
            
            # Stream output
            while True:
                line = await process.stdout.readline()
                if not line:
                    break
                decoded = line.decode().rstrip()
                # Filter out progress bars and verbose loading messages
                if decoded and not decoded.startswith("Loading weights:") and not "Materializing param" in decoded:
                    builder.write(f"{decoded}\n")
            
            await process.wait()
            
            if process.returncode == 0:
                builder.write("\n✅ Semantic index built!\n")
                builder.write("You can now use CodeSearch for natural language queries.\n")
                return builder.ok(brief="Semantic index ready")
            else:
                return builder.error(
                    f"Semantic indexing failed with exit code {process.returncode}",
                    brief="Index failed"
                )
                
        except FileNotFoundError:
            return ToolError(
                message="chop command not found. Make sure axe-dig is installed: pip install axe-dig",
                brief="axe-dig not installed"
            )
        except Exception as e:
            return ToolError(
                message=f"Semantic indexing failed: {str(e)}",
                brief="Error"
            )
