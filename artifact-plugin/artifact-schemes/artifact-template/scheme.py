"""artifact-template scheme — templates that produce target-scheme artifacts.

A template carries:
  - jinja2 body (for text artifacts)
  - declared inputs (pydantic-validated)
  - output mapping (path template + literal create_input with jinja fields)
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from artifactlib.kinds import Kind
from artifactlib.scheme import Scheme, Subcommand


class TemplateInput(BaseModel):
    name: str
    type: str = "string"
    required: bool = False
    default: Any = None


class OutputMapping(BaseModel):
    # path under which the target scheme's artifact will be created.
    path_template: str
    # literal dict (values jinja-rendered against inputs) forming the target
    # scheme's `create` input.
    create_input: dict[str, Any] = Field(default_factory=dict)


class ArtifactTemplate(BaseModel):
    name: str
    target_scheme: str
    description: str = ""
    body: str = ""
    inputs: list[TemplateInput] = Field(default_factory=list)
    output: OutputMapping
    contract_version: int = 1


class CreateIn(BaseModel):
    id: str
    name: str
    target_scheme: str
    description: str = ""
    body: str = ""
    inputs: list[TemplateInput] = Field(default_factory=list)
    output: OutputMapping
    contract_version: int = 1


class CreateOut(BaseModel):
    uri: str
    created: bool


class GetIn(BaseModel):
    uri: str


class GetOut(BaseModel):
    uri: str
    content: ArtifactTemplate


class InstantiateIn(BaseModel):
    uri: str
    inputs: dict[str, Any] = Field(default_factory=dict)
    target_storage: str | None = None


class InstantiateOut(BaseModel):
    produced_uri: str
    edges: list[str] = Field(default_factory=list)


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
    target_scheme: str | None = None


class ListOut(BaseModel):
    entries: list[dict[str, Any]]


SCHEME = Scheme(
    kind=Kind.VERTEX,
    name="artifact-template",
    contract_version=1,
    content_model=ArtifactTemplate,
    subcommands={
        "create":      Subcommand(in_model=CreateIn,      out_model=CreateOut,      required=True),
        "get":         Subcommand(in_model=GetIn,         out_model=GetOut,         required=True),
        "instantiate": Subcommand(in_model=InstantiateIn, out_model=InstantiateOut, required=True),
        "delete":      Subcommand(in_model=DeleteIn,      out_model=DeleteOut,      required=False),
        "status":      Subcommand(in_model=StatusIn,      out_model=StatusOut,      required=True),
        "list":        Subcommand(in_model=ListFilter,    out_model=ListOut,        required=True),
    },
)
