"""Snapshot comparison and image-state assertion inspection tools."""

from __future__ import annotations

import json
import logging
from typing import Any

from gimp_mcp_pro.models.common import OperationResult
from gimp_mcp_pro.tools.inspect_context_backend import _document_state_code
from gimp_mcp_pro.tools.types import AsyncToolBridge, MCPToolRegistrar, ToolResult
from gimp_mcp_pro.utils.errors import GimpCommandError

logger = logging.getLogger("gimp_mcp_pro.tools.inspect")


def _json_payload(result: dict[str, Any]) -> dict[str, Any]:
    """Extract the first JSON object printed by a generated Python command."""
    outputs = result.get("results", [])
    if isinstance(outputs, dict):
        return outputs
    if not isinstance(outputs, list):
        return {}
    for out in outputs:
        if not isinstance(out, str) or not out.strip():
            continue
        try:
            decoded = json.loads(out.strip())
        except json.JSONDecodeError:
            continue
        if isinstance(decoded, dict):
            return decoded
    return {}


def _scalar_fields(value: Any, prefix: str = "") -> dict[str, Any]:
    """Flatten stable scalar fields from a snapshot for structural comparison."""
    if isinstance(value, dict):
        flattened: dict[str, Any] = {}
        for key, nested in value.items():
            nested_prefix = f"{prefix}.{key}" if prefix else str(key)
            flattened.update(_scalar_fields(nested, nested_prefix))
        return flattened
    if isinstance(value, list):
        return {f"{prefix}.length" if prefix else "length": len(value)}
    if isinstance(value, str | int | float | bool) or value is None:
        return {prefix: value} if prefix else {}
    return {prefix: repr(value)} if prefix else {}


def _region_contains(region: dict[str, Any] | None, x: float, y: float) -> bool:
    """Return whether a point is inside an optional inclusive-exclusive region."""
    if not region:
        return True
    left = float(region.get("x", region.get("origin_x", 0)))
    top = float(region.get("y", region.get("origin_y", 0)))
    width = float(region.get("width", 0))
    height = float(region.get("height", 0))
    return left <= x < left + width and top <= y < top + height


def _sample_color(sample: dict[str, Any]) -> dict[str, float] | None:
    """Extract an RGBA-like mapping from a sampled color payload."""
    raw = sample.get("rgba") or sample.get("color")
    if not isinstance(raw, dict):
        return None
    try:
        return {
            "r": float(raw.get("r", 0.0)),
            "g": float(raw.get("g", 0.0)),
            "b": float(raw.get("b", 0.0)),
            "a": float(raw.get("a", 1.0)),
        }
    except (TypeError, ValueError):
        return None


def _color_delta(before: dict[str, float], after: dict[str, float]) -> float:
    """Return a compact RGBA mean absolute delta."""
    return sum(abs(after[channel] - before[channel]) for channel in ("r", "g", "b", "a")) / 4.0


def _snapshot_samples(snapshot: dict[str, Any]) -> dict[tuple[float, float], dict[str, Any]]:
    """Index sampled colors by point coordinates."""
    samples = snapshot.get("sampled_colors") or snapshot.get("samples") or []
    indexed: dict[tuple[float, float], dict[str, Any]] = {}
    if not isinstance(samples, list):
        return indexed
    for sample in samples:
        if not isinstance(sample, dict):
            continue
        try:
            key = (float(sample["x"]), float(sample["y"]))
        except (KeyError, TypeError, ValueError):
            continue
        indexed[key] = sample
    return indexed


def _compare_snapshot_data(
    before: dict[str, Any],
    after: dict[str, Any],
    *,
    region: dict[str, Any] | None = None,
    ignore_transparent: bool = False,
    tolerance: float = 0.0,
) -> dict[str, Any]:
    """Compare two supplied snapshot-like payloads without mutating GIMP."""
    before_samples = _snapshot_samples(before)
    after_samples = _snapshot_samples(after)
    changed_points: list[tuple[float, float]] = []
    deltas: list[float] = []
    ignored_transparent = 0

    for point in sorted(before_samples.keys() & after_samples.keys()):
        x, y = point
        if not _region_contains(region, x, y):
            continue
        before_color = _sample_color(before_samples[point])
        after_color = _sample_color(after_samples[point])
        if before_color is None or after_color is None:
            continue
        delta = _color_delta(before_color, after_color)
        if ignore_transparent and (before_color["a"] <= 0.0 or after_color["a"] <= 0.0):
            if delta > tolerance:
                ignored_transparent += 1
            continue
        if delta > tolerance:
            changed_points.append(point)
            deltas.append(delta)

    bounding_box: dict[str, int] | None = None
    if changed_points:
        xs = [point[0] for point in changed_points]
        ys = [point[1] for point in changed_points]
        min_x, max_x = int(min(xs)), int(max(xs))
        min_y, max_y = int(min(ys)), int(max(ys))
        bounding_box = {
            "x": min_x,
            "y": min_y,
            "width": max_x - min_x + 1,
            "height": max_y - min_y + 1,
        }

    changed_fields: list[str] = []
    if not before_samples and not after_samples:
        before_fields = _scalar_fields(before)
        after_fields = _scalar_fields(after)
        changed_fields = sorted(
            key
            for key in set(before_fields) | set(after_fields)
            if before_fields.get(key) != after_fields.get(key)
        )

    before_bitmap = before.get("image_data") or before.get("crop_png")
    after_bitmap = after.get("image_data") or after.get("crop_png")
    bitmap_changed = bool(
        before_bitmap is not None and after_bitmap is not None and before_bitmap != after_bitmap
    )

    return {
        "changed_pixels": len(changed_points),
        "bounding_box": bounding_box,
        "mean_delta": round(sum(deltas) / len(deltas), 6) if deltas else 0.0,
        "changed_fields": changed_fields,
        "bitmap_changed": bitmap_changed,
        "ignored_transparent_samples": ignored_transparent,
        "compared_samples": len(before_samples.keys() & after_samples.keys()),
        "region": region,
    }


