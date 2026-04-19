"""End-to-end: create a template artifact, then instantiate it via the mediator."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
RUNNER = REPO_ROOT / "artifact-plugin" / "scripts" / "run-provider.py"


def _run(argv: list[str], *, payload: dict, cwd: Path, env: dict) -> tuple[int, dict, str]:
    proc = subprocess.run(
        [sys.executable, str(RUNNER), *argv],
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        cwd=str(cwd),
        env=env,
    )
    try:
        out = json.loads(proc.stdout) if proc.stdout.strip() else {}
    except json.JSONDecodeError:
        out = {"raw": proc.stdout}
    return proc.returncode, out, proc.stderr


def _env(tmp: Path) -> dict:
    env = os.environ.copy()
    env["ARTIFACT_CONFIG_DIR"] = str(tmp / ".artifact-config")
    env["ARTIFACT_CACHE_DIR"] = str(tmp / ".artifact-cache")
    env["ARTIFACT_STATE_DIR"] = str(tmp / ".artifact-state")
    return env


def test_instantiate_design_document_template(tmp_worktree: Path):
    env = _env(tmp_worktree)

    # 1. Create the design-document template artifact in the worktree.
    create_payload = {
        "id": "design-document",
        "name": "design-document",
        "target_scheme": "document",
        "description": "Fill-in markdown design doc.",
        "body": "## {{ title }}\n\nAuthor: {{ author }}\n",
        "inputs": [
            {"name": "title", "type": "string", "required": True},
            {"name": "author", "type": "string", "required": True},
        ],
        "output": {
            "path_template": "docs/design/{{ title | slug }}",
            "create_input": {
                "title": "{{ title }}",
                "authors": ["{{ author }}"],
                "status": "draft",
            },
        },
    }
    code, out, stderr = _run(
        ["artifact-template", "create", "--storage", "file"],
        payload=create_payload,
        cwd=tmp_worktree,
        env=env,
    )
    assert code == 0, stderr
    template_uri = out["uri"]
    assert template_uri == "artifact-template|file/design-document"

    # 2. Instantiate.
    inst_payload = {
        "uri": template_uri,
        "inputs": {"title": "Auth rework", "author": "christian"},
        "target_storage": "file",
    }
    code, out, stderr = _run(
        [template_uri, "instantiate"],
        payload=inst_payload,
        cwd=tmp_worktree,
        env=env,
    )
    assert code == 0, stderr
    produced_uri = out["produced_uri"]
    assert produced_uri == "document|file/docs/design/auth-rework"
    assert len(out["edges"]) == 1

    # 3. Produced files exist.
    body = tmp_worktree / "docs" / "design" / "auth-rework.md"
    content = tmp_worktree / "docs" / "design" / "auth-rework.content.toml"
    assert body.read_text().startswith("## Auth rework")
    assert "Christian" not in content.read_text()  # lower case preserved
    assert "christian" in content.read_text()

    # 4. Edge artifact on disk.
    edge_dir = tmp_worktree / "artifact-edges" / "composed_of"
    assert any(p.suffix == ".json" for p in edge_dir.iterdir())
