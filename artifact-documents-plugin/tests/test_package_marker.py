"""Presence + version marker for the artifact-documents-plugin package."""

from __future__ import annotations

import sys
from pathlib import Path


def test_artifactlib_docs_version_matches_pyproject():
    scripts = Path(__file__).resolve().parent.parent / "scripts"
    if str(scripts) not in sys.path:
        sys.path.insert(0, str(scripts))
    import artifactlib_docs

    assert artifactlib_docs.__version__ == "2.0.2"