def _find_layer(state: dict[str, Any], assertion: dict[str, Any]) -> dict[str, Any] | None:
    """Find a layer in a document-state payload by name, id, or index."""
    layers = state.get("layer_tree") or state.get("layers_flat") or state.get("layers") or []
    if not isinstance(layers, list):
        return None
    expected_name = assertion.get("name") or assertion.get("layer_name")
    expected_id = assertion.get("id") or assertion.get("layer_id")
    expected_index = assertion.get("index") or assertion.get("layer_index")
    for layer in layers:
        if not isinstance(layer, dict):
            continue
        if expected_name is not None and layer.get("name") == expected_name:
            return layer
        if expected_id is not None and layer.get("id") == expected_id:
            return layer
        if expected_index is not None and layer.get("index") == expected_index:
            return layer
    return None


def _assertion_result(
    index: int, assertion: dict[str, Any], state: dict[str, Any]
) -> dict[str, Any]:
    """Evaluate one typed image-state assertion."""
    kind = str(assertion.get("type") or assertion.get("kind") or "").strip()
    if kind == "layer_exists":
        layer = _find_layer(state, assertion)
        label = (
            assertion.get("name")
            or assertion.get("layer_name")
            or assertion.get("id")
            or assertion.get("index")
        )
        passed = layer is not None
        return {
            "index": index,
            "type": kind,
            "passed": passed,
            "message": f"Layer {label!r} exists" if passed else f"Layer {label!r} does not exist",
        }
    if kind == "layer_visible":
        layer = _find_layer(state, assertion)
        expected = bool(assertion.get("visible", True))
        actual = bool(layer.get("visible", True)) if layer else None
        passed = layer is not None and actual == expected
        return {
            "index": index,
            "type": kind,
            "passed": passed,
            "expected": expected,
            "actual": actual,
            "message": f"Layer visibility is {actual}, expected {expected}",
        }
    if kind == "dimensions_equal":
        dimensions = state.get("dimensions") or state.get("basic") or {}
        actual_width = dimensions.get("width") if isinstance(dimensions, dict) else None
        actual_height = dimensions.get("height") if isinstance(dimensions, dict) else None
        expected_width = assertion.get("width")
        expected_height = assertion.get("height")
        passed = actual_width == expected_width and actual_height == expected_height
        return {
            "index": index,
            "type": kind,
            "passed": passed,
            "expected": {"width": expected_width, "height": expected_height},
            "actual": {"width": actual_width, "height": actual_height},
            "message": f"Dimensions are {actual_width}x{actual_height}, expected {expected_width}x{expected_height}",
        }
    if kind == "selection_non_empty":
        selection = state.get("selections") or state.get("selection") or {}
        actual = bool(selection.get("non_empty", False)) if isinstance(selection, dict) else False
        expected = bool(assertion.get("expected", True))
        passed = actual == expected
        return {
            "index": index,
            "type": kind,
            "passed": passed,
            "expected": expected,
            "actual": actual,
            "message": f"Selection non-empty is {actual}, expected {expected}",
        }
    if kind == "color_close":
        actual = assertion.get("actual")
        expected = assertion.get("expected")
        tolerance = float(assertion.get("tolerance", 0.01))
        passed = False
        delta = None
        if isinstance(actual, dict) and isinstance(expected, dict):
            actual_color = _sample_color({"rgba": actual})
            expected_color = _sample_color({"rgba": expected})
            if actual_color is not None and expected_color is not None:
                delta = _color_delta(actual_color, expected_color)
                passed = delta <= tolerance
        return {
            "index": index,
            "type": kind,
            "passed": passed,
            "expected": expected,
            "actual": actual,
            "delta": delta,
            "tolerance": tolerance,
            "message": f"Color delta {delta} is within tolerance {tolerance}"
            if passed
            else f"Color delta {delta} exceeds tolerance {tolerance}",
        }
    if kind == "region_changed":
        comparison = assertion.get("comparison") or {}
        changed_pixels = comparison.get("changed_pixels", 0) if isinstance(comparison, dict) else 0
        minimum = int(assertion.get("min_changed_pixels", 1))
        passed = int(changed_pixels) >= minimum
        return {
            "index": index,
            "type": kind,
            "passed": passed,
            "expected": {"min_changed_pixels": minimum},
            "actual": {"changed_pixels": changed_pixels},
            "message": f"Region changed pixels {changed_pixels}, expected at least {minimum}",
        }
    return {
        "index": index,
        "type": kind or "unknown",
        "passed": False,
        "message": f"Unsupported assertion type: {kind or 'missing'}",
    }


