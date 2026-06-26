"""Generated GIMP-side context manager snippets for native backend modules."""

from __future__ import annotations

import textwrap


def _dedent(block: str) -> str:
    """Dedent a generated Python block for bridge execution."""
    return textwrap.dedent(block).strip("\n")


def generated_context_helpers(names: list[str] | tuple[str, ...] | set[str]) -> list[str]:
    """Return generated GIMP-side context manager helpers by name."""
    requested = set(names)
    lines: list[str] = []
    if requested:
        lines.extend(["from contextlib import contextmanager", "import gc"])
    if "pdb_config" in requested:
        lines.append(
            _dedent("""
            @contextmanager
            def managed_pdb_config(proc):
                cfg = None
                try:
                    cfg = proc.create_config()
                    yield cfg
                finally:
                    try:
                        del cfg
                    except Exception:
                        pass
                    gc.collect()
            """)
        )
    if "file_obj" in requested:
        lines.append(
            _dedent("""
            @contextmanager
            def managed_file_obj(path):
                file_obj = None
                try:
                    file_obj = Gio.File.new_for_path(path)
                    yield file_obj
                finally:
                    try:
                        del file_obj
                    except Exception:
                        pass
                    gc.collect()
            """)
        )
    if "drawable_filter" in requested:
        lines.append(
            _dedent("""
            @contextmanager
            def managed_drawable_filter(drawable, operation):
                df = None
                cfg = None
                try:
                    df = Gimp.DrawableFilter.new(drawable, operation, '')
                    cfg = df.get_config()
                    yield df, cfg
                finally:
                    try:
                        if df is not None and hasattr(drawable, 'remove_filter'):
                            drawable.remove_filter(df)
                    except Exception:
                        pass
                    try:
                        del cfg
                    except Exception:
                        pass
                    try:
                        del df
                    except Exception:
                        pass
                    gc.collect()
            """)
        )
    if "temporary_duplicate_image" in requested:
        lines.append(
            _dedent("""
            @contextmanager
            def temporary_duplicate_image(image):
                preview_image = None
                try:
                    preview_image = image.duplicate()
                    yield preview_image
                finally:
                    try:
                        if preview_image is not None:
                            preview_image.delete()
                    except Exception:
                        pass
                    try:
                        del preview_image
                    except Exception:
                        pass
                    gc.collect()
            """)
        )
    return lines
