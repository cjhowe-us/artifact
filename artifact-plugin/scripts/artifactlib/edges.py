"""Factory for edge-kind schemes.

Every edge relation (composed_of, depends_on, validates, …) is its own scheme
with an identical content shape:

    { source: URI, target: URI, relation: str, attrs: dict }

`make_edge_scheme("composed_of")` returns the `Scheme` object for the
`composed_of` scheme. Each scheme.py under `artifact-schemes/<relation>/`
is a one-liner that calls this factory.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, create_model

from .kinds import Kind
from .scheme import Scheme, Subcommand


def make_edge_scheme(relation: str) -> Scheme:
    EdgeContent = create_model(
        f"{_camel(relation)}EdgeContent",
        source=(str, ...),
        target=(str, ...),
        relation=(str, relation),
        attrs=(dict[str, Any], Field(default_factory=dict)),
    )

    CreateIn = create_model(
        f"{_camel(relation)}EdgeCreateIn",
        source=(str, ...),
        target=(str, ...),
        attrs=(dict[str, Any], Field(default_factory=dict)),
    )

    class CreateOut(BaseModel):
        uri: str
        created: bool

    class GetIn(BaseModel):
        uri: str

    GetOut = create_model(
        f"{_camel(relation)}EdgeGetOut",
        uri=(str, ...),
        content=(EdgeContent, ...),
    )

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
        source: str | None = None
        target: str | None = None

    class ListOut(BaseModel):
        entries: list[dict[str, Any]]

    return Scheme(
        kind=Kind.EDGE,
        name=relation,
        contract_version=1,
        content_model=EdgeContent,
        subcommands={
            "create": Subcommand(in_model=CreateIn, out_model=CreateOut, required=True),
            "get": Subcommand(in_model=GetIn, out_model=GetOut, required=True),
            "delete": Subcommand(in_model=DeleteIn, out_model=DeleteOut, required=False),
            "status": Subcommand(in_model=StatusIn, out_model=StatusOut, required=True),
            "list": Subcommand(in_model=ListFilter, out_model=ListOut, required=True),
        },
    )


def _camel(s: str) -> str:
    return "".join(part.capitalize() for part in s.replace("-", "_").split("_"))
