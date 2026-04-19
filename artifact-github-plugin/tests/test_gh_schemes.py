"""All gh-* schemes load and expose the expected subcommands."""

from __future__ import annotations

from pathlib import Path

from artifactlib import scheme as scheme_mod
from artifactlib.kinds import Kind


SCHEMES = Path(__file__).resolve().parent.parent / "artifact-schemes"


def _load(name: str):
    return scheme_mod.load_scheme(SCHEMES / name / "scheme.py")


def test_all_schemes_loadable():
    for name in ("pr", "issue", "release", "milestone", "tag", "branch", "gist"):
        s = _load(name)
        assert s.kind is Kind.VERTEX
        assert s.name == name
        assert set(s.subcommands) >= {"create", "get", "status", "list"}


def test_pr_content_fields():
    s = _load("pr")
    instance = s.content_model(title="T", body="B", state="open")
    assert instance.title == "T"
    assert instance.state == "open"
