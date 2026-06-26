"""Architecture and lifecycle tests for native backend code generation."""

from __future__ import annotations

import pytest

from gimp_mcp_pro.tools import native_backend
from tests.promoted_tool_cases import PROMOTED_TOOL_CASES
from tests.test_tool_generated_code_paths import ScriptedBridge, registered_tools


def generated_for(operation: str) -> str:
    payload = dict(PROMOTED_TOOL_CASES[operation]["kwargs"])
    payload["operation"] = operation
    return "\n".join(native_backend.build_json_code(f"__gimp_mcp_{operation}__", payload))


def test_native_backend_uses_operation_registry_and_code_builder() -> None:
    assert hasattr(native_backend, "NativeOperation")
    assert hasattr(native_backend, "CodeBuilder")
    assert "preview_gegl_operation" in native_backend.NATIVE_OPERATIONS
    assert (
        native_backend.NATIVE_OPERATIONS["preview_gegl_operation"].name == "preview_gegl_operation"
    )
    builder = native_backend.CodeBuilder()
    builder.add("a = 1").block("if a:", ["b = 2"]).emit_json("result")
    assert builder.lines == [
        "a = 1",
        "if a:\n    b = 2",
        "print(json.dumps(result, sort_keys=True))",
    ]


def test_build_json_code_rejects_unknown_operation_without_bridge_call() -> None:
    with pytest.raises(ValueError, match="unknown native backend operation"):
        native_backend.build_json_code("__bad__", {"operation": "typoed_operation"})


def test_native_backend_common_context_manager_snippets_are_available() -> None:
    generated = "\n".join(
        native_backend.generated_context_helpers(
            ["pdb_config", "file_obj", "drawable_filter", "temporary_duplicate_image"]
        )
    )
    assert "from contextlib import contextmanager" in generated
    assert "def managed_pdb_config(proc):" in generated
    assert "def managed_file_obj(path):" in generated
    assert "def managed_drawable_filter(drawable, operation):" in generated
    assert "def temporary_duplicate_image(image):" in generated
    assert "gc.collect()" in generated


@pytest.mark.asyncio
async def test_import_as_layer_with_metadata_uses_file_context_and_rollback() -> None:
    bridge = ScriptedBridge()
    tools = registered_tools(bridge)
    result = await tools["import_as_layer_with_metadata"](
        **PROMOTED_TOOL_CASES["import_as_layer_with_metadata"]["kwargs"]
    )
    assert result["success"] is True
    generated = "\n".join(bridge.calls[-1][1])
    assert "def managed_file_obj(path):" in generated
    assert "with managed_file_obj(result['source']) as file_obj:" in generated
    assert "inserted_layer = False" in generated
    assert "image.remove_layer(layer)" in generated
    assert "del parasite" in generated
    assert "gc.collect()" in generated


@pytest.mark.asyncio
async def test_batch_export_variants_uses_managed_pdb_config_and_file_refs() -> None:
    bridge = ScriptedBridge()
    tools = registered_tools(bridge)
    result = await tools["batch_export_variants"](
        **PROMOTED_TOOL_CASES["batch_export_variants"]["kwargs"]
    )
    assert result["success"] is True
    generated = "\n".join(bridge.calls[-1][1])
    assert "def managed_pdb_config(proc):" in generated
    assert "def managed_file_obj(path):" in generated
    assert "with managed_file_obj(file_path) as file_obj:" in generated
    assert "with managed_pdb_config(export_proc) as config:" in generated
    assert "del export_proc" in generated


@pytest.mark.asyncio
async def test_preview_gegl_operation_uses_temporary_duplicate_and_filter_contexts() -> None:
    bridge = ScriptedBridge()
    tools = registered_tools(bridge)
    result = await tools["preview_gegl_operation"](
        **PROMOTED_TOOL_CASES["preview_gegl_operation"]["kwargs"]
    )
    assert result["success"] is True
    generated = "\n".join(bridge.calls[-1][1])
    assert "def temporary_duplicate_image(image):" in generated
    assert "def managed_drawable_filter(drawable, operation):" in generated
    assert "with temporary_duplicate_image(image) as preview_image:" in generated
    assert "with managed_drawable_filter(drawable, result['operation']) as (df, cfg):" in generated
    assert "preview_image.delete()" in generated


@pytest.mark.asyncio
async def test_apply_gegl_operation_uses_native_backend_allowlist_and_filter_context() -> None:
    bridge = ScriptedBridge()
    tools = registered_tools(bridge)
    result = await tools["apply_gegl_operation"](
        **PROMOTED_TOOL_CASES["apply_gegl_operation"]["kwargs"]
    )
    assert result["success"] is True
    generated = "\n".join(bridge.calls[-1][1])
    assert "# __gimp_mcp_apply_gegl_operation__" in generated
    assert "ALLOWED_GEGL_OPERATIONS" in generated
    assert "def managed_drawable_filter(drawable, operation):" in generated
    assert "with managed_drawable_filter(drawable, operation_name) as (df, cfg):" in generated
    assert "drawable.merge_filter(df)" in generated


@pytest.mark.asyncio
async def test_execute_pdb_call_uses_native_backend_allowlist_and_managed_config() -> None:
    bridge = ScriptedBridge()
    tools = registered_tools(bridge)
    result = await tools["execute_pdb_call"](**PROMOTED_TOOL_CASES["execute_pdb_call"]["kwargs"])
    assert result["success"] is True
    generated = "\n".join(bridge.calls[-1][1])
    assert "# __gimp_mcp_execute_pdb_call__" in generated
    assert "ALLOWED_PDB_PROCEDURES" in generated
    assert "def managed_pdb_config(proc):" in generated
    assert "with managed_pdb_config(proc) as config:" in generated
    assert "proc.run(config)" in generated
