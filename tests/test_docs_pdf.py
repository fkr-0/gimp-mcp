"""Tests for release documentation PDF generation."""

from __future__ import annotations

from pathlib import Path

import scripts.build_docs_pdf as docs_pdf


def test_docs_pdf_builder_writes_valid_pdf_header(tmp_path: Path) -> None:
    """The release PDF builder should work without external PDF toolchains."""
    output = tmp_path / "manual.pdf"

    docs_pdf.build_docs_pdf(output, docs=())

    data = output.read_bytes()
    assert data.startswith(b"%PDF-1.4")
    assert b"%%EOF" in data[-128:]
    assert len(data) > 500
