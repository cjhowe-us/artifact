"""preferences scheme — user preferences (default storages, WIP caps, tutor flags)."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from artifactlib.kinds import Kind
from artifactlib.scheme import Scheme, Subcommand


class Preferences(BaseModel):
    # storage.<scheme>.default — default storage per scheme
    storage: dict[str, dict[str, Any]] = Field(default_factory=dict)
    # wip.<scheme> = int
    wip: dict[str, int] = Field(default_factory=dict)
    # arbitrary extras
    extra: dict[str, Any] = Field(default_factory=dict)


class CreateIn(BaseModel):
    id: str = "user"
    storage: dict[str, dict[str, Any]] = Field(default_factory=dict)
    wip: dict[str, int] = Field(default_factory=dict)
    extra: dict[str, Any] = Field(default_factory=dict)


class CreateOut(BaseModel):
    uri: str
    created: bool


class GetIn(BaseModel):
    uri: str


class GetOut(BaseModel):
    uri: str
    content: Preferences


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
    name="preferences",
    contract_version=1,
    content_model=Preferences,
    subcommands={
        "create": Subcommand(in_model=CreateIn,   out_model=CreateOut, required=True),
        "get":    Subcommand(in_model=GetIn,      out_model=GetOut,    required=True),
        "delete": Subcommand(in_model=DeleteIn,   out_model=DeleteOut, required=False),
        "status": Subcommand(in_model=StatusIn,   out_model=StatusOut, required=True),
        "list":   Subcommand(in_model=ListFilter, out_model=ListOut,   required=True),
    },
)
