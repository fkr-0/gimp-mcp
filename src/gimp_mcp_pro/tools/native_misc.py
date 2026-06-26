"""Small native backend generators that do not warrant dedicated modules yet."""

from __future__ import annotations

from typing import Any

from gimp_mcp_pro.tools.native_backend import (
    NativeOperation,
)


def _op_palette_create_or_update(payload: dict[str, Any]) -> list[str]:
    return [
        "palette = Gimp.context_get_palette()",
        "palette_name = result['palette']['name']",
        "# Gimp.Palette is referenced for native palette capability detection",
        "result['existing_palette'] = str(palette) if palette else None",
        "result['palette']['native_class'] = str(getattr(Gimp, 'Palette', None))",
    ]


def _op_safe_python_eval(payload: dict[str, Any]) -> list[str]:
    return [
        "import ast, io",
        "from contextlib import redirect_stdout, redirect_stderr",
        "SAFE_EVAL_BUILTINS = {'abs': abs, 'min': min, 'max': max, 'sum': sum, 'len': len, 'round': round}",
        "tree = ast.parse(result['code'], mode='eval' if result['mode'] == 'expression' else 'exec')",
        "stdout = io.StringIO(); stderr = io.StringIO()",
        "with redirect_stdout(stdout), redirect_stderr(stderr):\n"
        "    if result['mode'] == 'expression': result['result'] = eval(compile(tree, '<safe_python_eval>', 'eval'), {'__builtins__': SAFE_EVAL_BUILTINS}, {})\n"
        "    else: exec(compile(tree, '<safe_python_eval>', 'exec'), {'__builtins__': SAFE_EVAL_BUILTINS}, {})",
        "result['stdout'] = stdout.getvalue(); result['stderr'] = stderr.getvalue()",
    ]


def _op_manage_guides_and_grid(payload: dict[str, Any]) -> list[str]:
    return [
        "images = Gimp.get_images()",
        "if not images: raise RuntimeError('No images are open')",
        "image = images[0]",
        "guide_id = image.find_next_guide(0)",
        "guides = []",
        "while guide_id:\n"
        "    guides.append({'id': guide_id, 'orientation': str(image.get_guide_orientation(guide_id)), 'position': image.get_guide_position(guide_id)})\n"
        "    guide_id = image.find_next_guide(guide_id)",
        "if result['action'] == 'add' and result.get('orientation') == 'horizontal': result['guide_id'] = image.add_hguide(int(result.get('position') or 0))",
        "if result['action'] == 'add' and result.get('orientation') == 'vertical': result['guide_id'] = image.add_vguide(int(result.get('position') or 0))",
        "result['guides'] = guides",
        "Gimp.displays_flush()",
    ]


def operations() -> dict[str, NativeOperation]:
    """Return registered native backend operations for this concern."""
    return {
        "palette_create_or_update": NativeOperation(
            name="palette_create_or_update",
            generator=_op_palette_create_or_update,
            required_payload_keys=("palette",),
        ),
        "safe_python_eval": NativeOperation(
            name="safe_python_eval",
            generator=_op_safe_python_eval,
            required_payload_keys=("code", "mode"),
        ),
        "manage_guides_and_grid": NativeOperation(
            name="manage_guides_and_grid",
            generator=_op_manage_guides_and_grid,
            required_payload_keys=("action",),
        ),
    }
