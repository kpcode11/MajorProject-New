"""Smoke tests for the backend package and HTTP framework dependency."""

import fastapi

import app


def test_backend_dependencies_import() -> None:
    """The backend package and its web framework are importable."""
    assert app.__doc__
    assert fastapi.__version__
