# GIMP MCP Menu Design

## Goal

Make the persistent GIMP-side MCP bridge discoverable in GIMP 3.2 without changing the existing MCP client lifecycle.

## Menu Registration

Register `Start MCP Pro Server` at:

`<Image>/Filters/Development/GIMP MCP Pro`

The procedure remains available through GIMP action search. A static regression test will assert the exact supported menu path.

## Runtime Lifecycle

Codex and Claude automatically launch the repository-local stdio MCP server through:

```text
uv --directory /home/user/code/gimp-mcp run gimp-mcp-pro serve
```

The stdio server connects to the separate persistent plugin bridge inside GIMP over `localhost:9877`. The user starts that bridge once per GIMP session using the menu item or action search. The bridge signals persistent readiness, leaves the GIMP UI responsive, and remains active until shutdown or GIMP exits.

## Deployment And Testing

Add a regression test for the menu path, run the focused plugin lifecycle tests, deploy the plugin into `~/.config/GIMP/3.2/plug-ins/gimp-mcp-pro/`, and confirm the deployed source matches the repository.

The unrelated Firefox desktop-file permissions are explicitly out of scope.
