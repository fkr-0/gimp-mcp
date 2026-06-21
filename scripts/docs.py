#!/usr/bin/env python3
"""Generate MkDocs Material pages from project and MCP tool docstrings.

Mkdocstrings is useful for top-level Python objects, but the public MCP tools in
this project are nested functions inside register_* helpers.  This generator
therefore extracts those nested handlers with ``ast`` and renders deterministic
Markdown pages that MkDocs Material can publish.
"""

from __future__ import annotations

import argparse
import ast
import inspect
import shutil
import sys
from collections import defaultdict
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
TOOLS_DIR = PROJECT_ROOT / "src" / "gimp_mcp_pro" / "tools"
DOCS_DIR = PROJECT_ROOT / "docs"
README_PATH = PROJECT_ROOT / "README.md"

MODULE_TITLES: dict[str, str] = {
    "image_tools": "Image Management",
    "layer_tools": "Layer Operations",
    "selection_tools": "Selections",
    "drawing_tools": "Drawing and Text",
    "inspect_tools": "Inspection",
    "history_tools": "History",
    "pdb_tools": "PDB and Escape Hatch",
    "transform_tools": "Transforms",
    "filter_tools": "Filters and Effects",
    "color_tools": "Color Adjustments",
}

FORBIDDEN_DOCSTRING_MARKERS = ("TODO", "TBD", "FIXME", "lorem ipsum")
GOOGLE_SECTION_NAMES = {"Args", "Arguments", "Returns", "Raises", "Examples", "Notes", "Warnings"}


@dataclass(frozen=True)
class ToolDoc:
    """Doc model for one MCP tool handler."""

    module: str
    module_title: str
    source_path: Path
    name: str
    lineno: int
    is_async: bool
    signature: str
    return_annotation: str
    summary: str
    docstring: str
    parameters: tuple[str, ...]

    @property
    def source_ref(self) -> str:
        """Return a stable source reference relative to the project root."""
        return f"{self.source_path.relative_to(PROJECT_ROOT)}:{self.lineno}"


