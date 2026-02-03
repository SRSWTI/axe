"""Auto-initialization for axe-dig codebase intelligence.

This module automatically warms and indexes the codebase when axe-cli starts,
ensuring semantic search and code analysis tools are ready to use.
"""

import asyncio
import json
import os
import shutil
import sys
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn

console = Console()


def is_chop_available() -> bool:
    """Check if chop CLI is available in PATH."""
    return shutil.which("chop") is not None


def is_codebase_warmed(work_dir: Path) -> bool:
    """Check if the codebase has been fully warmed with all required indexes."""
    dig_dir = work_dir / ".dig"
    
    if not dig_dir.exists():
        return False
    
    # Check for structural index
    call_graph = dig_dir / "cache" / "call_graph.json"
    if not call_graph.exists():
        return False
    
    # Check for semantic index
    semantic_index = dig_dir / "cache" / "semantic" / "index.faiss"
    semantic_metadata = dig_dir / "cache" / "semantic" / "metadata.json"
    if not semantic_index.exists() or not semantic_metadata.exists():
        return False
    
    return True


def is_daemon_running(work_dir: Path) -> bool:
    """Check if the axe-dig daemon is running."""
    pid_file = work_dir / ".dig" / "daemon.pid"
    if not pid_file.exists():
        return False
    
    try:
        pid = int(pid_file.read_text().strip())
        os.kill(pid, 0)
        return True
    except (ValueError, OSError, ProcessLookupError):
        return False


def create_dig_config(work_dir: Path, model: str) -> None:
    """Create .dig/config.json with daemon and semantic settings.
    
    Args:
        work_dir: The working directory
        model: The embedding model ('minilm' or 'bge-large')
    """
    dig_dir = work_dir / ".dig"
    dig_dir.mkdir(parents=True, exist_ok=True)
    
    config_file = dig_dir / "config.json"
    
    # Map model shortnames to full names
    model_map = {
        "minilm": "sentence-transformers/all-MiniLM-L6-v2",
        "bge-large": "BAAI/bge-large-en-v1.5",
    }
    model_name = model_map.get(model, model)
    
    config = {
        "semantic": {
            "enabled": True,
            "model": model_name,
            "auto_reindex_threshold": 20  # Rebuild after 20 file changes
        },
        "daemon": {
            "auto_start": True,
            "watch_files": True
        }
    }
    
    config_file.write_text(json.dumps(config, indent=2))
    console.print(f"  [dim]Created .dig/config.json[/dim]")


async def run_chop_command(cmd: str, work_dir: Path, env: dict | None = None, timeout: int = 600) -> tuple[bool, str]:
    """Run a chop command and return (success, output)."""
    full_env = os.environ.copy()
    if env:
        full_env.update(env)
    full_env["DIG_AUTO_DOWNLOAD"] = "1"
    
    try:
        process = await asyncio.create_subprocess_shell(
            cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            cwd=str(work_dir),
            env=full_env
        )
        
        try:
            stdout_data, _ = await asyncio.wait_for(process.communicate(), timeout=timeout)
        except asyncio.TimeoutError:
            try:
                process.kill()
            except ProcessLookupError:
                pass
            return False, "Command timed out"
            
        output = stdout_data.decode(errors="replace").strip()
        
        output_lines = []
        for line in output.split("\n"):
            decoded = line.rstrip()
            # Filter out verbose progress bars
            if decoded and not decoded.startswith("Loading weights:") and "Materializing param" not in decoded:
                output_lines.append(decoded)
        
        return process.returncode == 0, "\n".join(output_lines)
    except Exception as e:
        return False, str(e)


def prompt_user_for_init(work_dir: Path) -> tuple[bool, str]:
    """
    Ask the user if they want to initialize axe-dig and which model to use.
    
    Returns:
        (should_init, model_choice) - whether to initialize and which model
    """
    console.print()
    console.print(Panel.fit(
        "[bold]okay so, lets pre-warm your codebase![/bold]\n\n"
        "this builds the analysis stack once.\n"
        "after completion, queries are instant and the daemon handles everything.\n\n"
        "[dim]parsing structure. building call graphs. computing dependencies. encoding semantics.[/dim]\n\n"
        "axe-dig gives llms [bold red]lethal precision.[/bold red]\n"
        "natural language queries. [bold]exact context.[/bold] 95% fewer tokens.\n\n"
        "takes two minutes for typical projects.",
        border_style="white"
    ))
    console.print()
    console.print(f"[dim]this is the directory we gonna work with: {work_dir}[/dim]")
    console.print()
    
    # Check if user wants to initialize
    if not Confirm.ask(
        "[bold]would you like to initialize axe-dig for this project?[/bold]",
        default=True
    ):
        console.print("[dim]ok hmm, skipping axe-dig initialization. you can restart axe-cli later to initialize.[/dim]")
        return False, ""
    
    console.print()
    console.print("[bold]choose digging depth:[/bold]\n")
    console.print("  1) [bold]light-digging[/bold] (recommended)")
    console.print("     • 90mb download")
    console.print("     • 2gb ram during indexing")
    console.print("     • fast. ~1 min for medium projects")
    console.print("     • good precision for most codebases")
    console.print("     • finds: 'jwt validation' → verify_token()")
    console.print()
    console.print("  2) [bold]heavy-digging[/bold] (maximum precision)")
    console.print("     • 1.3gb download")
    console.print("     • 10gb+ ram during indexing")
    console.print("     • slower. 5-15 min for medium projects")
    console.print("     • lethal semantic matching")
    console.print("     • finds: 'connection pooling' → subtle patterns across files")
    console.print()
    
    choice = Prompt.ask(
        "[bold]select depth[/bold]",
        choices=["1", "2"],
        default="1"
    )
    
    model = "minilm" if choice == "1" else "bge-large"
    model_display = "light-digging (sentence-transformers/all-MiniLM-L6-v2)" if model == "minilm" else "heavy-digging (BAAI/bge-large-en-v1.5)"
    
    console.print(f"\n[dim]selected:[/dim] [red]{model_display}[/red]")
    return True, model


