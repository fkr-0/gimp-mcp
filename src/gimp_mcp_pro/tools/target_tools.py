"""Target resolution and validation tools for GIMP MCP Pro."""

from __future__ import annotations

import json
import logging
from typing import Any

from gimp_mcp_pro.models.common import OperationResult, py_literal
from gimp_mcp_pro.tools.types import AsyncToolBridge, MCPToolRegistrar, ToolResult
from gimp_mcp_pro.utils.errors import GimpCommandError

logger = logging.getLogger("gimp_mcp_pro.tools.target")


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


def _normal_target_types(target_types: list[str] | None) -> list[str]:
    """Normalize requested target type names."""
    allowed = {"image", "layer", "channel", "path"}
    if not target_types:
        return sorted(allowed)
    normalized = sorted({item.lower().strip() for item in target_types if item.strip()})
    invalid = [item for item in normalized if item not in allowed]
    if invalid:
        raise ValueError(f"unsupported target type(s): {', '.join(invalid)}")
    return normalized


def _inventory_code(query: str, target_types: list[str]) -> list[str]:
    """Return generated Python code that builds and searches a target inventory."""
    return [
        "import json",
        "# __gimp_mcp_resolve_target__",
        f"query = {py_literal(query.lower().strip())}",
        f"target_types = set({py_literal(target_types)})",
        "def safe_call(fn, default=None):\n"
        "    try:\n"
        "        return fn()\n"
        "    except Exception:\n"
        "        return default",
        "def stable_id(obj):\n"
        "    return safe_call(lambda: int(obj.get_id()), None) if obj is not None else None",
        "def offsets(obj):\n"
        "    off = safe_call(lambda: obj.get_offsets(), None)\n"
        "    if off is None: return {'x': 0, 'y': 0}\n"
        "    if hasattr(off, 'offset_x'): return {'x': off.offset_x, 'y': off.offset_y}\n"
        "    try: return {'x': off[0], 'y': off[1]}\n"
        "    except Exception: return {'x': 0, 'y': 0}",
        "def score(candidate):\n"
        "    text = ' '.join(str(candidate.get(k, '')) for k in ['id', 'index', 'name', 'type', 'kind']).lower()\n"
        "    if not query: return 0\n"
        "    if query == str(candidate.get('id', '')).lower(): return 100\n"
        "    if query == str(candidate.get('name', '')).lower(): return 90\n"
        "    if query in text: return 50\n"
        "    return 0",
        "images = Gimp.get_images()",
        "candidates = []",
        "for image_index, image in enumerate(images):\n"
        "    image_id = stable_id(image)\n"
        "    if 'image' in target_types:\n"
        "        candidates.append({'kind': 'image', 'type': 'image', 'id': image_id, 'index': image_index, 'name': safe_call(lambda image=image: image.get_name(), f'image-{image_index}'), 'width': safe_call(lambda image=image: image.get_width(), None), 'height': safe_call(lambda image=image: image.get_height(), None), 'visible': True, 'editable': True})\n"
        "    if 'layer' in target_types:\n"
        "        for layer_index, layer in enumerate(safe_call(lambda image=image: image.get_layers(), []) or []):\n"
        "            layer_offsets = offsets(layer)\n"
        "            candidates.append({'kind': 'layer', 'type': type(layer).__name__, 'id': stable_id(layer), 'image_id': image_id, 'index': layer_index, 'name': safe_call(lambda layer=layer: layer.get_name(), ''), 'visible': bool(safe_call(lambda layer=layer: layer.get_visible(), True)), 'editable': not bool(safe_call(lambda layer=layer: layer.get_lock_content(), False)), 'has_alpha': bool(safe_call(lambda layer=layer: layer.has_alpha(), False)), 'bounds': {'x': layer_offsets['x'], 'y': layer_offsets['y'], 'width': safe_call(lambda layer=layer: layer.get_width(), None), 'height': safe_call(lambda layer=layer: layer.get_height(), None)}})\n"
        "    if 'channel' in target_types:\n"
        "        for channel_index, channel in enumerate(safe_call(lambda image=image: image.get_channels(), []) or []):\n"
        "            candidates.append({'kind': 'channel', 'type': type(channel).__name__, 'id': stable_id(channel), 'image_id': image_id, 'index': channel_index, 'name': safe_call(lambda channel=channel: channel.get_name(), ''), 'visible': bool(safe_call(lambda channel=channel: channel.get_visible(), True)), 'editable': True})\n"
        "    if 'path' in target_types:\n"
        "        for path_index, path in enumerate(safe_call(lambda image=image: image.get_paths(), []) or []):\n"
        "            candidates.append({'kind': 'path', 'type': type(path).__name__, 'id': stable_id(path), 'image_id': image_id, 'index': path_index, 'name': safe_call(lambda path=path: path.get_name(), ''), 'visible': True, 'editable': True})",
        "matches = []",
        "for candidate in candidates:\n"
        "    candidate_score = score(candidate)\n"
        "    if candidate_score > 0:\n"
        "        item = dict(candidate)\n"
        "        item['score'] = candidate_score\n"
        "        matches.append(item)",
        "matches.sort(key=lambda item: item.get('score', 0), reverse=True)",
        "result = {'query': query, 'target_types': sorted(target_types), 'matches': matches, 'count': len(matches), 'ambiguity': {'ambiguous': len(matches) != 1, 'reason': 'none' if len(matches) == 1 else ('no_matches' if not matches else 'multiple_matches')}, 'selected': matches[0] if len(matches) == 1 else None}",
        "print(json.dumps(result))",
    ]


