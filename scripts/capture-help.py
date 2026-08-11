#!/usr/bin/env python3
"""Capture colour-preserving ``--help`` output into markdown files.

Runs the built CLI for the root command, the ``nexus-dashboard`` product
group, and each verb, then refreshes matching ` ```ansi ` blocks in place.
GitHub renders ` ```ansi ` fenced blocks with their ANSI SGR colours, so the
help stays colourful *and* copy-pasteable — no binary screenshot required.

Destinations (marker ``help:<name>`` → file):

* ``root`` → ``docs/commands/README.md``
* ``nexus-dashboard`` → ``README.md`` (product-tier help only)
* verb markers → ``docs/commands/nexus-dashboard/<verb>.md``

Colour is forced deterministically:

* each command runs under a pseudo-terminal (``pty``) so Typer/rich believe
  they are talking to a real terminal and emit raw ANSI escape codes;
* ``FORCE_COLOR=1`` and a fixed ``COLUMNS`` / pty window width give stable,
  reproducible wrapping;
* every capture runs from an isolated empty temp directory so a local
  ``nac-analytics.yaml`` cannot interfere and the output is pristine.

Usage::

    uv run python scripts/capture-help.py          # refresh all blocks
    uv run python scripts/capture-help.py --check  # CI drift detection

Standard library only.
"""

from __future__ import annotations

import argparse
import fcntl
import os
import pty
import re
import struct
import subprocess
import sys
import tempfile
import termios
from pathlib import Path

# A fixed terminal geometry keeps wrapping identical across machines.
WIDTH = 100
HEIGHT = 40
ESC = b"\x1b"

REPO_ROOT = Path(__file__).resolve().parent.parent
ND_COMMANDS = REPO_ROOT / "docs" / "commands" / "nexus-dashboard"

ND = "nexus-dashboard"

# (marker name, destination file, argv after the program name).
CAPTURES: tuple[tuple[str, Path, list[str]], ...] = (
    ("root", REPO_ROOT / "docs" / "commands" / "README.md", ["--help"]),
    ("nexus-dashboard", REPO_ROOT / "README.md", [ND, "--help"]),
    ("prechange", ND_COMMANDS / "prechange.md", [ND, "prechange", "--help"]),
    ("delta", ND_COMMANDS / "delta.md", [ND, "delta", "--help"]),
    ("snapshots", ND_COMMANDS / "snapshots.md", [ND, "snapshots", "--help"]),
    ("compliance", ND_COMMANDS / "compliance.md", [ND, "compliance", "--help"]),
    ("doctor", ND_COMMANDS / "doctor.md", [ND, "doctor", "--help"]),
)


def capture(args: list[str]) -> str:
    """Run ``nac-analytics <args>`` under a pty and return its raw ANSI output."""
    master, slave = pty.openpty()
    winsize = struct.pack("HHHH", HEIGHT, WIDTH, 0, 0)
    fcntl.ioctl(slave, termios.TIOCSWINSZ, winsize)

    env = dict(os.environ)
    env["FORCE_COLOR"] = "1"
    env["COLUMNS"] = str(WIDTH)
    env["LINES"] = str(HEIGHT)
    env["TERM"] = "xterm-256color"
    env.pop("NO_COLOR", None)

    bootstrap = (
        "import sys; sys.argv[0] = 'nac-analytics'; "
        "from nac_analytics.cli import main; main()"
    )

    chunks: list[bytes] = []
    with tempfile.TemporaryDirectory() as workdir:
        proc = subprocess.Popen(
            [sys.executable, "-c", bootstrap, *args],
            stdin=slave,
            stdout=slave,
            stderr=slave,
            cwd=workdir,
            env=env,
            close_fds=True,
        )
        os.close(slave)
        try:
            while True:
                try:
                    data = os.read(master, 65536)
                except OSError:
                    break
                if not data:
                    break
                chunks.append(data)
        finally:
            os.close(master)
        code = proc.wait()

    raw = b"".join(chunks)
    if code != 0:
        sys.stderr.write(raw.decode("utf-8", "replace"))
        raise SystemExit(
            f"`nac-analytics {' '.join(args)}` exited {code}; cannot capture help."
        )
    if ESC not in raw:
        raise SystemExit(
            f"No ANSI escape codes in output of `nac-analytics {' '.join(args)}`; "
            "colour was stripped — refusing to write a colourless block."
        )
    text = raw.decode("utf-8", "replace").replace("\r\n", "\n").replace("\r", "\n")
    return text.strip("\n")


def block_for(name: str, ansi: str) -> str:
    """Return the full marker-delimited ansi fenced block."""
    begin = f"<!-- BEGIN: help:{name} -->"
    end = f"<!-- END: help:{name} -->"
    return f"{begin}\n\n```ansi\n{ansi}\n```\n\n{end}"


def extract_block(text: str, name: str) -> str | None:
    """Return the marker-delimited block for ``help:<name>``, or None."""
    begin = f"<!-- BEGIN: help:{name} -->"
    end = f"<!-- END: help:{name} -->"
    pattern = re.compile(re.escape(begin) + r".*?" + re.escape(end), re.DOTALL)
    match = pattern.search(text)
    return match.group(0) if match else None


def replace_block(text: str, name: str, ansi: str) -> str:
    """Replace the content between the help:<name> markers with a fresh block."""
    begin = f"<!-- BEGIN: help:{name} -->"
    end = f"<!-- END: help:{name} -->"
    pattern = re.compile(re.escape(begin) + r".*?" + re.escape(end), re.DOTALL)
    if not pattern.search(text):
        raise SystemExit(
            f"{name}: no '{begin}' / '{end}' markers; add them to the destination file."
        )
    return pattern.sub(lambda _match: block_for(name, ansi), text, count=1)


def process_capture(name: str, path: Path, args: list[str], *, check: bool) -> bool:
    """Capture one help screen. Returns True when the on-disk block is stale."""
    if not path.is_file():
        raise SystemExit(f"{name}: destination not found at {path}")

    ansi = capture(args)
    fresh = block_for(name, ansi)
    text = path.read_text(encoding="utf-8")
    existing = extract_block(text, name)

    if existing == fresh:
        print(f"ok help:{name} ({path.relative_to(REPO_ROOT)})")
        return False

    if check:
        print(f"stale help:{name} ({path.relative_to(REPO_ROOT)})", file=sys.stderr)
        return True

    if existing is None:
        raise SystemExit(
            f"{name}: {path.relative_to(REPO_ROOT)} has no help:{name} markers."
        )
    path.write_text(replace_block(text, name, ansi), encoding="utf-8")
    print(f"captured help:{name} → {path.relative_to(REPO_ROOT)} ({len(ansi)} bytes)")
    return True


def main() -> None:
    parser = argparse.ArgumentParser(description="Capture CLI --help into markdown.")
    parser.add_argument(
        "--check",
        action="store_true",
        help="Verify captured blocks match the live CLI; exit 1 on drift.",
    )
    args = parser.parse_args()

    stale = False
    for name, path, argv in CAPTURES:
        if process_capture(name, path, argv, check=args.check):
            stale = True

    if args.check and stale:
        raise SystemExit(
            "Captured help is out of date; run: uv run python scripts/capture-help.py"
        )


if __name__ == "__main__":
    main()
