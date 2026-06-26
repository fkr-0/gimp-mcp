"""Native PDB operation code generators."""

from __future__ import annotations

from typing import Any

from gimp_mcp_pro.tools.native_backend import (
    NativeOperation,
    generated_context_helpers,
    py_literal,
)


def _op_pdb_introspect_typed(payload: dict[str, Any]) -> list[str]:
    return [
        "pdb = Gimp.get_pdb()",
        "names = list(pdb.query_procedures(result['query'], '', '', '', '', '', '', ''))",
        "for name in names[:result['max_results']]:\n"
        "    proc = pdb.lookup_procedure(name)\n"
        "    cfg = proc.create_config() if proc else None\n"
        "    result['procedures'].append(name)\n"
        "    result['signatures'].append({'name': name, 'config_type': type(cfg).__name__ if cfg else None})",
    ]


def _op_execute_pdb_call(payload: dict[str, Any]) -> list[str]:
    return [
        *generated_context_helpers(["pdb_config"]),
        f"procedure = {py_literal(payload.get('procedure'))}",
        f"arguments = {py_literal(payload.get('arguments_map') or {})}",
        f"allow_deprecated = {bool(payload.get('allow_deprecated'))!r}",
        f"dry_run = {bool(payload.get('dry_run'))!r}",
        f"ALLOWED_PDB_PROCEDURES = allowed_procedures = {py_literal(payload.get('allowed_procedures') or [])}",
        "argument_schema_errors = []",
        "pdb = Gimp.get_pdb()",
        "if pdb is None: raise RuntimeError('PDB not available')",
        "proc = pdb.lookup_procedure(procedure)",
        "if proc is None: raise RuntimeError(f'PDB procedure not found: {procedure}')",
        "if not allow_deprecated and hasattr(proc, 'get_deprecated') and proc.get_deprecated():\n"
        "    raise RuntimeError(f'PDB procedure is deprecated: {procedure}')",
        "with managed_pdb_config(proc) as config:\n"
        "    for key, value in arguments.items():\n"
        "        try:\n"
        "            if value == '$active_image':\n"
        "                images = Gimp.get_images()\n"
        "                if not images: raise RuntimeError('No active image')\n"
        "                value = images[0]\n"
        "            config.set_property(key, value)\n"
        "        except Exception as exc:\n"
        "            argument_schema_errors.append({'argument': key, 'error': str(exc)})\n"
        "    if argument_schema_errors: raise RuntimeError(json.dumps({'argument_schema_errors': argument_schema_errors}))\n"
        "    result['argument_schema_errors'] = argument_schema_errors\n"
        "    result['executed'] = False\n"
        "    result['return_values'] = None\n"
        "    if not dry_run:\n"
        "        pdb_result = proc.run(config)\n"
        "        result['executed'] = True\n"
        "        result['return_values'] = str(pdb_result)",
    ]


def operations() -> dict[str, NativeOperation]:
    """Return registered native backend operations for this concern."""
    return {
        "pdb_introspect_typed": NativeOperation(
            name="pdb_introspect_typed",
            generator=_op_pdb_introspect_typed,
            required_payload_keys=("query",),
        ),
        "execute_pdb_call": NativeOperation(
            name="execute_pdb_call",
            generator=_op_execute_pdb_call,
            required_payload_keys=("procedure", "arguments_map"),
        ),
    }
