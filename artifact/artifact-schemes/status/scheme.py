"""status metadata scheme — A single status string attached to the target artifact."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from artifactlib.kinds import Kind
from artifactlib.scheme import Scheme, Subcommand


class StatusContent(BaseModel):
    target: str
    value: str


class CreateIn(BaseModel):
    target: str
    value: str


class CreateOut(BaseModel):
    uri: str
    created: bool


class GetIn(BaseModel):
    uri: str


class GetOut(BaseModel):
    uri: str
    content: StatusContent


class DeleteIn(BaseModel):
    uri: str


class DeleteOut(BaseModel):
    uri: str
    deleted: bool


class StatusIn(BaseModel):
    uri: str


class StatusOut(BaseModel):
    uri: str
    status: str


class ListFilter(BaseModel):
    target: str | None = None


class ListOut(BaseModel):
    entries: list[dict[str, Any]] = Field(default_factory=list)


SCHEME = Scheme(
    kind=Kind.METADATA,
    name="status",
    contract_version=1,
    content_model=StatusContent,
    subcommands={
        "create": Subcommand(in_model=CreateIn,   out_model=CreateOut, required=True),
        "get":    Subcommand(in_model=GetIn,      out_model=GetOut,    required=True),
        "delete": Subcommand(in_model=DeleteIn,   out_model=DeleteOut, required=False),
        "status": Subcommand(in_model=StatusIn,   out_model=StatusOut, required=True),
        "list":   Subcommand(in_model=ListFilter, out_model=ListOut,   required=True),
    },
)
