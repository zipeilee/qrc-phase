"""Smoke checks for qrc-phase Python backend imports."""

import importlib

import pytest


def test_import_py_backend() -> None:
    import py_backend  # noqa: F401


def test_import_mindquantum_when_available() -> None:
    pytest.importorskip("mindquantum")
    mindquantum = importlib.import_module("mindquantum")
    assert mindquantum is not None

