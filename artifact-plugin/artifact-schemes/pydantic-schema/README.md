# pydantic-schema

Vertex scheme. A Pydantic `BaseModel` subclass — shipped as a `.py` body + `.content.toml` sidecar naming the class.

URI: `pydantic-schema|file/<id>`

Used to validate another scheme's content. Downstream artifacts record a `depends_on` edge to the pydantic-schema
artifact; changes propagate via the graph.
