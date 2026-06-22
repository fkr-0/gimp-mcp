"""Tests for generated MkDocs/tool documentation."""

from __future__ import annotations

import ast
from pathlib import Path

import yaml

import scripts.docs as docs

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_extract_tool_docs_matches_runtime_contract() -> None:
    tool_docs = docs.extract_tool_docs()
    names = {tool.name for tool in tool_docs}

    assert len(tool_docs) == 102
    assert len(names) == 102
    assert "get_image_bitmap" in names
    assert "execute_python" in names
    assert "apply_drop_shadow" in names
    assert "gimp_dev_status" in names


def test_tool_docstring_audit_is_clean() -> None:
    failures = docs.audit_tool_docstrings()

    assert failures == []


def _minimal_tool_doc(docstring: str, parameters: tuple[str, ...] = ("value",)) -> docs.ToolDoc:
    """Build a minimal ToolDoc for audit regression tests."""
    return docs.ToolDoc(
        module="example_tools",
        module_title="Example",
        source_path=PROJECT_ROOT / "src" / "example_tools.py",
        name="example_tool",
        lineno=1,
        is_async=True,
        signature="async def example_tool(value: int) -> dict[str, Any]",
        return_annotation="dict[str, Any]",
        summary=docs.summary_from_docstring(docstring),
        docstring=docstring,
        parameters=parameters,
    )


def test_docstring_audit_requires_google_args_and_returns() -> None:
    tool = _minimal_tool_doc(
        """Example tool summary.

        Args:
            value: Example value.
        """
    )

    failures = docs.audit_tool_docstrings([tool])

    assert any("Returns section" in failure for failure in failures)


def test_docstring_audit_requires_each_parameter() -> None:
    tool = _minimal_tool_doc(
        """Example tool summary.

        Args:
            other: Different value.

        Returns:
            Operation result dictionary.
        """
    )

    failures = docs.audit_tool_docstrings([tool])

    assert any("missing parameters: value" in failure for failure in failures)


def test_docstring_audit_rejects_legacy_pseudo_sections() -> None:
    tool = _minimal_tool_doc(
        """Example tool summary.

        BEST PRACTICE (from legacy notes): Before drawing a rectangle.

        Args:
            value: Example value.

        Returns:
            Operation result dictionary.
        """
    )

    failures = docs.audit_tool_docstrings([tool])

    assert any(
        "pseudo-section 'BEST PRACTICE (from legacy notes)'" in failure for failure in failures
    )


def test_generated_tool_reference_contains_signatures_and_docstrings(tmp_path: Path) -> None:
    written = docs.write_generated_docs(tmp_path)
    docs.render_docstring_audit(tmp_path)

    tool_index = tmp_path / "tools" / "index.md"
    inspect_page = tmp_path / "tools" / "inspect_tools.md"
    api_index = tmp_path / "api" / "index.md"
    protocol_page = tmp_path / "api" / "protocol.md"
    tool_types_page = tmp_path / "api" / "tools-types.md"

    assert tool_index in written
    assert inspect_page in written
    assert api_index in written
    assert protocol_page in written
    assert tool_types_page in written
    assert "Total tools: **102**" in tool_index.read_text()
    inspect_text = inspect_page.read_text()
    assert "async def get_image_bitmap" in inspect_text
    assert "Get the current image as a viewable bitmap" in inspect_text
    assert "-> ToolResult" in inspect_text


def test_docs_cli_generate_reports_written_files(tmp_path: Path, capsys) -> None:  # type: ignore[no-untyped-def]
    status = docs.main(["generate", "--output", str(tmp_path)])

    captured = capsys.readouterr()
    assert status == 0
    assert "tools/index.md" in captured.out
    assert (tmp_path / "tool-docstring-audit.md").exists()


def test_mkdocs_material_configuration_references_generated_pages() -> None:
    config = yaml.safe_load((PROJECT_ROOT / "mkdocs.yml").read_text())

    assert config["theme"]["name"] == "material"
    plugin_names = [
        next(iter(plugin)) if isinstance(plugin, dict) else plugin for plugin in config["plugins"]
    ]
    assert "mkdocstrings" in plugin_names
    assert "search" in plugin_names
    nav_text = str(config["nav"])
    assert "tools/index.md" in nav_text
    assert "tool-docstring-audit.md" in nav_text
    assert "api/config.md" in nav_text
    assert "api/protocol.md" in nav_text
    assert "api/tools-types.md" in nav_text
    assert "agent-workflows.md" in nav_text
    assert "tutorial-workflows.md" in nav_text
    assert "tools/gimp_dev_tools.md" in nav_text


def _public_method_docstring(path: str, class_name: str, method_name: str) -> str:
    """Return the cleaned docstring for a public class method."""
    tree = ast.parse((PROJECT_ROOT / path).read_text())
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            for child in node.body:
                if (
                    isinstance(child, ast.FunctionDef | ast.AsyncFunctionDef)
                    and child.name == method_name
                ):
                    return ast.get_docstring(child) or ""
    raise AssertionError(f"{class_name}.{method_name} not found in {path}")


def test_bridge_api_docstrings_describe_public_contracts() -> None:
    """Ensure prominent mkdocstrings bridge methods stay useful."""
    sync_connected = _public_method_docstring(
        "src/gimp_mcp_pro/bridge.py", "GimpBridge", "connected"
    )
    async_send = _public_method_docstring(
        "src/gimp_mcp_pro/async_bridge.py", "AsyncGimpBridge", "send_command"
    )

    assert "Returns:" in sync_connected
    assert "Args:" in async_send
    assert "Returns:" in async_send
    assert "Raises:" in async_send
