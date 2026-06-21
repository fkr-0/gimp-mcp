"""Tests for GitHub Actions CI/release workflow wiring."""

from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = PROJECT_ROOT / ".github" / "workflows" / "ci.yml"


def workflow_text() -> str:
    """Return the CI workflow source text."""
    return WORKFLOW.read_text()


def test_ci_runs_quality_gate_docs_and_package_build() -> None:
    """CI covers docs, tests, type checking, and wheel/sdist builds."""
    text = workflow_text()

    assert "uv sync --extra dev --frozen" in text
    assert "uv run pytest" in text
    assert "uv run mypy" in text
    assert "uv run mkdocs build --strict" in text
    assert "uv build --sdist --wheel" in text


def test_ci_tag_build_uploads_pdf_artifact() -> None:
    """Tag builds create and upload a docs PDF artifact outside dist/."""
    text = workflow_text()

    assert "tags:" in text
    assert "'v*'" in text
    assert "scripts/build_docs_pdf.py" in text
    assert "docs-pdf/gimp-mcp-pro-docs.pdf" in text
    assert "name: docs-pdf" in text
    assert "dist/gimp-mcp-pro-docs.pdf" not in text


def test_ci_release_job_publishes_packages_and_github_release() -> None:
    """Release job uses tag gating, PyPI publishing, and GitHub release assets."""
    text = workflow_text()

    assert "name: Tagged release" in text
    assert "if: startsWith(github.ref, 'refs/tags/v')" in text
    assert "pypa/gh-action-pypi-publish@release/v1" in text
    assert "softprops/action-gh-release@v2" in text
    assert "id-token: write" in text
    assert "contents: write" in text
