"""tags metadata scheme — Free-form tags attached to the target artifact."""

from __future__ import annotations

from typing import Any

from artifactlib.kinds import Kind
from artifactlib.scheme import Scheme, Subcommand
from pydantic import BaseModel, Field


class TagsContent(BaseModel):
    target: str
    tags: list[str] = Field(default_factory=list)


class CreateIn(BaseModel):
    target: str
    tags: list[str] = Field(default_factory=list)


class CreateOut(BaseModel):
    uri: str
    created: bool


class GetIn(BaseModel):
    uri: str


class GetOut(BaseModel):
    uri: str
    content: TagsContent


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
    name="tags",
    contract_version=1,
    content_model=TagsContent,
    subcommands={
        "create": Subcommand(in_model=CreateIn, out_model=CreateOut, required=True),
        "get": Subcommand(in_model=GetIn, out_model=GetOut, required=True),
        "delete": Subcommand(in_model=DeleteIn, out_model=DeleteOut, required=False),
        "status": Subcommand(in_model=StatusIn, out_model=StatusOut, required=True),
        "list": Subcommand(in_model=ListFilter, out_model=ListOut, required=True),
    },
)
