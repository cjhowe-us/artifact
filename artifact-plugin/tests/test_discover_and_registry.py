import json
import os
from pathlib import Path

import pytest

import discover as discover_mod  # type: ignore


def test_discover_finds_schemes_and_storages(registry: dict):
    names = {e["name"] for e in registry["entries"] if e["entry_type"] == "artifact-scheme"}
    assert "artifact-template" in names
    assert "composed_of" in names
    assert "preferences" in names

    storage_names = {e["name"] for e in registry["entries"] if e["entry_type"] == "artifact-storage"}
    assert "file" in storage_names
    assert "user-config" in storage_names


def test_registry_has_no_warnings_on_clean_repo(registry: dict):
    assert registry.get("warnings") == []


def test_registry_scheme_entries_carry_storages(registry: dict):
    c = next(
        e for e in registry["entries"]
        if e["entry_type"] == "artifact-scheme" and e["name"] == "composed_of"
    )
    assert any(s.get("name") == "file" for s in c["storages"])
