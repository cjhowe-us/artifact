"""Unit tests for the `gh` CLI wrapper (no network, all subprocess mocked)."""

from __future__ import annotations

import subprocess
import types

import pytest
from artifactlib_gh import gh


def _fake_proc(stdout: str = "", stderr: str = "", returncode: int = 0):
    return types.SimpleNamespace(stdout=stdout, stderr=stderr, returncode=returncode)


def test_run_json_parses_stdout(monkeypatch: pytest.MonkeyPatch):
    def fake_run(argv, **kw):
        assert argv[0] == "gh"
        assert argv[1:] == ["pr", "view", "1", "--json", "number"]
        return _fake_proc(stdout='{"number": 1}\n')

    monkeypatch.setattr(subprocess, "run", fake_run)
    assert gh.run_json(["pr", "view", "1", "--json", "number"]) == {"number": 1}


def test_run_json_empty_stdout_is_none(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(subprocess, "run", lambda *a, **kw: _fake_proc(stdout="   \n"))
    assert gh.run_json(["any"]) is None


def test_run_json_raises_on_nonzero(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *a, **kw: _fake_proc(stderr="boom\n", returncode=2),
    )
    with pytest.raises(gh.GhError) as exc:
        gh.run_json(["pr", "view", "999"])
    assert exc.value.code == 2
    assert exc.value.stderr == "boom\n"


def test_run_returns_stdout(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(subprocess, "run", lambda *a, **kw: _fake_proc(stdout="hi\n"))
    assert gh.run(["auth", "status"]) == "hi\n"


def test_run_raises_gherror(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(
        subprocess, "run", lambda *a, **kw: _fake_proc(stderr="unauth", returncode=1)
    )
    with pytest.raises(gh.GhError):
        gh.run(["api", "/rate_limit"])


def test_run_forwards_stdin_input(monkeypatch: pytest.MonkeyPatch):
    seen = {}

    def fake_run(argv, **kw):
        seen["input"] = kw.get("input")
        return _fake_proc(stdout="ok")

    monkeypatch.setattr(subprocess, "run", fake_run)
    gh.run(["api", "/x", "--input", "-"], input='{"hello": "world"}')
    assert seen["input"] == '{"hello": "world"}'


def test_gherror_message_strips_stderr_whitespace():
    err = gh.GhError("  traceback  \n", 7)
    assert "gh exited 7: traceback" in str(err)
