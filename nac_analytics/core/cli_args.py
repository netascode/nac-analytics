"""Pre-Typer argv handling shared across products.

``--config`` is resolved before Typer runs (it selects the YAML file that seeds
the environment), so it is stripped from argv here rather than declared as a
Typer option.
"""

from __future__ import annotations

from pathlib import Path

CONFIG_OPTION = "--config"


def strip_config_option(argv: list[str]) -> tuple[Path | None, list[str]]:
    """Remove a root-level ``--config`` option from ``argv`` before Typer runs."""
    remaining: list[str] = []
    config_path: Path | None = None
    index = 0
    while index < len(argv):
        arg = argv[index]
        if arg == CONFIG_OPTION and index + 1 < len(argv):
            config_path = Path(argv[index + 1])
            index += 2
            continue
        if arg.startswith(f"{CONFIG_OPTION}="):
            config_path = Path(arg.split("=", 1)[1])
            index += 1
            continue
        remaining.append(arg)
        index += 1
    return config_path, remaining
