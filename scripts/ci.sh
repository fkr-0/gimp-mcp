#!/usr/bin/env bash
set -euo pipefail

uv sync --extra dev --frozen
uv run python scripts/compat.py validate
uv run python scripts/docs.py generate
uv run python scripts/docs.py audit
uv run ruff format --check .
uv run ruff check .
uv run mypy
uv run pytest
uv run --extra dev mkdocs build --strict
uv build --sdist --wheel
