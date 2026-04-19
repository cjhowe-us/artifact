import pytest
from artifactlib import validate
from pydantic import BaseModel, ValidationError


class Model(BaseModel):
    x: int


def test_validate_raise_ok():
    out = validate.validate_raise(Model, {"x": 3})
    assert out.x == 3


def test_validate_raise_error():
    with pytest.raises(ValidationError):
        validate.validate_raise(Model, {"x": "not-int"})


def test_emit_schema_mismatch(capsys):
    try:
        Model.model_validate({"x": "bad"})
    except ValidationError as exc:
        validate.emit_schema_mismatch(exc)
    out = capsys.readouterr().out
    assert '"error": "schema-mismatch"' in out
    assert '"details"' in out
