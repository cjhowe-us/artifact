"""issue scheme — GitHub issue."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from artifactlib.kinds import Kind
from artifactlib.scheme import Scheme, Subcommand


class IssueContent(BaseModel):
    title: str = ""
    body: str = ""
    state: str = "open"
    url: str = ""
    number: int | None = None
    labels: list[str] = Field(default_factory=list)


class CreateIn(BaseModel):
    id: str = ""
    title: str = ""
    body: str = ""
    state: str = "open"
    url: str = ""
    number: int | None = None
    labels: list[str] = Field(default_factory=list)


class CreateOut(BaseModel):
    uri: str
    created: bool


class GetIn(BaseModel):
    uri: str


class GetOut(BaseModel):
    uri: str
    content: IssueContent


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
    name="issue",
    contract_version=1,
    content_model=IssueContent,
    subcommands={
        "create": Subcommand(in_model=CreateIn,   out_model=CreateOut, required=True),
        "get":    Subcommand(in_model=GetIn,      out_model=GetOut,    required=True),
        "status": Subcommand(in_model=StatusIn,   out_model=StatusOut, required=True),
        "list":   Subcommand(in_model=ListFilter, out_model=ListOut,   required=True),
    },
)
