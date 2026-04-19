"""tag scheme — Git tag in a GitHub repo."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from artifactlib.kinds import Kind
from artifactlib.scheme import Scheme, Subcommand


class TagContent(BaseModel):
    name: str = ""
    commit_sha: str = ""
    url: str = ""


class CreateIn(BaseModel):
    id: str = ""
    name: str = ""
    commit_sha: str = ""
    url: str = ""


class CreateOut(BaseModel):
    uri: str
    created: bool


class GetIn(BaseModel):
    uri: str


class GetOut(BaseModel):
    uri: str
    content: TagContent


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
    owner: str | None = None
    repo: str | None = None


class ListOut(BaseModel):
    entries: list[dict[str, Any]] = Field(default_factory=list)


SCHEME = Scheme(
    kind=Kind.VERTEX,
    name="tag",
    contract_version=1,
    content_model=TagContent,
    subcommands={
        "create": Subcommand(in_model=CreateIn,   out_model=CreateOut, required=True),
        "get":    Subcommand(in_model=GetIn,      out_model=GetOut,    required=True),
        "status": Subcommand(in_model=StatusIn,   out_model=StatusOut, required=True),
        "list":   Subcommand(in_model=ListFilter, out_model=ListOut,   required=True),
    },
)
