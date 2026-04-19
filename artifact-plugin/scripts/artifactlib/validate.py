"""Pydantic validation helpers + canonical schema-mismatch error shape."""

from __future__ import annotations

import sys
from typing import Any

from pydantic import BaseModel, ValidationError


SCHEMA_MISMATCH_EXIT = 3


def validate(model_cls: type[BaseModel], data: dict[str, Any]) -> BaseModel:
    """Validate `data` against `model_cls`. On failure, emit schema-mismatch
    JSON to stdout and exit with SCHEMA_MISMATCH_EXIT.
    """
    try:
        return model_cls.model_validate(data)
    except ValidationError as exc:
        emit_schema_mismatch(exc)
        sys.exit(SCHEMA_MISMATCH_EXIT)


def validate_raise(model_cls: type[BaseModel], data: dict[str, Any]) -> BaseModel:
    """Same as `validate` but re-raises instead of exiting (for library callers)."""
    return model_cls.model_validate(data)


def emit_schema_mismatch(exc: ValidationError) -> None:
    import json

    payload = {"error": "schema-mismatch", "details": exc.errors()}
    sys.stdout.write(json.dumps(payload) + "\n")
    sys.stdout.flush()
