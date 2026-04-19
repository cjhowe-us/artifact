#!/usr/bin/env python3
"""CLI entry point for artifact subcommands.

Usage:
    run-provider.py <URI-or-scheme> <subcommand> [options...]

Options:
    --uri <u>          Artifact URI (scheme|storage/path). If given as first arg, inferred.
    --storage <name>   Storage override (only when no URI).
    --data <path|->    JSON payload file (or "-" for stdin). If omitted, stdin is read (if non-tty).
    --inputs <path|->  Alias for --data.
    --target-scheme <s> For the artifact-template `instantiate` subcommand.

URI format: <scheme>|<storage>/<path>.

Reads JSON payload from --data (or stdin), dispatches via the scheme mediator,
writes JSON result to stdout. Exits:

- 0   success
- 2   dispatch error (missing storage, unknown subcommand, etc.)
- 3   schema mismatch (pydantic validation failed)
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from artifactlib import registry, uri as uri_mod  # noqa: E402
from artifactlib.provider import dispatch  # noqa: E402
from artifactlib.validate import SCHEMA_MISMATCH_EXIT, emit_schema_mismatch  # noqa: E402

from pydantic import ValidationError  # noqa: E402


def _ensure_registry() -> None:
    if registry.registry_path().is_file():
        return
    import subprocess

    discover = HERE / "discover.py"
    if discover.is_file():
        subprocess.run(
            [sys.executable, str(discover)],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )


def _read_payload(path_or_dash: str | None) -> dict:
    if path_or_dash:
        raw = sys.stdin.read() if path_or_dash == "-" else Path(path_or_dash).read_text()
    elif not sys.stdin.isatty():
        raw = sys.stdin.read()
    else:
        raw = ""
    if not raw.strip():
        return {}
    return json.loads(raw)


def _die(msg: str, code: int = 2) -> None:
    sys.stdout.write(json.dumps({"error": msg}) + "\n")
    sys.stdout.flush()
    sys.exit(code)


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        _die("URI-or-scheme and subcommand required")
    first = argv[0]
    subcommand = argv[1]
    rest = argv[2:]

    uri_str: str | None = None
    storage_override: str | None = None
    data_path: str | None = None
    extra: dict = {}
    i = 0
    while i < len(rest):
        tok = rest[i]
        if tok in ("--uri",):
            uri_str = rest[i + 1]
            i += 2
        elif tok == "--storage":
            storage_override = rest[i + 1]
            i += 2
        elif tok in ("--data", "--inputs"):
            data_path = rest[i + 1]
            i += 2
        elif tok == "--target-scheme":
            extra["target_scheme"] = rest[i + 1]
            i += 2
        else:
            i += 1

    _ensure_registry()

    parsed = uri_mod.try_parse(first)
    if parsed is not None:
        scheme_name = parsed.scheme
        uri_str = first
    else:
        scheme_name = first

    payload = _read_payload(data_path)
    if extra:
        payload = {**payload, **extra}

    try:
        out = dispatch(
            scheme_name=scheme_name,
            subcommand=subcommand,
            payload=payload,
            uri_str=uri_str,
            storage_override=storage_override,
        )
    except ValidationError as exc:
        emit_schema_mismatch(exc)
        return SCHEMA_MISMATCH_EXIT
    except (
        registry.RegistryMissing,
        registry.NoStorageForScheme,
        registry.AmbiguousStorage,
    ) as exc:
        _die(str(exc))
        return 2
    except Exception as exc:  # noqa: BLE001
        _die(f"{type(exc).__name__}: {exc}")
        return 2

    sys.stdout.write(json.dumps(out) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
