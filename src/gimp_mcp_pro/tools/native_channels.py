"""Native channel operation code generators."""

from __future__ import annotations

from typing import Any

from gimp_mcp_pro.tools.native_backend import (
    NativeOperation,
)


def _op_channels(payload: dict[str, Any]) -> list[str]:
    return [
        "images = Gimp.get_images()",
        "if not images: raise RuntimeError('No images are open')",
        "image = images[0]",
        "channels = image.get_channels()",
        "result['channels'] = [{'name': c.get_name(), 'visible': c.get_visible()} for c in channels]",
        "if result['action'] == 'create':\n"
        "    channel = Gimp.Channel.new(image, result.get('name') or 'MCP Channel', image.get_width(), image.get_height(), 100.0, Gegl.Color.new('black'))\n"
        "    image.insert_channel(channel, None, 0)\n"
        "    result['created'] = channel.get_name()",
        "elif result['action'] in {'show', 'hide'} and channels:\n"
        "    channels[0].set_visible(result['action'] == 'show')\n"
        "    result['updated'] = channels[0].get_name()",
        "elif result['action'] == 'to_selection' and channels:\n"
        "    image.select_item(Gimp.ChannelOps.REPLACE, channels[0])\n"
        "    result['selection_changed'] = True",
        "Gimp.displays_flush()",
    ]


def operations() -> dict[str, NativeOperation]:
    """Return registered native backend operations for this concern."""
    return {
        "edit_channels": NativeOperation(
            name="edit_channels", generator=_op_channels, required_payload_keys=("action",)
        ),
        "manage_channels": NativeOperation(
            name="manage_channels", generator=_op_channels, required_payload_keys=("action",)
        ),
    }
