"""In-process coverage for the top-level script entry points (graph.py, run-provider.py)."""

from __future__ import annotations

import importlib.util
import io as _io
import json
import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"


def _load_script(name: str):
    spec = importlib.util.spec_from_file_location(f"_{name}", SCRIPTS / f"{name}.py")
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ---------- graph.py ---------------------------------------------------------


def _install_graph_fake(monkeypatch: pytest.MonkeyPatch, edges):
    from artifactlib import graph as graph_lib

    def fake_list_edges(**kw):
        return edges

    monkeypatch.setattr(graph_lib, "list_edges", fake_list_edges)
    monkeypatch.setattr(graph_lib, "expand", lambda **kw: edges)
    monkeypatch.setattr(graph_lib, "find", lambda **kw: edges)


def test_graph_script_no_args_errors(capsys: pytest.CaptureFixture[str]):
    mod = _load_script("graph")
    assert mod.main([]) == 2
    assert "usage:" in capsys.readouterr().err


def test_graph_script_unknown_subcommand(capsys: pytest.CaptureFixture[str]):
    mod = _load_script("graph")
    assert mod.main(["bogus"]) == 2
    assert "unknown subcommand" in capsys.readouterr().err


def test_graph_script_expand(capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch):
    from artifactlib import graph as graph_lib

    _install_graph_fake(monkeypatch, [graph_lib.Edge("u", "a", "b", "composed_of", {})])
    mod = _load_script("graph")
    assert mod.main(["expand", "--uri", "a", "--depth", "2", "--relation", "composed_of"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload[0]["target"] == "b"


def test_graph_script_find(capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch):
    from artifactlib import graph as graph_lib

    _install_graph_fake(monkeypatch, [graph_lib.Edge("u", "a", "b", "closes", {})])
    mod = _load_script("graph")
    assert mod.main(["find", "--relation", "closes", "--target", "b"]) == 0


def test_graph_script_list(capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch):
    _install_graph_fake(monkeypatch, [])
    mod = _load_script("graph")
    assert mod.main(["list", "--source", "a"]) == 0


# ---------- run-provider.py ---------------------------------------------------


def _install_dispatch(monkeypatch: pytest.MonkeyPatch, result=None, raises=None):
    from artifactlib import provider as provider_mod

    def fake(**kw):
        if raises is not None:
            raise raises
        return result if result is not None else {"uri": kw.get("uri_str") or "x|y/z", "ok": True}

    monkeypatch.setattr(provider_mod, "dispatch", fake)


def _install_registry(monkeypatch: pytest.MonkeyPatch):
    from artifactlib import registry

    # Pretend registry is already built so _ensure_registry short-circuits.
    monkeypatch.setattr(
        registry, "registry_path", lambda: Path("/dev/null").parent / "registry.json"
    )
    # Force registry_path().is_file() → True by pointing at the run-provider.py itself.
    monkeypatch.setattr(registry, "registry_path", lambda: SCRIPTS / "run-provider.py")


def test_run_provider_missing_args_exits(capsys: pytest.CaptureFixture[str]):
    mod = _load_script("run-provider")
    with pytest.raises(SystemExit):
        mod.main([])
    assert "URI-or-scheme and subcommand required" in capsys.readouterr().out


def test_run_provider_dispatches_scheme_form(
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
):
    _install_registry(monkeypatch)
    _install_dispatch(monkeypatch, result={"answer": 42})
    monkeypatch.setattr(sys, "stdin", _io.StringIO(""))
    mod = _load_script("run-provider")
    assert mod.main(["issue", "list", "--storage", "gh-issue"]) == 0
    assert json.loads(capsys.readouterr().out) == {"answer": 42}


def test_run_provider_dispatches_uri_form(
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
):
    _install_registry(monkeypatch)
    _install_dispatch(monkeypatch, result={"uri": "pr|gh-pr/o/r/1"})
    monkeypatch.setattr(sys, "stdin", _io.StringIO(""))
    mod = _load_script("run-provider")
    assert mod.main(["pr|gh-pr/o/r/1", "get"]) == 0


def test_run_provider_payload_from_stdin(
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
):
    _install_registry(monkeypatch)
    _install_dispatch(monkeypatch, result={"echoed": True})
    monkeypatch.setattr(sys, "stdin", _io.StringIO('{"id": "probe"}\n'))

    mod = _load_script("run-provider")
    assert mod.main(["status", "create", "--data", "-"]) == 0


def test_run_provider_payload_from_file(
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch, tmp_path: Path
):
    payload = tmp_path / "p.json"
    payload.write_text('{"k": 1}')
    _install_registry(monkeypatch)
    _install_dispatch(monkeypatch, result={"ok": True})
    monkeypatch.setattr(sys, "stdin", _io.StringIO(""))

    mod = _load_script("run-provider")
    assert mod.main(["status", "create", "--inputs", str(payload)]) == 0


def test_run_provider_surface_validation_error(
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
):
    from pydantic import BaseModel, ValidationError

    class _M(BaseModel):
        need: str

    try:
        _M.model_validate({})
    except ValidationError as exc:
        err = exc

    _install_registry(monkeypatch)
    _install_dispatch(monkeypatch, raises=err)
    monkeypatch.setattr(sys, "stdin", _io.StringIO(""))

    mod = _load_script("run-provider")
    assert mod.main(["status", "create"]) == 3
    payload = json.loads(capsys.readouterr().out)
    assert payload["error"] == "schema-mismatch"


def test_run_provider_registry_missing_exits_2(
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
):
    from artifactlib import registry

    _install_registry(monkeypatch)
    _install_dispatch(monkeypatch, raises=registry.NoStorageForScheme("issue"))
    monkeypatch.setattr(sys, "stdin", _io.StringIO(""))
    mod = _load_script("run-provider")
    with pytest.raises(SystemExit) as exc:
        mod.main(["issue", "get"])
    assert exc.value.code == 2


def test_run_provider_generic_exception_exits_2(
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
):
    _install_registry(monkeypatch)
    _install_dispatch(monkeypatch, raises=RuntimeError("kaboom"))
    monkeypatch.setattr(sys, "stdin", _io.StringIO(""))
    mod = _load_script("run-provider")
    with pytest.raises(SystemExit) as exc:
        mod.main(["status", "get"])
    assert exc.value.code == 2
    assert "RuntimeError: kaboom" in capsys.readouterr().out


def test_run_provider_with_target_scheme_flag(monkeypatch: pytest.MonkeyPatch):
    """--target-scheme merges into payload."""
    seen = {}

    def fake_dispatch(**kw):
        seen.update(kw)
        return {"ok": True}

    from artifactlib import provider as provider_mod

    monkeypatch.setattr(provider_mod, "dispatch", fake_dispatch)
    _install_registry(monkeypatch)
    monkeypatch.setattr(sys, "stdin", _io.StringIO(""))
    mod = _load_script("run-provider")
    assert mod.main(["artifact-template", "instantiate", "--target-scheme", "document"]) == 0
    assert seen["payload"]["target_scheme"] == "document"