def _validate_code(targets: list[Any], required_capabilities: list[str]) -> list[str]:
    """Return generated Python code that validates target references against live inventory."""
    return [
        "import json",
        "# __gimp_mcp_validate_targets__",
        f"targets = {py_literal(targets)}",
        f"required_capabilities = set({py_literal(required_capabilities)})",
        "def safe_call(fn, default=None):\n"
        "    try:\n"
        "        return fn()\n"
        "    except Exception:\n"
        "        return default",
        "def stable_id(obj):\n"
        "    return safe_call(lambda: int(obj.get_id()), None) if obj is not None else None",
        "def layer_candidate(image, image_id, layer, index):\n"
        "    return {'kind': 'layer', 'id': stable_id(layer), 'image_id': image_id, 'index': index, 'name': safe_call(lambda: layer.get_name(), ''), 'visible': bool(safe_call(lambda: layer.get_visible(), True)), 'editable': not bool(safe_call(lambda: layer.get_lock_content(), False)), 'has_alpha': bool(safe_call(lambda: layer.has_alpha(), False)), 'type': type(layer).__name__}",
        "images = Gimp.get_images()",
        "inventory = []",
        "for image_index, image in enumerate(images):\n"
        "    image_id = stable_id(image)\n"
        "    inventory.append({'kind': 'image', 'id': image_id, 'image_id': image_id, 'index': image_index, 'name': safe_call(lambda image=image: image.get_name(), f'image-{image_index}'), 'visible': True, 'editable': True, 'type': 'image'})\n"
        "    for layer_index, layer in enumerate(safe_call(lambda image=image: image.get_layers(), []) or []):\n"
        "        inventory.append(layer_candidate(image, image_id, layer, layer_index))",
        "def target_kind(target):\n"
        "    if isinstance(target, dict): return target.get('kind') or target.get('type')\n"
        "    return None",
        "def target_id(target):\n"
        "    if isinstance(target, dict): return target.get('id')\n"
        "    if isinstance(target, int): return target\n"
        "    return None",
        "def target_name(target):\n"
        "    if isinstance(target, dict): return target.get('name')\n"
        "    if isinstance(target, str): return target\n"
        "    return None",
        "def matches_target(candidate, target):\n"
        "    kind = target_kind(target)\n"
        "    ident = target_id(target)\n"
        "    name = target_name(target)\n"
        "    if kind and str(candidate.get('kind')).lower() != str(kind).lower(): return False\n"
        "    if ident is not None and candidate.get('id') == ident: return True\n"
        "    if name is not None and str(candidate.get('name', '')).lower() == str(name).lower(): return True\n"
        "    return False",
        "validated = []",
        "failures = []",
        "warnings = []",
        "for position, target in enumerate(targets):\n"
        "    matches = [candidate for candidate in inventory if matches_target(candidate, target)]\n"
        "    if not matches:\n"
        "        failures.append({'target': target, 'index': position, 'reason': 'not_found'})\n"
        "        continue\n"
        "    if len(matches) > 1:\n"
        "        failures.append({'target': target, 'index': position, 'reason': 'ambiguous', 'matches': matches})\n"
        "        continue\n"
        "    candidate = matches[0]\n"
        "    if 'visible' in required_capabilities and not candidate.get('visible', False): failures.append({'target': target, 'index': position, 'reason': 'not_visible'})\n"
        "    if 'editable' in required_capabilities and not candidate.get('editable', False): failures.append({'target': target, 'index': position, 'reason': 'not_editable'})\n"
        "    if 'raster' in required_capabilities and candidate.get('kind') != 'layer': failures.append({'target': target, 'index': position, 'reason': 'not_raster_layer'})\n"
        "    if 'alpha' in required_capabilities and not candidate.get('has_alpha', False): warnings.append({'target': target, 'index': position, 'warning': 'missing_alpha_channel'})\n"
        "    validated.append(candidate)",
        "result = {'valid': not failures, 'targets': validated, 'failures': failures, 'warnings': warnings, 'required_capabilities': sorted(required_capabilities)}",
        "print(json.dumps(result))",
    ]


