"""Graph queries over edge artifacts."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path


REPO = Path(__file__).resolve().parent.parent
RUNNER = REPO / "scripts" / "run-provider.py"


def _make_edge(tmp: Path, env: dict, relation: str, source: str, target: str) -> str:
    proc = subprocess.run(
        [sys.executable, str(RUNNER), relation, "create", "--storage", "file"],
        input=json.dumps({"source": source, "target": target}),
        text=True,
        capture_output=True,
        cwd=str(tmp),
        env=env,
    )
    assert proc.returncode == 0, proc.stderr
    return json.loads(proc.stdout)["uri"]


def test_graph_find_returns_edges(tmp_worktree: Path):
    env = os.environ.copy()
    env["ARTIFACT_CACHE_DIR"] = str(tmp_worktree / ".artifact-cache")
    env["ARTIFACT_CONFIG_DIR"] = str(tmp_worktree / ".artifact-config")

    _make_edge(tmp_worktree, env, "composed_of", "doc|file/a", "doc|file/b")
    _make_edge(tmp_worktree, env, "composed_of", "doc|file/c", "doc|file/b")
    _make_edge(tmp_worktree, env, "depends_on", "doc|file/a", "doc|file/x")

    # graph.find --relation composed_of --target doc|file/b → 2 results
    from artifactlib import graph

    os.environ.update(env)
    edges = graph.find(relation="composed_of", target="doc|file/b")
    assert len(edges) == 2
    sources = {e.source for e in edges}
    assert sources == {"doc|file/a", "doc|file/c"}

    # find for depends_on
    edges = graph.find(relation="depends_on", target="doc|file/x")
    assert len(edges) == 1
    assert edges[0].source == "doc|file/a"