def register_snapshot_inspect_tools(mcp: MCPToolRegistrar, bridge: AsyncToolBridge) -> None:
    """Register this focused inspect tool subset."""

    @mcp.tool()
    async def compare_snapshots(
        before: dict[str, Any],
        after: dict[str, Any],
        metrics: list[str] | None = None,
        region: dict[str, Any] | None = None,
        ignore_transparent: bool = False,
        tolerance: float = 0.0,
    ) -> ToolResult:
        """Compare two supplied snapshot, thumbnail, or region payloads.

        Notes:
            This verification tool is intentionally read-only and deterministic.
            It compares sampled region colors when present, otherwise falls back
            to stable scalar-field differences. Ordinary visual mismatches are
            returned as structured data, not exceptions.

        Args:
            before: Snapshot-like payload captured before an operation.
            after: Snapshot-like payload captured after an operation.
            metrics: Optional metric names requested by the caller.
            region: Optional bounded region to limit sampled-color comparison.
            ignore_transparent: Ignore sampled points where either side is fully transparent.
            tolerance: RGBA mean absolute delta threshold for sampled colors.

        Returns:
            Operation result with changed sample count, bounding box, mean delta, and changed fields.
        """
        if not isinstance(before, dict) or not isinstance(after, dict):
            return OperationResult.fail(
                operation="compare_snapshots",
                error="before and after must be snapshot dictionaries",
            ).model_dump()
        if tolerance < 0:
            return OperationResult.fail(
                operation="compare_snapshots",
                error="tolerance must be >= 0",
            ).model_dump()
        data = _compare_snapshot_data(
            before,
            after,
            region=region,
            ignore_transparent=ignore_transparent,
            tolerance=tolerance,
        )
        data["metrics"] = metrics or ["changed_pixels", "bounding_box", "mean_delta"]
        return OperationResult.ok(
            operation="compare_snapshots",
            message="Snapshots compared",
            data=data,
        ).model_dump()

    @mcp.tool()
    async def assert_image_state(
        assertions: list[dict[str, Any]] | None = None,
        state: dict[str, Any] | None = None,
    ) -> ToolResult:
        """Evaluate typed postconditions against supplied or active document state.

        Notes:
            Use this after edits to verify facts such as layer existence,
            layer visibility, canvas dimensions, non-empty selection, and color
            closeness. Failed assertions are reported in ``data.results`` while
            the tool call itself still succeeds.

        Args:
            assertions: List of typed assertion dictionaries.
            state: Optional state payload. When absent, the active GIMP document is observed.

        Returns:
            Operation result whose data contains ``passed`` plus per-assertion results.
        """
        assertion_list = assertions or []
        if not isinstance(assertion_list, list):
            return OperationResult.fail(
                operation="assert_image_state",
                error="assertions must be a list",
            ).model_dump()
        try:
            resolved_state = state
            state_source = "provided"
            if resolved_state is None:
                observed = await bridge.async_execute_python(_document_state_code())
                resolved_state = _json_payload(observed)
                state_source = "observed"
            if not isinstance(resolved_state, dict):
                return OperationResult.fail(
                    operation="assert_image_state",
                    error="state must be a dictionary",
                ).model_dump()
            results = [
                _assertion_result(index, assertion, resolved_state)
                for index, assertion in enumerate(assertion_list)
                if isinstance(assertion, dict)
            ]
            invalid_count = len(assertion_list) - len(results)
            for _ in range(invalid_count):
                results.append(
                    {
                        "index": len(results),
                        "type": "invalid",
                        "passed": False,
                        "message": "Assertion must be a dictionary",
                    }
                )
            passed = all(result.get("passed") is True for result in results)
            return OperationResult.ok(
                operation="assert_image_state",
                message="Image state assertions evaluated",
                data={
                    "passed": passed,
                    "results": results,
                    "assertion_count": len(assertion_list),
                    "state_source": state_source,
                },
            ).model_dump()
        except GimpCommandError as e:
            return OperationResult.fail(operation="assert_image_state", error=str(e)).model_dump()