async def auto_initialize_codebase(work_dir: Path, model: str | None = None, interactive: bool = True) -> None:
    """
    Automatically initialize the codebase with axe-dig if not already done.
    
    This runs:
    1. chop warm <path> - Build structural index
    2. chop semantic index <path> - Build semantic embeddings
    3. chop daemon start - Start background daemon (non-blocking)
    
    Args:
        work_dir: The working directory to initialize
        model: Embedding model to use ('minilm' or 'bge-large'). If None, will prompt user.
        interactive: Whether to prompt user for confirmation
    """
    if not is_chop_available():
        return
    
    if is_codebase_warmed(work_dir):
        # Already initialized, start daemon in background if not running
        if not is_daemon_running(work_dir):
            # Fire and forget - don't wait for daemon
            asyncio.create_task(_start_daemon_background(work_dir))
        return
    
    # Prompt user if interactive mode
    if interactive:
        should_init, model_choice = prompt_user_for_init(work_dir)
        if not should_init:
            return
        model = model_choice
    
    if model is None:
        model = "minilm"  # Default to minilm for non-interactive
    
    # Map model shortnames to full names
    model_map = {
        "minilm": "sentence-transformers/all-MiniLM-L6-v2",
        "bge-large": "BAAI/bge-large-en-v1.5",
    }
    model_name = model_map.get(model, model)
    
    console.print()
    console.print(Panel.fit(
        "[bold]okay lets do this!, grab a coffee—- axe is now understanding your codebase![/bold]\n"
        f"[dim]Model: {model_name}[/dim]",
        border_style="white"
    ))
    console.print()
    
    # Create config.json with daemon and semantic settings
    create_dig_config(work_dir, model)
    
    with Progress(
        SpinnerColumn(style="bold red"),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(bar_width=None, style="dim white", complete_style="white", finished_style="white"),
        TaskProgressColumn(),
        console=console,
        transient=False
    ) as progress:
        
        # Step 1: Structural indexing
        task1 = progress.add_task("building and understanding the structure..", total=100)
        progress.update(task1, advance=10)
        
        success, output = await run_chop_command(f"chop warm {work_dir}", work_dir)
        
        if success:
            progress.update(task1, advance=90, description="[bold]✓ structure indexed[/bold]")
            for line in output.split("\n"):
                if "Indexed" in line and "files" in line:
                    console.print(f"  [dim]{line}[/dim]")
        else:
            progress.update(task1, description="[red]✗structural indexing failed[/red]")
            console.print(f"  [red]{output[:200]}[/red]")
            return
        
        # Step 2: Semantic indexing
        task2 = progress.add_task("building semantics...", total=100)
        progress.update(task2, advance=10)
        
        cmd = f"chop semantic index {work_dir} --model {model_name}"
        success, output = await run_chop_command(cmd, work_dir, timeout=1800)
        
        if success:
            progress.update(task2, advance=90, description="[bold]✓ ok, semantic index built[/bold]")
            for line in output.split("\n"):
                if "Indexed" in line and "code units" in line:
                    console.print(f"  [dim]{line}[/dim]")
        else:
            progress.update(task2, description="[red]⚠ semantic indexing failed due to some reason, maybe try again?[/red]")
            console.print(f"  [red]{output[:200]}[/red]")
        
        # Step 3: Start daemon
        task3 = progress.add_task("starting daemon...", total=100)
        progress.update(task3, advance=10)
        
        success, output = await run_chop_command(f"chop daemon start --project {work_dir}", work_dir, timeout=30)
        
        if success or "already running" in output.lower():
            progress.update(task3, advance=90, description="[bold]daemon active[/bold]")
        else:
            progress.update(task3, description="[red]⚠ umm, daemon skipped[/red]")
            console.print(f"  [dim]you can run 'chop daemon start --project {work_dir}' manually if needed[/dim]")
    
    console.print()
    console.print(Panel.fit(
        "[bold]axe ready[/bold]\n\n"
        "[dim]tools available:[/dim]\n"
        "  • codesearch - semantic search by behavior\n"
        "  • codecontext - precise function context\n"
        "  • codeimpact - reverse call graph\n"
        "  • codestructure - function and class maps",
        border_style="white"
    ))
    console.print()


async def _start_daemon_background(work_dir: Path) -> None:
    """Start the daemon in the background without blocking."""
    try:
        await run_chop_command(f"chop daemon start --project {work_dir}", work_dir, timeout=10)
    except Exception:
        pass  # Ignore daemon errors


async def ensure_codebase_initialized(work_dir: Path) -> None:
    """
    Ensure the codebase is initialized, running auto-init if needed.
    
    This is the main entry point called from axe-cli startup.
    """
    # Check if stdin is a TTY (interactive terminal)
    interactive = sys.stdin.isatty()
    
    try:
        await auto_initialize_codebase(work_dir, model=None, interactive=interactive)
    except Exception as e:
        console.print(f"[red]⚠ Axe-dig auto-init skipped: {e}[/red]")
