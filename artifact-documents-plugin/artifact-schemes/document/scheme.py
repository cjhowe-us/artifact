"""document scheme — markdown body + structured content."""

from __future__ import annotations

from typing import Any

from artifactlib.kinds import Kind
from artifactlib.scheme import Scheme, Subcommand
from pydantic import BaseModel, Field


class DocumentContent(BaseModel):
    title: str = ""
    authors: list[str] = Field(default_factory=list)
    status: str = "draft"
    body: str = ""


class CreateIn(BaseModel):
    id: str
    title: str = ""
    authors: list[str] = Field(default_factory=list)
    status: str = "draft"
    body: str = ""


class CreateOut(BaseModel):
    uri: str
    created: bool


class GetIn(BaseModel):
    uri: str


class GetOut(BaseModel):
    uri: str
    content: DocumentContent


class UpdateIn(BaseModel):
    uri: str
    patch: dict[str, Any] = Field(default_factory=dict)


class UpdateOut(BaseModel):
    uri: str
    updated: bool


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
    status: str | None = None


class ListOut(BaseModel):
    entries: list[dict[str, Any]] = Field(default_factory=list)


SCHEME = Scheme(
    kind=Kind.VERTEX,
    name="document",
    contract_version=1,
    content_model=DocumentContent,
    subcommands={
        "create": Subcommand(in_model=CreateIn, out_model=CreateOut, required=True),
        "get": Subcommand(in_model=GetIn, out_model=GetOut, required=True),
        "update": Subcommand(in_model=UpdateIn, out_model=UpdateOut, required=True),
        "delete": Subcommand(in_model=DeleteIn, out_model=DeleteOut, required=False),
        "status": Subcommand(in_model=StatusIn, out_model=StatusOut, required=True),
        "list": Subcommand(in_model=ListFilter, out_model=ListOut, required=True),
    },
    edge_relations=("composed_of", "depends_on", "mentions", "supersedes"),
)
