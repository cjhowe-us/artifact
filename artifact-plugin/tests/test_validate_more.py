"""Extra artifactlib.validate coverage: exit path + emit_schema_mismatch."""

from __future__ import annotations

import json

import pytest
from artifactlib import validate as validate_mod
from pydantic import BaseModel


class _M(BaseModel):
    id: str
    count: int


def test_validate_happy_path_returns_model():
    inst = validate_mod.validate(_M, {"id": "x", "count": 3})
    assert isinstance(inst, _M)
    assert inst.count == 3


def test_validate_raise_reraises_on_error():
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        validate_mod.validate_raise(_M, {"id": "x"})  # missing count


def test_validate_emits_schema_mismatch_and_exits(capsys: pytest.CaptureFixture[str]):
    with pytest.raises(SystemExit) as exc:
        validate_mod.validate(_M, {"id": "x"})  # missing count
    assert exc.value.code == validate_mod.SCHEMA_MISMATCH_EXIT
    payload = json.loads(capsys.readouterr().out)
    assert payload["error"] == "schema-mismatch"
    assert any(tuple(e["loc"]) == ("count",) for e in payload["details"])
