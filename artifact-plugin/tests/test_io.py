"""Tests for artifactlib.io — atomic writes, git root, locks."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
from artifactlib import io


def test_git_root_inside_worktree(tmp_worktree: Path):
    root = io.git_root(tmp_worktree)
    assert root.resolve() == tmp_worktree.resolve()


def test_git_root_outside_worktree_returns_cwd(tmp_path: Path):
    assert io.git_root(tmp_path).resolve() == tmp_path.resolve()


def test_git_root_when_git_missing(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    real_check_output = subprocess.check_output

    def fake(*args, **kwargs):
        raise FileNotFoundError()

    monkeypatch.setattr(subprocess, "check_output", fake)
    assert io.git_root(tmp_path).resolve() == tmp_path.resolve()
    # restore for other tests in the module
    monkeypatch.setattr(subprocess, "check_output", real_check_output)


def test_atomic_write_creates_parents(tmp_path: Path):
    target = tmp_path / "nested/dir/file.txt"
    io.atomic_write_text(target, "hello")
    assert target.read_text() == "hello"


def test_atomic_write_overwrites_existing(tmp_path: Path):
    target = tmp_path / "f.txt"
    target.write_text("old")
    io.atomic_write_text(target, "new")
    assert target.read_text() == "new"


def test_atomic_write_cleans_tmp_on_failure(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    import os

    def boom(*args, **kwargs):
        raise RuntimeError("replace failed")

    monkeypatch.setattr(os, "replace", boom)
    target = tmp_path / "x.txt"
    with pytest.raises(RuntimeError, match="replace failed"):
        io.atomic_write_text(target, "data")
    # no .tmp-* leftover
    assert not list(tmp_path.glob(".tmp-*"))


def test_read_lock_owner_missing(tmp_path: Path):
    assert io.read_lock_owner(tmp_path / "absent.lock") == ""


def test_try_take_lock_fresh(tmp_path: Path):
    lock = tmp_path / "l.lock"
    acquired, owner = io.try_take_lock(lock, "alice")
    assert acquired is True
    assert owner == "alice"
    assert lock.read_text() == "alice"


def test_try_take_lock_same_owner_reentrant(tmp_path: Path):
    lock = tmp_path / "l.lock"
    io.try_take_lock(lock, "alice")
    acquired, owner = io.try_take_lock(lock, "alice")
    assert (acquired, owner) == (True, "alice")


def test_try_take_lock_blocked_by_other(tmp_path: Path):
    lock = tmp_path / "l.lock"
    io.try_take_lock(lock, "alice")
    acquired, owner = io.try_take_lock(lock, "bob")
    assert acquired is False
    assert owner == "alice"


def test_release_lock_removes_file(tmp_path: Path):
    lock = tmp_path / "l.lock"
    io.try_take_lock(lock, "alice")
    io.release_lock(lock, "alice")
    assert not lock.exists()


def test_release_lock_no_op_if_other_owns(tmp_path: Path):
    lock = tmp_path / "l.lock"
    io.try_take_lock(lock, "alice")
    io.release_lock(lock, "bob")
    assert lock.exists()


def test_release_lock_when_missing_is_no_error(tmp_path: Path):
    io.release_lock(tmp_path / "absent.lock", "alice")