def register_target_tools(mcp: MCPToolRegistrar, bridge: AsyncToolBridge) -> None:
    """Register target resolution and validation tools with the MCP server."""

    @mcp.tool()
    async def resolve_target(
        query: str,
        target_types: list[str] | None = None,
        require_unique: bool = False,
    ) -> ToolResult:
        """Resolve a user or agent target reference into concrete GIMP object IDs.

        Notes:
            This read-only tool prevents silent guesses. It searches images, layers,
            channels, and paths by name, stable ID, type, visibility hints, and index
            text, then reports ambiguity when no single target can be selected safely.

        Args:
            query: Natural-language or structured target reference such as a name or ID.
            target_types: Optional target kinds to search: image, layer, channel, path.
            require_unique: Fail the tool call if the query does not resolve to one target.

        Returns:
            Operation result with matches, selected target when unique, and ambiguity metadata.
        """
        if not query.strip():
            return OperationResult.fail(
                operation="resolve_target", error="query must not be empty"
            ).model_dump()
        try:
            normalized_types = _normal_target_types(target_types)
        except ValueError as exc:
            return OperationResult.fail(operation="resolve_target", error=str(exc)).model_dump()

        try:
            result = await bridge.async_execute_python(_inventory_code(query, normalized_types))
            data = _json_payload(result)
            ambiguous = data.get("ambiguity", {}).get("ambiguous", True)
            if require_unique and ambiguous:
                return OperationResult.fail(
                    operation="resolve_target",
                    error="target reference did not resolve uniquely",
                    data=data,
                ).model_dump()
            return OperationResult.ok(
                operation="resolve_target",
                message=f"Resolved {len(data.get('matches', []))} target candidate(s)",
                data=data,
            ).model_dump()
        except GimpCommandError as e:
            return OperationResult.fail(operation="resolve_target", error=str(e)).model_dump()

    @mcp.tool()
    async def validate_targets(
        targets: list[Any],
        required_capabilities: list[str] | None = None,
    ) -> ToolResult:
        """Validate that proposed targets still exist and support required actions.

        Notes:
            Use this immediately before mutation. It detects missing, ambiguous,
            hidden, locked, non-layer, or otherwise unsupported targets and returns
            actionable failures instead of allowing stale plans to continue.

        Args:
            targets: Target references as IDs, names, or dictionaries with kind/id/name.
            required_capabilities: Capabilities such as visible, editable, raster, or alpha.

        Returns:
            Operation result with validity, validated targets, failures, and warnings.
        """
        if not targets:
            return OperationResult.fail(
                operation="validate_targets", error="targets must not be empty"
            ).model_dump()
        capabilities = sorted({item.lower().strip() for item in (required_capabilities or [])})
        allowed = {"visible", "editable", "raster", "alpha"}
        invalid = [item for item in capabilities if item not in allowed]
        if invalid:
            return OperationResult.fail(
                operation="validate_targets",
                error=f"unsupported required capability/capabilities: {', '.join(invalid)}",
            ).model_dump()

        try:
            result = await bridge.async_execute_python(_validate_code(targets, capabilities))
            data = _json_payload(result)
            if not data.get("valid", False):
                return OperationResult.fail(
                    operation="validate_targets",
                    error="one or more targets are invalid",
                    data=data,
                ).model_dump()
            return OperationResult.ok(
                operation="validate_targets",
                message=f"Validated {len(data.get('targets', []))} target(s)",
                data=data,
            ).model_dump()
        except GimpCommandError as e:
            return OperationResult.fail(operation="validate_targets", error=str(e)).model_dump()
