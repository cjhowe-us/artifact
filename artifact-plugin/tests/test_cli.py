"""Tests for artifactlib.cli argv parsing + io helpers."""

from __future__ import annotations

import io as io_mod
import json
from pathlib import Path

import pytest
from artifactlib import cli


def test_parse_subcommand_with_flags_and_positionals():
    args = cli.parse(["get", "--scheme", "pr", "--uri", "pr|gh-pr/o/r/1", "extra", "--check"])
    assert args.subcommand == "get"
    assert args.flags == {"--scheme": "pr", "--uri": "pr|gh-pr/o/r/1"}
    assert args.booleans == {"--check"}
    assert args.positional == ["extra"]


def test_parse_empty_argv_dies(capsys: pytest.CaptureFixture[str]):
    with pytest.raises(SystemExit) as exc:
        cli.parse([])
    assert exc.value.code == 2
    assert json.loads(capsys.readouterr().out)["error"] == "subcommand required"


def test_parse_flag_missing_value(capsys: pytest.CaptureFixture[str]):
    with pytest.raises(SystemExit):
        cli.parse(["get", "--scheme"])
    assert "--scheme requires a value" in capsys.readouterr().out


def test_args_get_defaults_and_require():
    args = cli.parse(["list", "--scheme", "issue"])
    assert args.get("--scheme") == "issue"
    assert args.get("--uri") is None
    assert args.get("--uri", "fallback") == "fallback"
    assert args.require("--scheme") == "issue"


def test_args_require_missing_dies(capsys: pytest.CaptureFixture[str]):
    args = cli.parse(["list"])
    with pytest.raises(SystemExit):
        args.require("--scheme")
    assert "--scheme required" in capsys.readouterr().out


def test_read_json_arg_empty_string():
    assert cli.read_json_arg(None) == {}
    assert cli.read_json_arg("") == {}


def test_read_json_arg_from_file(tmp_path: Path):
    p = tmp_path / "payload.json"
    p.write_text('{"k": 1}')
    assert cli.read_json_arg(str(p)) == {"k": 1}


def test_read_json_arg_whitespace_file_returns_empty(tmp_path: Path):
    p = tmp_path / "empty.json"
    p.write_text("   \n")
    assert cli.read_json_arg(str(p)) == {}


def test_read_json_arg_from_stdin(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr("sys.stdin", io_mod.StringIO('{"hello": "world"}'))
    assert cli.read_json_arg("-") == {"hello": "world"}


def test_emit_writes_json_with_newline(capsys: pytest.CaptureFixture[str]):
    cli.emit({"status": "ok"})
    out = capsys.readouterr().out
    assert out.endswith("\n")
    assert json.loads(out) == {"status": "ok"}


def test_die_writes_error_json_and_exits(capsys: pytest.CaptureFixture[str]):
    with pytest.raises(SystemExit) as exc:
        cli.die("boom", exit_code=5)
    assert exc.value.code == 5
    assert json.loads(capsys.readouterr().out) == {"error": "boom"}
