"""Cover the SessionStart dep-probe hook."""

from __future__ import annotations

import importlib
import importlib.util
import sys
from pathlib import Path

import pytest

HOOK = Path(__file__).resolve().parent.parent / "hooks" / "sessionstart-discover.py"


def _load_hook_module():
    spec = importlib.util.spec_from_file_location("_hook", HOOK)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_hook_returns_zero_with_install_hint_when_deps_missing(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
):
    hook = _load_hook_module()

    real_find_spec = importlib.util.find_spec

    def fake_find_spec(name: str, *a, **kw):
        return None if name == "pydantic" else real_find_spec(name, *a, **kw)

    monkeypatch.setattr(importlib.util, "find_spec", fake_find_spec)
    assert hook.main() == 0
    assert "install deps" in capsys.readouterr().err


def test_hook_dispatches_to_discover_when_deps_present(monkeypatch: pytest.MonkeyPatch):
    hook = _load_hook_module()

    # Inject a fake `discover` module so the import inside main() resolves
    # without running real registry discovery.
    import types

    fake = types.ModuleType("discover")
    calls = []

    def fake_main():
        calls.append(True)
        return 7

    fake.main = fake_main  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "discover", fake)

    assert hook.main() == 7
    assert calls == [True]
