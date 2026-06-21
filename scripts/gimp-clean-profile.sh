#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PORT="${GIMP_MCP_PORT:-9877}"
PROFILE_ROOT="${GIMP_MCP_PROFILE_ROOT:-$(mktemp -d -t gimp-mcp-profile-XXXXXX)}"
export XDG_CONFIG_HOME="$PROFILE_ROOT/config"
export GIMP_MCP_PORT="$PORT"
export GIMP_MCP_AUTO_START=1
unset PYTHONHOME || true
unset VIRTUAL_ENV || true
PLUGIN_DIR="$XDG_CONFIG_HOME/GIMP/3.0/plug-ins/gimp_mcp_plugin"
mkdir -p "$PLUGIN_DIR"
cp "$ROOT/gimp_plugin/gimp_mcp_plugin.py" "$PLUGIN_DIR/gimp_mcp_plugin.py"
chmod +x "$PLUGIN_DIR/gimp_mcp_plugin.py"
echo "XDG_CONFIG_HOME=$XDG_CONFIG_HOME"
