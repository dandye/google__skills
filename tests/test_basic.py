"""Basic test suite for google__skills."""

from google__skills.core import run_pipeline


def test_run_pipeline() -> None:
    result = run_pipeline("developer")
    assert "developer" in result
    assert "google__skills initialized successfully." in result
