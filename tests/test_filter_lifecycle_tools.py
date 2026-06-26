"""Lifecycle and leak-safety tests for filter category generated code."""

from __future__ import annotations

import pytest

from gimp_mcp_pro.tools.filter_tools import register_filter_tools
from tests.test_tool_generated_code_paths import CaptureMCP, ScriptedBridge


@pytest.mark.asyncio
async def test_committed_filter_releases_drawable_filter_references() -> None:
    mcp = CaptureMCP()
    bridge = ScriptedBridge()
    register_filter_tools(mcp, bridge)

    result = await mcp.tools["apply_gaussian_blur"](radius_x=3.0, radius_y=4.0, layer_index=0)

    assert result["success"] is True
    generated = "\n".join(bridge.calls[-1][1])
    assert "# __gimp_mcp_filter_lifecycle__" in generated
    assert "df = None" in generated
    assert "cfg = None" in generated
    assert "try:" in generated
    assert "finally:" in generated
    assert "drawable.append_filter(df)" in generated
    assert "drawable.merge_filter(df)" in generated
    assert "del cfg" in generated
    assert "del df" in generated
    assert "gc.collect()" in generated


@pytest.mark.asyncio
async def test_preview_filter_removes_temporary_layer_on_filter_failure_and_releases_refs() -> None:
    mcp = CaptureMCP()
    bridge = ScriptedBridge()
    register_filter_tools(mcp, bridge)

    result = await mcp.tools["preview_filter"](
        filter="gaussian_blur",
        parameters={"radius_x": 3.0, "radius_y": 4.0},
        preview_mode="temporary_layer",
        layer_index=0,
    )

    assert result["success"] is True
    generated = "\n".join(bridge.calls[-1][1])
    assert "# __gimp_mcp_preview_filter_lifecycle__" in generated
    assert "preview_layer = None" in generated
    assert "df = None" in generated
    assert "cfg = None" in generated
    assert "except Exception:" in generated
    assert "image.remove_layer(preview_layer)" in generated
    assert "raise" in generated
    assert "del cfg" in generated
    assert "del df" in generated
    assert "gc.collect()" in generated


@pytest.mark.asyncio
async def test_committed_filter_lifecycle_block_is_single_exec_unit() -> None:
    """GIMP bridge executes each code-list item separately, so try/finally must be one item."""
    mcp = CaptureMCP()
    bridge = ScriptedBridge()
    register_filter_tools(mcp, bridge)

    result = await mcp.tools["apply_gaussian_blur"](radius_x=3.0, radius_y=4.0, layer_index=0)

    assert result["success"] is True
    generated_items = bridge.calls[-1][1]
    assert "try:" not in generated_items
    lifecycle_blocks = [
        item for item in generated_items if "# __gimp_mcp_filter_lifecycle__" in item
    ]
    assert len(lifecycle_blocks) == 1
    assert "try:\n    df = Gimp.DrawableFilter.new" in lifecycle_blocks[0]
    assert "finally:\n    try:" in lifecycle_blocks[0]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("tool_name", "kwargs", "operation", "expected_properties"),
    [
        (
            "apply_pixelize",
            {"block_width": 8, "block_height": 6},
            "gegl:pixelize",
            {"size-x": 8, "size-y": 6},
        ),
        ("apply_edge_detect", {"method": "sobel", "amount": 1.5}, "gegl:edge", {"amount": 1.5}),
        (
            "apply_emboss",
            {"azimuth": 315.0, "elevation": 45.0, "depth": 3},
            "gegl:emboss",
            {"azimuth": 315.0, "elevation": 45.0, "depth": 3},
        ),
        (
            "apply_noise",
            {"amount": 0.25},
            "gegl:noise-hsv",
            {"holdness": 2, "value-distance": 0.25},
        ),
        ("apply_median", {"radius": 4}, "gegl:median-blur", {"radius": 4}),
    ],
)
async def test_remaining_filter_matrix_only_wrappers_have_direct_generated_code_coverage(
    tool_name: str,
    kwargs: dict[str, object],
    operation: str,
    expected_properties: dict[str, object],
) -> None:
    mcp = CaptureMCP()
    bridge = ScriptedBridge()
    register_filter_tools(mcp, bridge)

    result = await mcp.tools[tool_name](**kwargs)

    assert result["success"] is True
    generated = "\n".join(bridge.calls[-1][1])
    assert "# __gimp_mcp_filter_lifecycle__" in generated
    assert f"df = Gimp.DrawableFilter.new(drawable, '{operation}', '')" in generated
    for key, value in expected_properties.items():
        assert f"cfg.set_property({key!r}, {value!r})" in generated
    assert "drawable.append_filter(df)" in generated
    assert "drawable.merge_filter(df)" in generated
    assert "del cfg" in generated
    assert "del df" in generated
    assert "gc.collect()" in generated
