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
LOGICAL_TOOL_MODULES = {
    "inspect_context_backend": "inspect_tools",
    "inspect_geometry_backend": "inspect_tools",
    "inspect_snapshot_backend": "inspect_tools",
    "inspect_bitmap_backend": "inspect_tools",
}

MODULE_TITLES: dict[str, str] = {
    "image_tools": "Image Management",
    "layer_tools": "Layer Operations",
    "selection_tools": "Selections",
    "path_tools": "Vector Paths",
    "target_tools": "Target Resolution",
    "drawing_tools": "Drawing and Text",
    "inspect_tools": "Inspection",
    "gimp_dev_tools": "gimp.dev Integration",
    "history_tools": "History",
    "pdb_tools": "PDB and Escape Hatch",
    "transform_tools": "Transforms",
    "filter_tools": "Filters and Effects",
    "color_tools": "Color Adjustments",
    "flow_tools": "Repeatable Flows and Macros",
}

FORBIDDEN_DOCSTRING_MARKERS = ("TODO", "TBD", "FIXME", "lorem ipsum")
FORBIDDEN_PSEUDO_SECTIONS = (
    "WHEN TO USE",
    "BEST PRACTICE",
    "PRIMARY USE",
    "IMPORTANT",
    "WARNING",
    "COMBINES WITH",
    "NOTE",
)
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
        module = LOGICAL_TOOL_MODULES.get(path.stem, path.stem)
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

!!! success "GIMP 3.2.4 compatibility verified"
    `compat.results.yml` records a 24/24 isolated clean-profile Xvfb run with the 183-tool registry and `claim_allowed: true`. Re-run the contract whenever the plug-in protocol or GIMP-facing generated code changes.

## Documentation map

- [Tool Reference](tools/index.md): generated from the actual MCP tool handler docstrings.
- [Docstring Style](docstring-style.md): Google-style policy used by MkDocs and the MCP tool audit.
- [Compatibility Runbook](gimp-3.2.4-compat.md): clean-profile GIMP 3.2.4 verification workflow.
- [Native Backend Helpers](native-backend.md): architecture and usage of shared generated-code helpers.
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


def _docstring_section_items(docstring: str, section: str) -> list[tuple[str, str]]:
    """Return documented items from a Google-style docstring section."""
    items: list[tuple[str, str]] = []
    current_name: str | None = None
    current_description: list[str] = []
    for line in _docstring_section_lines(docstring, section):
        stripped = line.strip()
        if not stripped:
            continue
        if ":" in stripped and not stripped.startswith("-"):
            prefix, description = stripped.split(":", 1)
            candidate = prefix.replace("`", "").split(" ", 1)[0].strip()
            if candidate.isidentifier() or "," in prefix:
                if current_name is not None:
                    items.append((current_name, " ".join(current_description).strip()))
                current_name = prefix.strip().replace("`", "")
                current_description = [description.strip()]
                continue
        if current_name is not None:
            current_description.append(stripped)
    if current_name is not None:
        items.append((current_name, " ".join(current_description).strip()))
    return items


def _docstring_section_text(docstring: str, section: str) -> str:
    """Return compact text from a Google-style docstring section."""
    return " ".join(
        line.strip() for line in _docstring_section_lines(docstring, section) if line.strip()
    )


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
        arg_items = _docstring_section_items(tool.docstring, "Args")
        documented_args = {name.split(",", 1)[0].split(" ", 1)[0] for name, _ in arg_items}
        if tool.parameters:
            lines.append("## Parameters")
            lines.append("")
            lines.append("| Parameter | Description |")
            lines.append("|---|---|")
            item_map = {
                name.split(",", 1)[0].split(" ", 1)[0]: (name, desc) for name, desc in arg_items
            }
            for parameter in tool.parameters:
                display, description = item_map.get(parameter, (parameter, "_Undocumented._"))
                lines.append(f"| `{display}` | {description} |")
            for name, description in arg_items:
                key = name.split(",", 1)[0].split(" ", 1)[0]
                if key not in documented_args or key in tool.parameters:
                    continue
                lines.append(f"| `{name}` | {description} |")
            lines.append("")
        returns_text = _docstring_section_text(tool.docstring, "Returns")
        if returns_text:
            lines.append("## Returns")
            lines.append("")
            lines.append(returns_text)
            lines.append("")
        lines.append("## Contract")
        lines.append("")
        lines.extend(
            [
                "- Return shape: `ToolResult` / `OperationResult` with structured status, message, data, and error fields.",
                "- Compatibility contract: `compat.yml` tracks this public MCP registry surface.",
                "- Generated-code smoke: `tests/test_tool_generated_code_paths.py` exercises fast handler success paths.",
                "- Invocation matrix: `tests/test_tool_invocation_matrix.py` keeps public arguments covered.",
                "",
            ]
        )
        lines.append("## Docstring")
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
- [Protocol Types](protocol.md)
- [Tool Typing Protocols](tools-types.md)
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


def _rewrite_readme_links_for_docs_site(text: str) -> str:
    """Rewrite repository-root docs links for the generated MkDocs readme page."""
    return text.replace("](docs/", "](")


def copy_readme(output_dir: Path) -> None:
    """Copy README into docs for site consumers."""
    if README_PATH.exists():
        readme = _rewrite_readme_links_for_docs_site(README_PATH.read_text(encoding="utf-8"))
        (output_dir / "readme.md").write_text(readme, encoding="utf-8")


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
        api_dir / "protocol.md": render_mkdocstrings_page(
            "Protocol Types", "gimp_mcp_pro.protocol"
        ),
        api_dir / "tools-types.md": render_mkdocstrings_page(
            "Tool Typing Protocols", "gimp_mcp_pro.tools.types"
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
        for line in tool.docstring.splitlines():
            stripped = line.strip()
            if not stripped.endswith(":") and ":" not in stripped:
                continue
            prefix = stripped.split(":", 1)[0]
            legacy_prefix = next(
                (
                    section
                    for section in FORBIDDEN_PSEUDO_SECTIONS
                    if prefix == section or prefix.startswith(f"{section} ")
                ),
                None,
            )
            if legacy_prefix is not None:
                failures.append(
                    f"{ref}: pseudo-section {prefix!r} should be a Google-style "
                    "Notes or Warnings section"
                )
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
