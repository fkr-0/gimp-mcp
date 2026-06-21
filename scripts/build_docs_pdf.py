#!/usr/bin/env python3
"""Build a compact PDF documentation artifact without external system tools.

The PDF intentionally contains the primary authored Markdown pages plus generated
workflow references as plain text. MkDocs remains the canonical HTML renderer;
this script exists so tag builds can attach a portable documentation artifact in
CI without depending on a browser or TeX installation.
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DOCS_DIR = PROJECT_ROOT / "docs"
DEFAULT_OUTPUT = PROJECT_ROOT / "dist" / "gimp-mcp-pro-docs.pdf"
DEFAULT_DOCS = (
    "index.md",
    "readme.md",
    "tutorial-workflows.md",
    "gimp-3.2.4-compat.md",
    "async-tool-architecture.md",
    "future-tools-roadmap.md",
    "tools/index.md",
)
PAGE_WIDTH = 595
PAGE_HEIGHT = 842
MARGIN_X = 54
MARGIN_TOP = 56
LINE_HEIGHT = 13
MAX_CHARS = 92


def strip_markdown(text: str) -> str:
    """Convert Markdown-ish source into plain text suitable for the PDF."""
    text = re.sub(r"```.*?```", "[code block omitted in PDF summary]", text, flags=re.S)
    text = re.sub(r"`([^`]+)`", r"\1", text)
    text = re.sub(r"\[(.*?)\]\((.*?)\)", r"\1", text)
    text = re.sub(r"^#{1,6}\s*", "", text, flags=re.M)
    text = re.sub(r"^\s*[-*]\s+", "• ", text, flags=re.M)
    text = text.replace("|", " ")
    return text


def wrap_line(line: str, width: int = MAX_CHARS) -> list[str]:
    """Wrap one line without importing textwrap for deterministic splits."""
    line = line.rstrip()
    if not line:
        return [""]
    words = line.split()
    output: list[str] = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if len(candidate) <= width:
            current = candidate
        else:
            if current:
                output.append(current)
            current = word[:width]
    if current:
        output.append(current)
    return output


def doc_lines(paths: list[Path]) -> list[str]:
    """Collect wrapped text lines from documentation pages."""
    lines = ["GIMP MCP Pro Documentation", ""]
    for path in paths:
        rel = path.relative_to(DOCS_DIR)
        lines.extend([f"=== {rel} ===", ""])
        lines.extend(
            wrapped
            for raw_line in strip_markdown(path.read_text(encoding="utf-8")).splitlines()
            for wrapped in wrap_line(raw_line)
        )
        lines.append("")
    return lines


def escape_pdf_text(text: str) -> str:
    """Escape one text fragment for a PDF literal string."""
    safe = text.encode("latin-1", "replace").decode("latin-1")
    return safe.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def paginate(lines: list[str]) -> list[list[str]]:
    """Split wrapped lines into PDF pages."""
    lines_per_page = int((PAGE_HEIGHT - MARGIN_TOP * 2) / LINE_HEIGHT)
    return [lines[index : index + lines_per_page] for index in range(0, len(lines), lines_per_page)]


def page_stream(lines: list[str]) -> str:
    """Render one PDF page content stream."""
    y = PAGE_HEIGHT - MARGIN_TOP
    stream = ["BT", "/F1 9 Tf"]
    for line in lines:
        stream.append(f"1 0 0 1 {MARGIN_X} {y} Tm ({escape_pdf_text(line)}) Tj")
        y -= LINE_HEIGHT
    stream.append("ET")
    return "\n".join(stream)


def build_pdf(lines: list[str] | Path, sources: list[Path] | None = None) -> bytes | Path:
    """Build a minimal valid PDF file or write one from source Markdown files.

    Args:
        lines: Plain text lines, or an output path when ``sources`` is provided.
        sources: Optional source Markdown files to render directly to ``lines``.

    Returns:
        PDF bytes for line input, or the written output path for source-file input.
    """
    if sources is not None:
        output = Path(lines)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(build_pdf(doc_lines(sources)))
        return output

    pages = paginate(lines)
    objects: list[str] = [
        "<< /Type /Catalog /Pages 2 0 R >>",
        "<< /Type /Pages /Kids [] /Count 0 >>",
        "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    page_object_ids: list[int] = []
    for page in pages:
        content = page_stream(page)
        content_id = len(objects) + 1
        objects.append(
            f"<< /Length {len(content.encode('latin-1'))} >>\nstream\n{content}\nendstream"
        )
        page_id = len(objects) + 1
        objects.append(
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {PAGE_WIDTH} {PAGE_HEIGHT}] "
            f"/Resources << /Font << /F1 3 0 R >> >> /Contents {content_id} 0 R >>"
        )
        page_object_ids.append(page_id)
    objects[1] = (
        f"<< /Type /Pages /Kids [{' '.join(f'{page_id} 0 R' for page_id in page_object_ids)}] "
        f"/Count {len(page_object_ids)} >>"
    )

    chunks = [b"%PDF-1.4\n"]
    offsets: list[int] = []
    for index, obj in enumerate(objects, start=1):
        offsets.append(sum(len(chunk) for chunk in chunks))
        chunks.append(f"{index} 0 obj\n{obj}\nendobj\n".encode("latin-1"))
    xref_offset = sum(len(chunk) for chunk in chunks)
    xref = [f"xref\n0 {len(objects) + 1}\n", "0000000000 65535 f \n"]
    xref.extend(f"{offset:010d} 00000 n \n" for offset in offsets)
    chunks.append("".join(xref).encode("latin-1"))
    chunks.append(
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref_offset}\n%%EOF\n".encode(
            "latin-1"
        )
    )
    return b"".join(chunks)


def build_docs_pdf(output: Path = DEFAULT_OUTPUT, docs: tuple[str, ...] = DEFAULT_DOCS) -> Path:
    """Build the documentation PDF.

    Args:
        output: Destination PDF path.
        docs: Relative docs pages to include.

    Returns:
        Path to the generated PDF.
    """
    paths = [DOCS_DIR / doc for doc in docs if (DOCS_DIR / doc).exists()]
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(build_pdf(doc_lines(paths)))
    return output


def main(argv: list[str] | None = None) -> int:
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="Build a compact docs PDF artifact.")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)
    output = build_docs_pdf(args.output)
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
