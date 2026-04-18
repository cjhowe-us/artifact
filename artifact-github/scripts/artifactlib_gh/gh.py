"""Minimal `gh` CLI wrapper shared by gh-* storages.

All calls use ``subprocess.run([...])`` (never ``shell=True``). Stdout parsed
as JSON when the command was asked for JSON. Errors surface as
``GhError(stderr, exit_code)``.
"""

from __future__ import annotations

import json
import subprocess
from typing import Any


class GhError(RuntimeError):
    def __init__(self, stderr: str, code: int) -> None:
        self.stderr = stderr
        self.code = code
        super().__init__(f"gh exited {code}: {stderr.strip()}")


def run_json(argv: list[str], *, input: str | None = None) -> Any:
    proc = subprocess.run(
        ["gh", *argv],
        input=input,
        text=True,
        capture_output=True,
    )
    if proc.returncode != 0:
        raise GhError(proc.stderr, proc.returncode)
    if not proc.stdout.strip():
        return None
    return json.loads(proc.stdout)


def run(argv: list[str], *, input: str | None = None) -> str:
    proc = subprocess.run(
        ["gh", *argv],
        input=input,
        text=True,
        capture_output=True,
    )
    if proc.returncode != 0:
        raise GhError(proc.stderr, proc.returncode)
    return proc.stdout
