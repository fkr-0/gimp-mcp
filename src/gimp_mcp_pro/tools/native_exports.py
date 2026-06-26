"""Native import/export operation code generators."""

from __future__ import annotations

from typing import Any

from gimp_mcp_pro.tools.native_backend import (
    CodeBuilder,
    NativeOperation,
    generated_context_helpers,
)


def _op_import_as_layer_with_metadata(payload: dict[str, Any]) -> list[str]:
    builder = CodeBuilder()
    builder.add("from gi.repository import Gio")
    builder.extend(generated_context_helpers(["file_obj"]))
    builder.extend(
        [
            "images = Gimp.get_images()",
            "if not images: raise RuntimeError('No images are open')",
            "image = images[0]",
            "layer = None",
            "parasite = None",
            "inserted_layer = False",
            "try:\n"
            "    with managed_file_obj(result['source']) as file_obj:\n"
            "        layer = Gimp.file_load_layer(Gimp.RunMode.NONINTERACTIVE, image, file_obj)\n"
            "    if result.get('layer_name'): layer.set_name(result['layer_name'])\n"
            "    placement = result.get('placement') or {}\n"
            "    layer.set_offsets(int(placement.get('x', 0)), int(placement.get('y', 0)))\n"
            "    image.insert_layer(layer, None, 0)\n"
            "    inserted_layer = True\n"
            "    parasite = Gimp.Parasite.new('gimp-mcp-import-metadata', 0, json.dumps(result['metadata'], sort_keys=True).encode('utf-8'))\n"
            "    layer.attach_parasite(parasite)\n"
            "    result['layer_id'] = int(layer.get_id()) if hasattr(layer, 'get_id') else None\n"
            "except Exception:\n"
            "    try:\n"
            "        if inserted_layer and layer is not None:\n"
            "            image.remove_layer(layer)\n"
            "    except Exception:\n"
            "        pass\n"
            "    raise\n"
            "finally:\n"
            "    try:\n"
            "        del parasite\n"
            "    except Exception:\n"
            "        pass\n"
            "    try:\n"
            "        del layer\n"
            "    except Exception:\n"
            "        pass\n"
            "    gc.collect()",
            "Gimp.displays_flush()",
        ]
    )
    return builder.lines


def _op_batch_export_variants(payload: dict[str, Any]) -> list[str]:
    return [
        "from gi.repository import Gio",
        *generated_context_helpers(["pdb_config", "file_obj"]),
        "images = Gimp.get_images()",
        "if not images: raise RuntimeError('No images are open')",
        "image = images[0]",
        "pdb = Gimp.get_pdb()",
        "procedure_by_format = {'png': 'file-png-export', 'jpeg': 'file-jpeg-export', 'jpg': 'file-jpeg-export', 'webp': 'file-webp-export', 'tiff': 'file-tiff-export', 'tif': 'file-tiff-export', 'xcf': 'gimp-xcf-save'}",
        "for index, variant in enumerate(result['variants']):\n"
        "    fmt = str(variant.get('format', 'png')).lower().lstrip('.')\n"
        "    export_proc = None\n"
        "    try:\n"
        "        export_proc = pdb.lookup_procedure(procedure_by_format[fmt])\n"
        "        file_path = f\"{result['base_path']}-{index}.{fmt}\"\n"
        "        with managed_file_obj(file_path) as file_obj:\n"
        "            with managed_pdb_config(export_proc) as config:\n"
        "                config.set_property('file', file_obj)\n"
        "                try: config.set_property('image', image)\n"
        "                except Exception: pass\n"
        "                export_proc.run(config)\n"
        "        result['files'].append(file_path)\n"
        "    finally:\n"
        "        try:\n"
        "            del export_proc\n"
        "        except Exception:\n"
        "            pass\n"
        "        gc.collect()",
    ]


def operations() -> dict[str, NativeOperation]:
    """Return registered native backend operations for this concern."""
    return {
        "import_as_layer_with_metadata": NativeOperation(
            name="import_as_layer_with_metadata",
            generator=_op_import_as_layer_with_metadata,
            required_payload_keys=("source",),
        ),
        "batch_export_variants": NativeOperation(
            name="batch_export_variants",
            generator=_op_batch_export_variants,
            required_payload_keys=("variants", "base_path"),
        ),
    }
