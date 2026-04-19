"""conversation scheme — a transient or persisted conversation thread."""

from __future__ import annotations

from typing import Any

from artifactlib.kinds import Kind
from artifactlib.scheme import Scheme, Subcommand
from pydantic import BaseModel, Field


class Message(BaseModel):
    role: str  # "user" | "assistant" | "system"
    content: str
    ts: str | None = None


class Conversation(BaseModel):
    title: str = ""
    messages: list[Message] = Field(default_factory=list)
    attrs: dict[str, Any] = Field(default_factory=dict)


class CreateIn(BaseModel):
    id: str
    title: str = ""
    messages: list[Message] = Field(default_factory=list)
    attrs: dict[str, Any] = Field(default_factory=dict)


class CreateOut(BaseModel):
    uri: str
    created: bool


class GetIn(BaseModel):
    uri: str


class GetOut(BaseModel):
    uri: str
    content: Conversation


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
    pass


class ListOut(BaseModel):
    entries: list[dict[str, Any]] = Field(default_factory=list)


SCHEME = Scheme(
    kind=Kind.VERTEX,
    name="conversation",
    contract_version=1,
    content_model=Conversation,
    subcommands={
        "create": Subcommand(in_model=CreateIn, out_model=CreateOut, required=True),
        "get": Subcommand(in_model=GetIn, out_model=GetOut, required=True),
        "delete": Subcommand(in_model=DeleteIn, out_model=DeleteOut, required=False),
        "status": Subcommand(in_model=StatusIn, out_model=StatusOut, required=True),
        "list": Subcommand(in_model=ListFilter, out_model=ListOut, required=True),
    },
)
