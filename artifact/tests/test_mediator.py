"""End-to-end mediator dispatch via run-provider.py (stdin JSON in / JSON out)."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path


REPO = Path(__file__).resolve().parent.parent
RUNNER = REPO / "scripts" / "run-provider.py"


def _run(argv: list[str], *, payload: dict | None, cwd: Path, env: dict) -> tuple[int, str, str]:
    proc = subprocess.run(
        [sys.executable, str(RUNNER), *argv],
        input=json.dumps(payload) if payload is not None else "",
        text=True,
        capture_output=True,
        cwd=str(cwd),
        env=env,
    )
    return proc.returncode, proc.stdout, proc.stderr


def _env(tmp_worktree: Path) -> dict:
    env = os.environ.copy()
    env["ARTIFACT_CONFIG_DIR"] = str(tmp_worktree / ".artifact-config")
    env["ARTIFACT_CACHE_DIR"] = str(tmp_worktree / ".artifact-cache")
    env["ARTIFACT_STATE_DIR"] = str(tmp_worktree / ".artifact-state")
    return env


def test_edge_create_and_get_end_to_end(tmp_worktree: Path):
    env = _env(tmp_worktree)

    # create
    code, stdout, stderr = _run(
        ["composed_of", "create", "--storage", "file"],
        payload={"source": "doc|file/a", "target": "doc|file/b"},
        cwd=tmp_worktree,
        env=env,
    )
    assert code == 0, stderr
    out = json.loads(stdout)
    assert out["created"] is True
    uri = out["uri"]

    # get
    code, stdout, stderr = _run(
        [uri, "get"],
        payload={"uri": uri},
        cwd=tmp_worktree,
        env=env,
    )
    assert code == 0, stderr
    got = json.loads(stdout)
    assert got["content"]["source"] == "doc|file/a"
    assert got["content"]["target"] == "doc|file/b"


def test_schema_mismatch_returns_exit_3(tmp_worktree: Path):
    env = _env(tmp_worktree)
    code, stdout, stderr = _run(
        ["composed_of", "create", "--storage", "file"],
        payload={"source": 123, "target": "ok"},  # source must be str
        cwd=tmp_worktree,
        env=env,
    )
    assert code == 3
    out = json.loads(stdout)
    assert out["error"] == "schema-mismatch"
    assert isinstance(out["details"], list)


def test_unknown_storage(tmp_worktree: Path):
    env = _env(tmp_worktree)
    code, stdout, _ = _run(
        ["composed_of", "create", "--storage", "nonexistent"],
        payload={"source": "a|b/c", "target": "d|e/f"},
        cwd=tmp_worktree,
        env=env,
    )
    assert code == 2
    assert "error" in json.loads(stdout)