def is_mcp_tool(node: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    """Return whether an AST function node is decorated with @mcp.tool(...)."""
    for decorator in node.decorator_list:
        if isinstance(decorator, ast.Call) and getattr(decorator.func, "attr", None) == "tool":
            return True
    return False


def annotation_text(node: ast.AST | None, *, fallback: str = "Any") -> str:
    """Render an annotation/default AST node as source text."""
    if node is None:
        return fallback
    return ast.unparse(node)


def argument_text(argument: ast.arg, default: ast.expr | None = None) -> str:
    """Render one argument with optional annotation and default."""
    text = argument.arg
    if argument.annotation is not None:
        text += f": {ast.unparse(argument.annotation)}"
    if default is not None:
        text += f" = {ast.unparse(default)}"
    return text


def render_signature(node: ast.FunctionDef | ast.AsyncFunctionDef) -> str:
    """Render a compact function signature from AST."""
    positional = list(node.args.posonlyargs) + list(node.args.args)
    defaults: list[ast.expr | None] = [None] * (len(positional) - len(node.args.defaults)) + list(
        node.args.defaults
    )

    parts = [
        argument_text(argument, default)
        for argument, default in zip(positional, defaults, strict=True)
    ]
    if node.args.vararg is not None:
        parts.append("*" + argument_text(node.args.vararg))
    elif node.args.kwonlyargs:
        parts.append("*")

    for argument, default in zip(node.args.kwonlyargs, node.args.kw_defaults, strict=True):
        parts.append(argument_text(argument, default))

    if node.args.kwarg is not None:
        parts.append("**" + argument_text(node.args.kwarg))

    prefix = "async def" if isinstance(node, ast.AsyncFunctionDef) else "def"
    returns = annotation_text(node.returns)
    return f"{prefix} {node.name}({', '.join(parts)}) -> {returns}"


def public_parameters(node: ast.FunctionDef | ast.AsyncFunctionDef) -> tuple[str, ...]:
    """Return public tool parameter names."""
    names = [argument.arg for argument in node.args.posonlyargs + node.args.args]
    names.extend(argument.arg for argument in node.args.kwonlyargs)
    return tuple(name for name in names if name not in {"self", "cls"})


def summary_from_docstring(docstring: str) -> str:
    """Return the first non-empty docstring line."""
    for line in docstring.splitlines():
        stripped = line.strip()
        if stripped:
            return stripped
    return ""


def extract_tool_docs(tools_dir: Path = TOOLS_DIR) -> list[ToolDoc]:
    """Extract all MCP tool doc models from source files."""
    docs: list[ToolDoc] = []
    for path in sorted(tools_dir.glob("*.py")):
        if path.name in {"__init__.py", "types.py"}:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        module = path.stem
        for node in ast.walk(tree):
            if not isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
                continue
            if not is_mcp_tool(node):
                continue
            docstring = inspect.cleandoc(ast.get_docstring(node) or "")
            docs.append(
                ToolDoc(
                    module=module,
                    module_title=MODULE_TITLES.get(module, module.replace("_", " ").title()),
                    source_path=path,
                    name=node.name,
                    lineno=node.lineno,
                    is_async=isinstance(node, ast.AsyncFunctionDef),
                    signature=render_signature(node),
                    return_annotation=annotation_text(node.returns),
                    summary=summary_from_docstring(docstring),
                    docstring=docstring,
                    parameters=public_parameters(node),
                )
            )
    return sorted(docs, key=lambda item: (item.module, item.lineno, item.name))


def group_by_module(tools: Iterable[ToolDoc]) -> dict[str, list[ToolDoc]]:
    """Group tools by source module while preserving extraction order."""
    grouped: dict[str, list[ToolDoc]] = defaultdict(list)
    for tool in tools:
        grouped[tool.module].append(tool)
    return dict(grouped)


def markdown_anchor(name: str) -> str:
    """Return a simple MkDocs-compatible anchor suffix."""
    return name.lower().replace("_", "-")


def render_index(tools: Sequence[ToolDoc]) -> str:
    """Render docs/index.md."""
    return f"""# GIMP MCP Pro

GIMP MCP Pro exposes typed Model Context Protocol tools for operating GIMP from an AI assistant while keeping GIMP-specific execution inside a plug-in process.

!!! warning "GIMP 3.2.4 compatibility status"
    The branch-level compatibility claim is still gated by `compat.yml` and live evidence in `compat.results.yml`. Static documentation and tests do not by themselves prove GIMP 3.2.4 compatibility.

## Documentation map

- [Tool Reference](tools/index.md): generated from the actual MCP tool handler docstrings.
- [Compatibility Runbook](gimp-3.2.4-compat.md): clean-profile GIMP 3.2.4 verification workflow.
- [Python API](api/index.md): mkdocstrings-rendered top-level package API.

## Current generated tool count

```yaml
tools: {len(tools)}
source: src/gimp_mcp_pro/tools
```
"""


def render_tools_index(grouped: Mapping[str, Sequence[ToolDoc]]) -> str:
    """Render docs/tools/index.md."""
    total = sum(len(items) for items in grouped.values())
    lines = [
        "# MCP Tool Reference",
        "",
        "This section is generated from the nested `@mcp.tool()` handler docstrings in `src/gimp_mcp_pro/tools`.",
        "",
        '!!! info "Generated documentation"',
        "    Regenerate with `uv run python scripts/docs.py generate` before building or publishing docs.",
        "",
        f"Total tools: **{total}**",
        "",
        "| Category | Tools | Page |",
        "|---|---:|---|",
    ]
    for module, tools in grouped.items():
        title = tools[0].module_title if tools else MODULE_TITLES.get(module, module)
        lines.append(f"| {title} | {len(tools)} | [{module}]({module}.md) |")
    lines.extend(["", "## Tool inventory", ""])
    for module, tools in grouped.items():
        title = tools[0].module_title if tools else module
        lines.append(f"### {title}")
        lines.append("")
        for tool in tools:
            lines.append(
                f"- [`{tool.name}`]({module}.md#{markdown_anchor(tool.name)}) — {tool.summary}"
            )
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def render_tool_module(module: str, tools: Sequence[ToolDoc]) -> str:
    """Render one docs/tools/<module>.md page."""
    title = tools[0].module_title if tools else MODULE_TITLES.get(module, module)
    lines = [
        f"# {title}",
        "",
        f"Source module: `src/gimp_mcp_pro/tools/{module}.py`",
        "",
        "| Tool | Summary | Parameters |",
        "|---|---|---:|",
    ]
    for tool in tools:
        lines.append(
            f"| [`{tool.name}`](#{markdown_anchor(tool.name)}) | {tool.summary} | {len(tool.parameters)} |"
        )
    lines.append("")
    for tool in tools:
        lines.extend(
            [
                f"## `{tool.name}` {{#{markdown_anchor(tool.name)}}}",
                "",
                f"Source: `{tool.source_ref}`",
                "",
                "```python",
                tool.signature,
                "```",
                "",
            ]
        )
        if tool.parameters:
            lines.append("**Parameters**")
            lines.append("")
            for parameter in tool.parameters:
                lines.append(f"- `{parameter}`")
            lines.append("")
        lines.append("**Docstring**")
        lines.append("")
        lines.append(tool.docstring or "_No docstring available._")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def render_api_index() -> str:
    """Render docs/api/index.md."""
    return """# Python API

The pages in this section are rendered by mkdocstrings from top-level Python modules.
Nested MCP tool handlers are documented separately in the generated [Tool Reference](../tools/index.md).

- [Configuration](config.md)
- [Bridge](bridge.md)
- [Async Bridge](async-bridge.md)
- [Server](server.md)
- [Common Models](models-common.md)
"""


def render_mkdocstrings_page(title: str, module: str) -> str:
    """Render one mkdocstrings page."""
    return f"""# {title}

::: {module}
    options:
      show_source: true
      show_root_heading: true
      show_symbol_type_heading: true
      members_order: source
"""


def copy_readme(output_dir: Path) -> None:
    """Copy README into docs for site consumers."""
    if README_PATH.exists():
        (output_dir / "readme.md").write_text(
            README_PATH.read_text(encoding="utf-8"), encoding="utf-8"
        )


def write_generated_docs(output_dir: Path = DOCS_DIR) -> list[Path]:
    """Generate documentation files and return written paths."""
    tools = extract_tool_docs()
    grouped = group_by_module(tools)
    written: list[Path] = []

    output_dir.mkdir(parents=True, exist_ok=True)
    tools_dir = output_dir / "tools"
    api_dir = output_dir / "api"
    tools_dir.mkdir(parents=True, exist_ok=True)
    api_dir.mkdir(parents=True, exist_ok=True)

    pages: dict[Path, str] = {
        output_dir / "index.md": render_index(tools),
        tools_dir / "index.md": render_tools_index(grouped),
        api_dir / "index.md": render_api_index(),
        api_dir / "config.md": render_mkdocstrings_page("Configuration", "gimp_mcp_pro.config"),
        api_dir / "bridge.md": render_mkdocstrings_page("Bridge", "gimp_mcp_pro.bridge"),
        api_dir / "async-bridge.md": render_mkdocstrings_page(
            "Async Bridge", "gimp_mcp_pro.async_bridge"
        ),
        api_dir / "server.md": render_mkdocstrings_page("Server", "gimp_mcp_pro.server"),
        api_dir / "models-common.md": render_mkdocstrings_page(
            "Common Models", "gimp_mcp_pro.models.common"
        ),
    }
    for module, module_tools in grouped.items():
        pages[tools_dir / f"{module}.md"] = render_tool_module(module, module_tools)

    for path, content in sorted(pages.items()):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        written.append(path)

    copy_readme(output_dir)
    written.append(output_dir / "readme.md")
    return written


def _docstring_section_lines(docstring: str, section: str) -> list[str]:
    """Return body lines for a Google-style docstring section.

    Args:
        docstring: Cleaned docstring text.
        section: Section name without the trailing colon.

    Returns:
        Lines belonging to the requested section, excluding the heading.
    """
    lines = docstring.splitlines()
    body: list[str] = []
    in_section = False
    heading = f"{section}:"
    for line in lines:
        stripped = line.strip()
        if stripped == heading:
            in_section = True
            continue
        if in_section and stripped.endswith(":") and stripped[:-1] in GOOGLE_SECTION_NAMES:
            break
        if in_section:
            body.append(line)
    return body


def _documented_args(docstring: str) -> set[str]:
    """Extract parameter names documented in a Google-style Args section.

    Args:
        docstring: Cleaned docstring text.

    Returns:
        Parameter names found before colons in the Args section. Grouped
        declarations such as ``x, y: Coordinates`` count for both names.
    """
    names: set[str] = set()
    for line in _docstring_section_lines(docstring, "Args"):
        stripped = line.strip()
        if not stripped or stripped.startswith("-") or ":" not in stripped:
            continue
        prefix = stripped.split(":", 1)[0]
        # Accept Google style with optional type hints: ``name (int):``.
        prefix = prefix.replace("`", "")
        for part in prefix.split(","):
            name = part.strip().split(" ", 1)[0]
            if name.isidentifier():
                names.add(name)
    return names


def _has_section(docstring: str, section: str) -> bool:
    """Return whether a cleaned docstring contains a Google-style section.

    Args:
        docstring: Cleaned docstring text.
        section: Section name without the trailing colon.

    Returns:
        True when the section heading is present.
    """
    return any(line.strip() == f"{section}:" for line in docstring.splitlines())


def audit_tool_docstrings(tools: Sequence[ToolDoc] | None = None) -> list[str]:
    """Return Google-style documentation quality issues for MCP tool handlers.

    Args:
        tools: Optional pre-extracted tool documentation models. When omitted,
            the current source tree is scanned.

    Returns:
        Human-readable audit failures. An empty list means all tool docstrings
        satisfy the MkDocs-oriented source policy.
    """
    if tools is None:
        tools = extract_tool_docs()
    failures: list[str] = []
    seen: set[str] = set()
    for tool in tools:
        ref = f"{tool.source_ref} {tool.name}"
        if tool.name in seen:
            failures.append(f"duplicate tool name: {tool.name}")
        seen.add(tool.name)
        if not tool.docstring:
            failures.append(f"{ref}: missing docstring")
            continue
        if len(tool.summary) < 12:
            failures.append(f"{ref}: summary is too short")
        if tool.summary and not tool.summary[0].isupper():
            failures.append(f"{ref}: summary should start with an uppercase letter")
        lowered = tool.docstring.lower()
        for marker in FORBIDDEN_DOCSTRING_MARKERS:
            if marker.lower() in lowered:
                failures.append(f"{ref}: contains placeholder marker {marker!r}")
        if tool.return_annotation == "Any":
            failures.append(f"{ref}: missing explicit return annotation")
        if not _has_section(tool.docstring, "Returns"):
            failures.append(f"{ref}: missing Google-style Returns section")
        if tool.parameters:
            if not _has_section(tool.docstring, "Args"):
                failures.append(f"{ref}: missing Google-style Args section")
            else:
                documented = _documented_args(tool.docstring)
                missing = [
                    parameter for parameter in tool.parameters if parameter not in documented
                ]
                if missing:
                    failures.append(
                        f"{ref}: Args section is missing parameters: {', '.join(missing)}"
                    )
    return failures


def render_docstring_audit(output_dir: Path = DOCS_DIR) -> Path:
    """Write a Markdown audit report for tool docstrings."""
    tools = extract_tool_docs()
    failures = audit_tool_docstrings(tools)
    grouped = group_by_module(tools)
    lines = [
        "# Tool Docstring Audit",
        "",
        "This audit is generated from the same AST extraction path as the tool reference.",
        "",
        f"Total tools: **{len(tools)}**",
        f"Audit failures: **{len(failures)}**",
        "",
    ]
    if failures:
        lines.append("## Failures")
        lines.append("")
        for failure in failures:
            lines.append(f"- {failure}")
        lines.append("")
    lines.append("## Coverage by module")
    lines.append("")
    lines.append("| Module | Tools |")
    lines.append("|---|---:|")
    for module, module_tools in grouped.items():
        lines.append(f"| `{module}` | {len(module_tools)} |")
    lines.append("")

    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / "tool-docstring-audit.md"
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def remove_site_dir(path: Path) -> None:
    """Remove generated site output if present."""
    if path.exists():
        shutil.rmtree(path)


def display_path(path: Path) -> Path:
    """Return a project-relative path when possible, otherwise the absolute path."""
    try:
        return path.relative_to(PROJECT_ROOT)
    except ValueError:
        return path


def cmd_generate(args: argparse.Namespace) -> int:
    """Generate docs and docstring audit report."""
    output_dir = Path(args.output)
    if not output_dir.is_absolute():
        output_dir = PROJECT_ROOT / output_dir
    written = write_generated_docs(output_dir)
    audit_path = render_docstring_audit(output_dir)
    written.append(audit_path)
    for path in written:
        print(display_path(path))
    return 0


def cmd_audit(_: argparse.Namespace) -> int:
    """Audit tool docstrings."""
    failures = audit_tool_docstrings()
    if failures:
        print("tool docstring audit failed:", file=sys.stderr)
        for failure in failures:
            print(f"- {failure}", file=sys.stderr)
        return 1
    print("tool docstring audit ok")
    return 0


def build_parser() -> argparse.ArgumentParser:
    """Build the documentation CLI parser."""
    parser = argparse.ArgumentParser(description="Generate MkDocs documentation from source docs.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    generate = subparsers.add_parser("generate", help="Generate docs pages from tool docstrings.")
    generate.add_argument("--output", default="docs", help="Output docs directory.")
    generate.set_defaults(func=cmd_generate)

    audit = subparsers.add_parser("audit", help="Check MCP tool docstring quality.")
    audit.set_defaults(func=cmd_audit)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Script entry point."""
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
