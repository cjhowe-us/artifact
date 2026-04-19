"""Tiny argv helpers for backend/provider scripts.

Backends receive argv shaped like:
    <subcommand> --scheme <s> [--uri <u>] [--data <path|->] [--patch <path|->] ...

Parsing is deliberately simple: every recognized flag takes one value; anything
else passes through. Each backend validates required flags per subcommand.
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, NoReturn

_ONE_VALUE_FLAGS = {
    "--scheme",
    "--uri",
    "--data",
    "--patch",
    "--filter",
    "--owner",
    "--append",
    "--inputs",
    "--target-backend",
    "--backend",
}
_BOOL_FLAGS = {"--check"}


@dataclass
class Args:
    subcommand: str
    flags: dict[str, str] = field(default_factory=dict)
    booleans: set[str] = field(default_factory=set)
    positional: list[str] = field(default_factory=list)

    def get(self, name: str, default: str | None = None) -> str | None:
        return self.flags.get(name, default)

    def require(self, name: str) -> str:
        val = self.flags.get(name)
        if not val:
            die(f"{name} required")
        return val


def parse(argv: list[str]) -> Args:
    if not argv:
        die("subcommand required")
    sub = argv[0]
    rest = argv[1:]
    flags: dict[str, str] = {}
    booleans: set[str] = set()
    positional: list[str] = []
    i = 0
    while i < len(rest):
        tok = rest[i]
        if tok in _ONE_VALUE_FLAGS:
            if i + 1 >= len(rest):
                die(f"{tok} requires a value")
            flags[tok] = rest[i + 1]
            i += 2
        elif tok in _BOOL_FLAGS:
            booleans.add(tok)
            i += 1
        else:
            positional.append(tok)
            i += 1
    return Args(subcommand=sub, flags=flags, booleans=booleans, positional=positional)


def read_json_arg(path_or_dash: str | None) -> dict[str, Any]:
    if not path_or_dash:
        return {}
    raw = sys.stdin.read() if path_or_dash == "-" else Path(path_or_dash).read_text()
    if not raw.strip():
        return {}
    return json.loads(raw)


def emit(obj: dict[str, Any]) -> None:
    sys.stdout.write(json.dumps(obj) + "\n")
    sys.stdout.flush()


def die(msg: str, exit_code: int = 2) -> NoReturn:
    sys.stdout.write(json.dumps({"error": msg}) + "\n")
    sys.stdout.flush()
    sys.exit(exit_code)
