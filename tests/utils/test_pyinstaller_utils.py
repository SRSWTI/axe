from __future__ import annotations

import platform
import sys
from pathlib import Path

from inline_snapshot import snapshot


def test_pyinstaller_datas():
    from axe_cli.utils.pyinstaller import datas

    project_root = Path(__file__).parent.parent.parent
    python_version = f"{sys.version_info.major}.{sys.version_info.minor}"
    site_packages = f".venv/lib/python{python_version}/site-packages"
    datas = [
        (
            Path(path)
            .relative_to(project_root)
            .as_posix()
            .replace(".venv/Lib/site-packages", site_packages),
            Path(dst).as_posix(),
        )
        for path, dst in datas
    ]

    assert sorted(datas) == snapshot(
        [
            (
                f"{site_packages}/dateparser/data/dateparser_tz_cache.pkl",
                "dateparser/data",
            ),
            (
                f"{site_packages}/fastmcp/../fastmcp-2.12.5.dist-info/INSTALLER",
                "fastmcp/../fastmcp-2.12.5.dist-info",
            ),
            (
                f"{site_packages}/fastmcp/../fastmcp-2.12.5.dist-info/METADATA",
                "fastmcp/../fastmcp-2.12.5.dist-info",
            ),
            (
                f"{site_packages}/fastmcp/../fastmcp-2.12.5.dist-info/RECORD",
                "fastmcp/../fastmcp-2.12.5.dist-info",
            ),
            (
                f"{site_packages}/fastmcp/../fastmcp-2.12.5.dist-info/REQUESTED",
                "fastmcp/../fastmcp-2.12.5.dist-info",
            ),
            (
                f"{site_packages}/fastmcp/../fastmcp-2.12.5.dist-info/WHEEL",
                "fastmcp/../fastmcp-2.12.5.dist-info",
            ),
            (
                f"{site_packages}/fastmcp/../fastmcp-2.12.5.dist-info/entry_points.txt",
                "fastmcp/../fastmcp-2.12.5.dist-info",
            ),
            (
                f"{site_packages}/fastmcp/../fastmcp-2.12.5.dist-info/licenses/LICENSE",
                "fastmcp/../fastmcp-2.12.5.dist-info/licenses",
            ),
            (
                "src/axe_cli/CHANGELOG.md",
                "axe_cli",
            ),
            ("src/axe_cli/agents/default/agent.yaml", "axe_cli/agents/default"),
            ("src/axe_cli/agents/default/sub.yaml", "axe_cli/agents/default"),
            ("src/axe_cli/agents/default/system.md", "axe_cli/agents/default"),
            ("src/axe_cli/agents/okabe/agent.yaml", "axe_cli/agents/okabe"),
            (
                f"src/axe_cli/deps/bin/{'rg.exe' if platform.system() == 'Windows' else 'rg'}",
                "axe_cli/deps/bin",
            ),
            ("src/axe_cli/prompts/compact.md", "axe_cli/prompts"),
            ("src/axe_cli/prompts/init.md", "axe_cli/prompts"),
            (
                "src/axe_cli/skills/axe-cli-help/SKILL.md",
                "axe_cli/skills/axe-cli-help",
            ),
            (
                "src/axe_cli/skills/skill-creator/SKILL.md",
                "axe_cli/skills/skill-creator",
            ),
            (
                "src/axe_cli/tools/dmail/dmail.md",
                "axe_cli/tools/dmail",
            ),
            (
                "src/axe_cli/tools/file/glob.md",
                "axe_cli/tools/file",
            ),
            (
                "src/axe_cli/tools/file/grep.md",
                "axe_cli/tools/file",
            ),
            (
                "src/axe_cli/tools/file/read.md",
                "axe_cli/tools/file",
            ),
            (
                "src/axe_cli/tools/file/read_media.md",
                "axe_cli/tools/file",
            ),
            (
                "src/axe_cli/tools/file/replace.md",
                "axe_cli/tools/file",
            ),
            (
                "src/axe_cli/tools/file/write.md",
                "axe_cli/tools/file",
            ),
            ("src/axe_cli/tools/multiagent/create.md", "axe_cli/tools/multiagent"),
            ("src/axe_cli/tools/multiagent/task.md", "axe_cli/tools/multiagent"),
            ("src/axe_cli/tools/shell/bash.md", "axe_cli/tools/shell"),
            ("src/axe_cli/tools/shell/powershell.md", "axe_cli/tools/shell"),
            (
                "src/axe_cli/tools/think/think.md",
                "axe_cli/tools/think",
            ),
            (
                "src/axe_cli/tools/todo/set_todo_list.md",
                "axe_cli/tools/todo",
            ),
            (
                "src/axe_cli/tools/web/fetch.md",
                "axe_cli/tools/web",
            ),
            (
                "src/axe_cli/tools/web/search.md",
                "axe_cli/tools/web",
            ),
        ]
    )


def test_pyinstaller_hiddenimports():
    from axe_cli.utils.pyinstaller import hiddenimports

    assert sorted(hiddenimports) == snapshot(
        [
            "axe_cli.tools",
            "axe_cli.tools.axe",
            "axe_cli.tools.axe.auto_init",
            "axe_cli.tools.axe.context",
            "axe_cli.tools.axe.impact",
            "axe_cli.tools.axe.index",
            "axe_cli.tools.axe.prewarm",
            "axe_cli.tools.axe.search",
            "axe_cli.tools.axe.structure",
            "axe_cli.tools.axe.warm",
            "axe_cli.tools.display",
            "axe_cli.tools.dmail",
            "axe_cli.tools.file",
            "axe_cli.tools.file.glob",
            "axe_cli.tools.file.grep_local",
            "axe_cli.tools.file.read",
            "axe_cli.tools.file.read_media",
            "axe_cli.tools.file.replace",
            "axe_cli.tools.file.utils",
            "axe_cli.tools.file.write",
            "axe_cli.tools.multiagent",
            "axe_cli.tools.multiagent.create",
            "axe_cli.tools.multiagent.task",
            "axe_cli.tools.shell",
            "axe_cli.tools.test",
            "axe_cli.tools.think",
            "axe_cli.tools.todo",
            "axe_cli.tools.utils",
            "axe_cli.tools.web",
            "axe_cli.tools.web.fetch",
            "axe_cli.tools.web.search",
        ]
    )
