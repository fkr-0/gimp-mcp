"""Lifecycle and atomicity tests for color category generated code."""

from __future__ import annotations

import pytest

from gimp_mcp_pro.tools.color_tools import register_color_tools
from tests.test_tool_generated_code_paths import CaptureMCP, ScriptedBridge


@pytest.mark.asyncio
async def test_set_paint_context_validates_before_mutation_and_rolls_back_on_failure() -> None:
    mcp = CaptureMCP()
    bridge = ScriptedBridge()
    register_color_tools(mcp, bridge)

    result = await mcp.tools["set_paint_context"](
        brush="2. Hardness 050",
        size=12.5,
        opacity=80.0,
        pattern="Pine",
        gradient="FG to BG (RGB)",
        foreground="#112233",
        background="#ffffff",
    )

    assert result["success"] is True
    generated = "\n".join(bridge.calls[-1][1])
    assert "# __gimp_mcp_paint_context_lifecycle__" in generated
    assert "previous_foreground_color = Gimp.context_get_foreground()" in generated
    assert "previous_background_color = Gimp.context_get_background()" in generated
    assert "foreground_color = None" in generated
    assert "background_color = None" in generated
    assert "brush_names = _resource_names(Gimp.brushes_get_list(''))" in generated
    assert "pattern_names = _resource_names(Gimp.patterns_get_list(''))" in generated
    assert "gradient_names = _resource_names(Gimp.gradients_get_list(''))" in generated
    assert generated.index("brush_names = _resource_names") < generated.index(
        "Gimp.context_set_brush('2. Hardness 050')"
    )
    assert generated.index("pattern_names = _resource_names") < generated.index(
        "Gimp.context_set_pattern('Pine')"
    )
    assert generated.index("gradient_names = _resource_names") < generated.index(
        "Gimp.context_set_gradient('FG to BG (RGB)')"
    )
    assert "except Exception:" in generated
    assert "Gimp.context_set_brush(previous_context['brush'])" in generated
    assert "Gimp.context_set_pattern(previous_context['pattern'])" in generated
    assert "Gimp.context_set_gradient(previous_context['gradient'])" in generated
    assert "Gimp.context_set_opacity(previous_context['opacity'])" in generated
    assert "Gimp.context_set_brush_size(previous_context['brush_size'])" in generated
    assert "Gimp.context_set_foreground(previous_foreground_color)" in generated
    assert "Gimp.context_set_background(previous_background_color)" in generated
    assert "finally:" in generated
    assert "del foreground_color" in generated
    assert "del background_color" in generated
    assert "gc.collect()" in generated
    # Keep compatibility with existing generated-code contract tests.
    assert "Gimp.context_set_foreground(Gegl.Color.new('#112233'))" in generated
    assert "Gimp.context_set_background(Gegl.Color.new('#ffffff'))" in generated


MUTATING_ADJUSTMENT_CASES = [
    (
        "adjust_brightness_contrast",
        {"brightness": 12, "contrast": -8},
        "Gimp.Drawable.brightness_contrast",
    ),
    (
        "adjust_hue_saturation",
        {"hue": 10, "lightness": 5, "saturation": -6},
        "Gimp.Drawable.hue_saturation",
    ),
    (
        "adjust_color_balance",
        {"range": "midtones", "cyan_red": 5.0, "magenta_green": -2.0, "yellow_blue": 1.0},
        "Gimp.Drawable.color_balance",
    ),
    (
        "adjust_levels",
        {"channel": "value", "input_low": 10, "input_high": 245},
        "Gimp.Drawable.levels",
    ),
    (
        "adjust_curves",
        {"channel": "value", "control_points": [0, 0, 128, 150, 255, 255]},
        "Gimp.Drawable.curves_spline",
    ),
    ("desaturate", {"method": "luminosity"}, "Gimp.Drawable.desaturate"),
    ("invert_colors", {}, "Gimp.Drawable.invert"),
    ("apply_threshold", {"low": 10, "high": 220}, "Gimp.Drawable.threshold"),
    ("posterize", {"levels": 4}, "Gimp.Drawable.posterize"),
    ("auto_white_balance", {}, "Gimp.Drawable.levels_stretch"),
]


@pytest.mark.asyncio
@pytest.mark.parametrize(("tool_name", "kwargs", "mutation_call"), MUTATING_ADJUSTMENT_CASES)
async def test_mutating_color_adjustments_use_shared_undo_lifecycle(
    tool_name: str, kwargs: dict[str, object], mutation_call: str
) -> None:
    mcp = CaptureMCP()
    bridge = ScriptedBridge()
    register_color_tools(mcp, bridge)

    result = await mcp.tools[tool_name](**kwargs)

    assert result["success"] is True
    generated = "\n".join(bridge.calls[-1][1])
    assert "# __gimp_mcp_color_adjustment_lifecycle__" in generated
    assert "image.undo_group_start()" in generated
    assert "try:" in generated
    assert mutation_call in generated
    assert "finally:" in generated
    assert "image.undo_group_end()" in generated
    assert generated.index("image.undo_group_start()") < generated.index(mutation_call)
    assert generated.index(mutation_call) < generated.index("image.undo_group_end()")
