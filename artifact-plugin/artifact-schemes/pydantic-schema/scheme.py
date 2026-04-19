"""pydantic-schema scheme — artifacts that are pydantic BaseModel classes.

The body `.py` file is loaded via `importlib.util.spec_from_file_location` and
the class named by `content.class_name` is extracted. Callers assert it's a
`BaseModel` subclass before using it to validate another scheme's content.
"""

from __future__ import annotations

from typing import Any

from artifactlib.kinds import Kind
from artifactlib.scheme import Scheme, Subcommand
from pydantic import BaseModel, Field


class PydanticSchemaContent(BaseModel):
    class_name: str
    body: str = ""  # the .py source
    description: str = ""
    contract_version: int = 1


class CreateIn(BaseModel):
    id: str
    class_name: str
    body: str
    description: str = ""
    contract_version: int = 1


class CreateOut(BaseModel):
    uri: str
    created: bool


class GetIn(BaseModel):
    uri: str


class GetOut(BaseModel):
    uri: str
    content: PydanticSchemaContent


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
    name="pydantic-schema",
    contract_version=1,
    content_model=PydanticSchemaContent,
    subcommands={
        "create": Subcommand(in_model=CreateIn, out_model=CreateOut, required=True),
        "get": Subcommand(in_model=GetIn, out_model=GetOut, required=True),
        "delete": Subcommand(in_model=DeleteIn, out_model=DeleteOut, required=False),
        "status": Subcommand(in_model=StatusIn, out_model=StatusOut, required=True),
        "list": Subcommand(in_model=ListFilter, out_model=ListOut, required=True),
    },
)
