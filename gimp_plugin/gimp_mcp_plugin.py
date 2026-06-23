#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
GIMP MCP Pro Plugin — Enhanced Model Context Protocol integration for GIMP 3.0+

Key improvements over maorcc's plugin:
- Length-prefixed framing (reliable message boundaries)
- Persistent connections (no reconnect per command)
- Native command handlers for common operations
- Undo group support
- Backward-compatible with JSON boundary detection

Install: Copy this file to your GIMP plugins directory.
  Linux:   ~/.config/GIMP/3.0/plug-ins/gimp-mcp-pro/gimp_mcp_plugin.py
  macOS:   ~/Library/Application Support/GIMP/3.0/plug-ins/gimp-mcp-pro/gimp_mcp_plugin.py
  Windows: %APPDATA%/GIMP/3.0/plug-ins/gimp-mcp-pro/gimp_mcp_plugin.py

Make sure the file is executable (chmod +x on Linux/macOS).
"""

import gi

gi.require_version("Gimp", "3.0")

from gi.repository import Gimp
from gi.repository import GLib
from gi.repository import GObject

import base64
import io
import json
import os
import platform
import queue
import signal
import socket
import struct
import subprocess
import sys
import tempfile
import threading
import traceback

# Protocol constants
HEADER_SIZE = 4
MAX_MESSAGE_SIZE = 100 * 1024 * 1024  # 100 MB
USE_LENGTH_PREFIX = True  # Set False for backward compat with maorcc bridge
AUTOSTART_PROC = "plug-in-mcp-pro-autostart"
SERVER_PROC = "plug-in-mcp-pro-server"
BROWSE_PROC = "plug-in-mcp-pro-browse-flows"
MANAGE_PROC = "plug-in-mcp-pro-manage-flows"
FLOW_PROC_PREFIX = "plug-in-mcp-pro-flow-"


def N_(message):
    return message


def _(message):
    return GLib.dgettext(None, message)


def _env_flag(name, default="0"):
    return os.environ.get(name, default).strip().lower() in {"1", "true", "yes", "on"}


def exec_and_capture(command, context):
    """Execute Python code and capture stdout."""
    buf = io.StringIO()
    old_stdout = sys.stdout
    sys.stdout = buf
    try:
        exec(command, context)
    finally:
        sys.stdout = old_stdout
    return buf.getvalue()


class MCPProPlugin(Gimp.PlugIn):
    """Enhanced GIMP MCP plugin with reliable framing and native handlers."""

    def __init__(self):
        super().__init__()
        self.host = "localhost"
        self.port = int(os.environ.get("GIMP_MCP_PORT", "9877"))
        self.running = False
        self.server_socket = None
        self.server_thread = None
        self.main_loop = None
        self.auto_start_done = False
        self.flow_specs = {}
        # Persistent Python execution context
        self.exec_context = {}
        exec("from gi.repository import Gimp, Gegl", self.exec_context)

    # ------------------------------------------------------------------
    # GIMP Plugin registration
    # ------------------------------------------------------------------

    def do_set_i18n(self, name):
        return False, None, None

    def _maybe_autostart(self, reason):
        if self.auto_start_done:
            return
        if _env_flag("GIMP_MCP_AUTO_START") or _env_flag("GIMP_MCP_PRO_AUTOSTART"):
            self.auto_start_done = True
            blocking = _env_flag("GIMP_MCP_BLOCKING_AUTOSTART") or _env_flag(
                "GIMP_MCP_PRO_BLOCKING_AUTOSTART"
            )
            self._start_server_thread(reason=reason, blocking=blocking)

    def do_init_procedures(self):
        self._maybe_autostart(reason="environment autostart during init")

    def do_query_procedures(self):
        self._maybe_autostart(reason="environment autostart during query")
        return [AUTOSTART_PROC, SERVER_PROC]

    def do_create_procedure(self, name):
        if name == AUTOSTART_PROC:
            return Gimp.Procedure.new(self, name, Gimp.PDBProcType.PERSISTENT, self.run, None)
        if name == SERVER_PROC:
            return self._create_server_procedure(name)
        return None

    def _create_server_procedure(self, name):
        procedure = Gimp.Procedure.new(self, name, Gimp.PDBProcType.PERSISTENT, self.run, None)
        procedure.set_menu_label(_("Start MCP Pro Server"))
        procedure.set_documentation(
            _("Starts the MCP Pro server for AI-assisted GIMP editing"),
            _("Starts a socket server that exposes GIMP operations via MCP"),
            name,
        )
        procedure.set_attribution("GIMP MCP Pro", "GIMP MCP Pro Contributors", "2026")
        procedure.add_menu_path("<Image>/Filters/Development/GIMP MCP Pro")
        return procedure

    def _create_flow_browser_procedure(self, name):
        procedure = Gimp.ImageProcedure.new(
            self, name, Gimp.PDBProcType.TEMPORARY, self.run_flow_browser, None
        )
        label = "Browse All Flows" if name == BROWSE_PROC else "Manage Flows"
        procedure.set_menu_label(_(label))
        procedure.set_documentation(_(label), _("Open the Repeatable Flows catalog"), name)
        procedure.set_image_types("*")
        procedure.add_menu_path("<Image>/Filters/Repeatable Flows/")
        return procedure

    def _create_flow_procedure(self, name, flow):
        procedure = Gimp.ImageProcedure.new(
            self, name, Gimp.PDBProcType.TEMPORARY, self.run_flow, None
        )
        procedure.set_menu_label(_(flow.get("title", flow.get("id", "Repeatable Flow"))))
        procedure.set_documentation(
            _(flow.get("description") or flow.get("title", "Repeatable Flow")),
            _("Run a declarative GIMP MCP Pro flow"),
            name,
        )
        procedure.set_image_types("*")
        procedure.add_menu_path("<Image>/Filters/Repeatable Flows/")
        for parameter in flow.get("parameters", []):
            self._add_flow_argument(procedure, parameter)
        return procedure

    def _add_flow_argument(self, procedure, parameter):
        name = parameter.get("name", "parameter").replace("_", "-")
        label = parameter.get("description") or parameter.get("name", name)
        kind = parameter.get("type", "text")
        default = parameter.get("default")
        flags = GObject.ParamFlags.READWRITE
        if kind == "boolean":
            procedure.add_boolean_argument(name, label, label, bool(default), flags)
        elif kind == "integer":
            procedure.add_int_argument(
                name,
                label,
                label,
                int(parameter.get("minimum", -(2**31))),
                int(parameter.get("maximum", 2**31 - 1)),
                int(default or 0),
                flags,
            )
        elif kind in {"number", "opacity", "angle"}:
            procedure.add_double_argument(
                name,
                label,
                label,
                float(parameter.get("minimum", -1.0e12)),
                float(parameter.get("maximum", 1.0e12)),
                float(default or 0.0),
                flags,
            )
        else:
            procedure.add_string_argument(name, label, label, str(default or ""), flags)

    def _flow_dir(self):
        config_home = os.environ.get("XDG_CONFIG_HOME", os.path.expanduser("~/.config"))
        return os.path.join(config_home, "gimp-mcp-pro", "flows")

    def _load_pinned_flows(self):
        return {
            FLOW_PROC_PREFIX + flow["id"]: flow
            for flow in self._load_all_flows()
            if flow.get("state") == "active" and flow.get("ui", {}).get("pinned")
        }

    def _load_all_flows(self):
        flows = []
        flow_dir = self._flow_dir()
        if not os.path.isdir(flow_dir):
            return flows
        for filename in sorted(os.listdir(flow_dir)):
            if not filename.endswith(".flow.json"):
                continue
            try:
                with open(os.path.join(flow_dir, filename), encoding="utf-8") as handle:
                    flow = json.load(handle)
                if flow.get("id") and flow.get("title"):
                    flows.append(flow)
            except (OSError, ValueError) as exc:
                print(f"Ignoring invalid repeatable flow {filename}: {exc}")
        return flows

    def _save_flow_json(self, flow):
        flow_dir = self._flow_dir()
        os.makedirs(flow_dir, exist_ok=True)
        path = os.path.join(flow_dir, flow["id"] + ".flow.json")
        fd, temporary = tempfile.mkstemp(prefix=".flow-", suffix=".json", dir=flow_dir)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(flow, handle, indent=2, sort_keys=True)
                handle.write("\n")
            os.replace(temporary, path)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)

    def _update_flow_lifecycle(self, flow, action):
        if action == "toggle-active":
            if flow.get("state") == "active":
                flow["state"] = "validated"
                flow.setdefault("ui", {})["pinned"] = False
            elif flow.get("state") == "validated":
                flow["state"] = "active"
            else:
                raise ValueError("Draft flows must be validated through MCP or CLI first")
        elif action == "toggle-pin":
            if flow.get("state") != "active":
                raise ValueError("Only active flows can be pinned")
            ui = flow.setdefault("ui", {})
            ui["pinned"] = not bool(ui.get("pinned"))
        self._save_flow_json(flow)

    def _runner_argv(self):
        config_path = os.path.join(os.path.dirname(self._flow_dir()), "runner.json")
        try:
            with open(config_path, encoding="utf-8") as handle:
                argv = json.load(handle).get("argv")
            if isinstance(argv, list) and argv and all(isinstance(item, str) for item in argv):
                return argv
        except (OSError, ValueError, AttributeError):
            pass
        return ["gimp-mcp-pro"]

    def run_flow(self, procedure, run_mode, image, drawables, config, run_data):
        flow = self.flow_specs.get(procedure.get_name()) or self._load_pinned_flows().get(
            procedure.get_name()
        )
        if flow is None:
            return procedure.new_return_values(Gimp.PDBStatusType.CALLING_ERROR, GLib.Error())
        if run_mode == Gimp.RunMode.INTERACTIVE and flow.get("parameters"):
            gi.require_version("GimpUi", "3.0")
            from gi.repository import GimpUi

            GimpUi.init(procedure.get_name())
            dialog = GimpUi.ProcedureDialog.new(procedure, config, flow.get("title"))
            dialog.fill(None)
            accepted = dialog.run()
            dialog.destroy()
            if not accepted:
                return procedure.new_return_values(Gimp.PDBStatusType.CANCEL, GLib.Error())
        parameters = {}
        for parameter in flow.get("parameters", []):
            key = parameter.get("name", "")
            if key:
                parameters[key] = config.get_property(key.replace("_", "-"))
        self._launch_flow(flow, parameters, image=image)
        return procedure.new_return_values(Gimp.PDBStatusType.SUCCESS, GLib.Error())

    def _capture_preview(self):
        result = self._handle_get_bitmap({"max_width": 512, "max_height": 512})
        payload = result.get("results", {})
        encoded = payload.get("image_data") if isinstance(payload, dict) else None
        if not encoded:
            return None
        fd, path = tempfile.mkstemp(prefix="gimp-flow-preview-", suffix=".png")
        with os.fdopen(fd, "wb") as handle:
            handle.write(base64.b64decode(encoded))
        return path

    def _launch_flow(self, flow, parameters, image=None):
        review = flow.get("review_policy", "final") == "final" and image is not None
        before_preview = self._capture_preview() if review else None
        argv = [
            *self._runner_argv(),
            "flow",
            "--flow-dir",
            self._flow_dir(),
            "run",
            flow["id"],
            "--params-json",
            json.dumps(parameters),
        ]
        process = subprocess.Popen(
            argv,
            start_new_session=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        if review:

            def check_finished():
                if process.poll() is None:
                    return GLib.SOURCE_CONTINUE
                if process.returncode == 0:
                    self._show_final_review(flow, image, before_preview)
                else:
                    Gimp.message(f"Flow '{flow.get('title')}' failed; inspect MCP logs.")
                    if before_preview and os.path.exists(before_preview):
                        os.unlink(before_preview)
                return GLib.SOURCE_REMOVE

            GLib.timeout_add(250, check_finished)

    def _show_final_review(self, flow, image, before_preview):
        gi.require_version("GimpUi", "3.0")
        gi.require_version("Gtk", "3.0")
        from gi.repository import GimpUi, Gtk

        after_preview = self._capture_preview()
        GimpUi.init("gimp-mcp-pro-flow-review")
        dialog = Gtk.Dialog(title=f"Review: {flow.get('title', 'Repeatable Flow')}")
        dialog.add_button(_("Commit"), Gtk.ResponseType.OK)
        dialog.add_button(_("Rollback"), Gtk.ResponseType.REJECT)
        dialog.add_button(_("Keep Open"), Gtk.ResponseType.CLOSE)
        box = dialog.get_content_area()
        box.set_spacing(8)
        previews = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        for label_text, path in (("Before", before_preview), ("After", after_preview)):
            column = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
            column.pack_start(Gtk.Label(label=label_text), False, False, 0)
            if path and os.path.exists(path):
                column.pack_start(Gtk.Image.new_from_file(path), True, True, 0)
            previews.pack_start(column, True, True, 0)
        box.pack_start(previews, True, True, 0)
        box.pack_start(
            Gtk.Label(label="The flow completed as grouped undo phases."), False, False, 0
        )
        dialog.show_all()
        response = dialog.run()
        dialog.destroy()
        if response == Gtk.ResponseType.REJECT:
            for _unused in flow.get("phases", [{}]):
                try:
                    image.undo()
                except Exception as exc:
                    Gimp.message(f"Rollback stopped: {exc}")
                    break
            Gimp.displays_flush()
        for path in (before_preview, after_preview):
            if path and os.path.exists(path):
                os.unlink(path)

    def run_flow_browser(self, procedure, run_mode, image, drawables, config, run_data):
        gi.require_version("GimpUi", "3.0")
        gi.require_version("Gtk", "3.0")
        from gi.repository import GimpUi, Gtk

        GimpUi.init(procedure.get_name())
        managing = procedure.get_name() == MANAGE_PROC
        title = "Manage Repeatable Flows" if managing else "Browse Repeatable Flows"
        dialog = Gtk.Dialog(title=title)
        dialog.add_button(_("Close"), Gtk.ResponseType.CLOSE)
        if managing:
            dialog.add_button(_("Toggle Active"), Gtk.ResponseType.ACCEPT)
            dialog.add_button(_("Toggle Pin"), Gtk.ResponseType.YES)
        else:
            dialog.add_button(_("Run"), Gtk.ResponseType.APPLY)

        content = dialog.get_content_area()
        content.set_spacing(8)
        search = Gtk.SearchEntry()
        search.set_placeholder_text(_("Search flows"))
        content.pack_start(search, False, False, 0)
        selector = Gtk.ComboBoxText()
        content.pack_start(selector, False, False, 0)
        details = Gtk.Label(xalign=0)
        details.set_line_wrap(True)
        content.pack_start(details, True, True, 0)
        flows = self._load_all_flows()
        visible = []

        def refresh(*unused):
            query = search.get_text().strip().lower()
            selector.remove_all()
            visible.clear()
            for flow in flows:
                haystack = " ".join(
                    [flow.get("id", ""), flow.get("title", ""), flow.get("description", "")]
                ).lower()
                if query and query not in haystack:
                    continue
                visible.append(flow)
                selector.append(flow["id"], flow["title"])
            if visible:
                selector.set_active(0)

        def update_details(*unused):
            flow_id = selector.get_active_id()
            flow = next((item for item in visible if item.get("id") == flow_id), None)
            if flow is None:
                details.set_text(_("No matching flows"))
                return
            tags = ", ".join(flow.get("capabilities", [])) or "typed-tools"
            details.set_text(
                f"{flow.get('description', '')}\n\n"
                f"State: {flow.get('state', 'draft')}  |  "
                f"Pinned: {bool(flow.get('ui', {}).get('pinned'))}\nCapabilities: {tags}"
            )

        search.connect("search-changed", refresh)
        selector.connect("changed", update_details)
        refresh()
        dialog.show_all()
        response = dialog.run()
        flow_id = selector.get_active_id()
        selected = next((item for item in visible if item.get("id") == flow_id), None)
        dialog.destroy()
        try:
            if selected is not None and response == Gtk.ResponseType.APPLY:
                if selected.get("state") != "active":
                    raise ValueError("Only active flows can run")
                required_without_default = [
                    item.get("name")
                    for item in selected.get("parameters", [])
                    if item.get("required") and item.get("default") is None
                ]
                if required_without_default:
                    raise ValueError(
                        "Pin this flow to open its parameter dialog; missing: "
                        + ", ".join(required_without_default)
                    )
                parameters = {
                    item["name"]: item.get("default")
                    for item in selected.get("parameters", [])
                    if item.get("name")
                }
                self._launch_flow(selected, parameters, image=image)
            elif selected is not None and response == Gtk.ResponseType.ACCEPT:
                self._update_flow_lifecycle(selected, "toggle-active")
                Gimp.message("Flow state updated. Restart GIMP to refresh pinned menu entries.")
            elif selected is not None and response == Gtk.ResponseType.YES:
                self._update_flow_lifecycle(selected, "toggle-pin")
                Gimp.message("Flow pin updated. Restart GIMP to refresh pinned menu entries.")
        except (OSError, ValueError) as exc:
            Gimp.message(str(exc))
        return procedure.new_return_values(Gimp.PDBStatusType.SUCCESS, GLib.Error())

    def run(self, procedure, *args):
        self._start_server_thread(reason="procedure invocation", blocking=False)
        if self.running:
            self._register_flow_procedures()
            procedure.persistent_ready()
            self.persistent_enable()
            self.main_loop = GLib.MainLoop()
            self.main_loop.run()
        return procedure.new_return_values(Gimp.PDBStatusType.SUCCESS, GLib.Error())

    def _register_flow_procedures(self):
        self.flow_specs = self._load_pinned_flows()
        for name in (BROWSE_PROC, MANAGE_PROC):
            self.add_temp_procedure(self._create_flow_browser_procedure(name))
        for name, flow in self.flow_specs.items():
            self.add_temp_procedure(self._create_flow_procedure(name, flow))

    def _start_server_thread(self, reason="manual", blocking=False):
        if self.running:
            print("MCP Pro Server is already running")
            return

        self.running = True
        try:
            signal.signal(signal.SIGTERM, self._shutdown)
            signal.signal(signal.SIGINT, self._shutdown)
        except ValueError:
            # Signal handlers can only be installed from the main thread.
            pass

        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.settimeout(1.0)
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(1)
        except Exception as e:
            print(f"Server error: {e}")
            self.running = False
            self.server_socket = None
            return

        print(f"GIMP MCP Pro server started on {self.host}:{self.port} ({reason})")
        if blocking:
            self._server_loop()
            return
        self.server_thread = threading.Thread(target=self._server_loop, daemon=False)
        self.server_thread.start()

    def _server_loop(self):
        while self.running and self.server_socket is not None:
            try:
                client, address = self.server_socket.accept()
                print(f"Client connected: {address}")
                t = threading.Thread(target=self._handle_client, args=(client,), daemon=True)
                t.start()
            except socket.timeout:
                continue
            except OSError:
                break
            except Exception as e:
                print(f"Server loop error: {e}")
                break

        print("MCP Pro server stopped")

    def _shutdown(self, signum=None, frame=None):
        print("Shutting down MCP Pro server...")
        self.running = False
        if self.server_socket:
            try:
                self.server_socket.close()
            except:
                pass
            self.server_socket = None
        if self.main_loop is not None and self.main_loop.is_running():
            self.main_loop.quit()

    def do_quit(self):
        self._shutdown()

    # ------------------------------------------------------------------
    # Client handling with length-prefixed framing
    # ------------------------------------------------------------------

    def _handle_client(self, client):
        """Handle a connected client with persistent connection."""
        client.settimeout(None)  # No timeout for persistent connection

        try:
            while self.running:
                try:
                    request = self._receive_message(client)
                    if request is None:
                        break

                    response = self._dispatch_on_gimp_thread(request)
                    self._send_message(client, response)
                except (ConnectionError, BrokenPipeError, OSError):
                    break
                except Exception as e:
                    error_resp = {
                        "status": "error",
                        "error": str(e),
                        "traceback": traceback.format_exc(),
                    }
                    try:
                        self._send_message(client, error_resp)
                    except:
                        break
        finally:
            try:
                client.close()
            except:
                pass
            print("Client disconnected")

    def _dispatch_on_gimp_thread(self, request):
        """Run a decoded request on the persistent GLib/GIMP thread."""
        response_queue = queue.Queue(maxsize=1)

        def dispatch_request():
            try:
                response_queue.put(self._dispatch(request))
            except Exception as exc:
                response_queue.put(
                    {
                        "status": "error",
                        "error": str(exc),
                        "traceback": traceback.format_exc(),
                    }
                )
            return GLib.SOURCE_REMOVE

        GLib.idle_add(dispatch_request)
        while self.running:
            try:
                return response_queue.get(timeout=0.1)
            except queue.Empty:
                continue
        raise RuntimeError("GIMP MCP Pro server stopped before the request completed")

    def _receive_message(self, sock):
        """Receive a message using length-prefixed framing (or JSON fallback)."""
        if USE_LENGTH_PREFIX:
            # Read 4-byte length header
            header = self._recv_exact(sock, HEADER_SIZE)
            if header is None:
                return None
            length = struct.unpack(">I", header)[0]
            if length > MAX_MESSAGE_SIZE:
                raise ValueError(f"Message too large: {length}")

            data = self._recv_exact(sock, length)
            if data is None:
                return None
            return json.loads(data.decode("utf-8"))
        else:
            # JSON boundary fallback
            buf = b""
            while True:
                chunk = sock.recv(8192)
                if not chunk:
                    return None
                buf += chunk
                try:
                    return json.loads(buf.decode("utf-8"))
                except (json.JSONDecodeError, UnicodeDecodeError):
                    continue

    def _send_message(self, sock, data):
        """Send a message with length-prefixed framing (or raw JSON fallback)."""
        payload = json.dumps(data).encode("utf-8")
        if USE_LENGTH_PREFIX:
            header = struct.pack(">I", len(payload))
            sock.sendall(header + payload)
        else:
            sock.sendall(payload)

    def _recv_exact(self, sock, n):
        """Receive exactly n bytes."""
        data = bytearray()
        while len(data) < n:
            chunk = sock.recv(min(n - len(data), 65536))
            if not chunk:
                return None
            data.extend(chunk)
        return bytes(data)

    # ------------------------------------------------------------------
    # Command dispatch
    # ------------------------------------------------------------------

    def _dispatch(self, request):
        """Route a command to the appropriate handler."""
        cmd_type = request.get("type", "")
        params = request.get("params", {})

        handlers = {
            "get_image_bitmap": self._handle_get_bitmap,
            "get_image_metadata": self._handle_get_metadata,
            "get_gimp_info": self._handle_get_gimp_info,
            "get_context_state": self._handle_get_context_state,
            "shutdown": self._handle_shutdown,
            "exec": self._handle_exec,
        }

        handler = handlers.get(cmd_type)
        if handler:
            try:
                return handler(params)
            except Exception as e:
                return {"status": "error", "error": str(e), "traceback": traceback.format_exc()}
        else:
            return {"status": "error", "error": f"Unknown command type: {cmd_type}"}

    # ------------------------------------------------------------------
    # Native handlers
    # ------------------------------------------------------------------

    def _handle_shutdown(self, params):
        """Request server shutdown after returning a success response."""
        threading.Thread(target=self._shutdown, daemon=True).start()
        return {"status": "success", "results": {"shutting_down": True}}

    def _handle_exec(self, params):
        """Execute Python code in GIMP's persistent context."""
        args = params.get("args", [])
        if not args or len(args) < 2:
            return {"status": "error", "error": "exec requires args: [mode, code_array]"}

        mode = args[0]
        code_lines = args[1] if len(args) > 1 else []

        if mode == "pyGObject-eval":
            vals = [str(eval(e, self.exec_context)) for e in code_lines]
            return {"status": "success", "results": vals}
        else:
            # pyGObject-console — execute and capture output
            outputs = []
            for line in code_lines:
                output = exec_and_capture(line, self.exec_context)
                outputs.append(output)
            return {"status": "success", "results": outputs}

    def _handle_get_bitmap(self, params):
        """Get current image as base64 PNG.

        Uses duplicate+flatten+crop instead of Image.new+edit_copy/paste to
        avoid dangling internal refs that crash GIMP's memsize idle handler.
        """
        images = Gimp.get_images()
        if not images:
            return {"status": "error", "error": "No images are open in GIMP"}

        image = images[0]
        max_width = params.get("max_width")
        max_height = params.get("max_height")
        region = params.get("region", {})

        orig_w = image.get_width()
        orig_h = image.get_height()

        needs_region = bool(region)
        cur_w = orig_w
        cur_h = orig_h
        if needs_region:
            cur_w = region.get("width", orig_w)
            cur_h = region.get("height", orig_h)

        needs_scale = bool(max_width and max_height and (cur_w > max_width or cur_h > max_height))

        export_image = None
        try:
            if needs_region or needs_scale:
                export_image = image.duplicate()
                export_image.flatten()

                if needs_region:
                    ox = region.get("origin_x", 0)
                    oy = region.get("origin_y", 0)
                    rw = region.get("width", orig_w)
                    rh = region.get("height", orig_h)
                    export_image.crop(rw, rh, ox, oy)

                if needs_scale:
                    ew = export_image.get_width()
                    eh = export_image.get_height()
                    aspect = ew / eh
                    max_aspect = max_width / max_height
                    if aspect > max_aspect:
                        tw, th = max_width, int(max_width / aspect)
                    else:
                        th, tw = max_height, int(max_height * aspect)
                    export_image.scale(tw, th)
            else:
                export_image = image.duplicate()
                export_image.flatten()

            fd, temp_path = tempfile.mkstemp(suffix=".png")
            os.close(fd)

            try:
                from gi.repository import Gio

                file_obj = Gio.File.new_for_path(temp_path)

                export_proc = Gimp.get_pdb().lookup_procedure("file-png-export")
                if export_proc:
                    cfg = export_proc.create_config()
                    cfg.set_property("image", export_image)
                    cfg.set_property("file", file_obj)
                    try:
                        cfg.set_property("drawables", export_image.get_layers())
                    except Exception:
                        pass
                    export_proc.run(cfg)
                else:
                    Gimp.file_save(Gimp.RunMode.NONINTERACTIVE, export_image, file_obj)

                with open(temp_path, "rb") as f:
                    encoded = base64.b64encode(f.read()).decode("utf-8")

                fw = export_image.get_width()
                fh = export_image.get_height()

                return {
                    "status": "success",
                    "results": {
                        "image_data": encoded,
                        "format": "png",
                        "width": fw,
                        "height": fh,
                        "original_width": orig_w,
                        "original_height": orig_h,
                        "encoding": "base64",
                    },
                }
            finally:
                if os.path.exists(temp_path):
                    os.unlink(temp_path)
        finally:
            if export_image is not None:
                try:
                    export_image.delete()
                except Exception:
                    pass

    def _handle_get_metadata(self, params):
        """Get image metadata without bitmap transfer."""
        images = Gimp.get_images()
        if not images:
            return {"status": "error", "error": "No images are open"}

        image = images[0]
        layers = image.get_layers()
        layers_info = []
        for i, layer in enumerate(layers):
            try:
                info = {
                    "name": layer.get_name(),
                    "visible": layer.get_visible(),
                    "opacity": layer.get_opacity(),
                    "width": layer.get_width(),
                    "height": layer.get_height(),
                    "has_alpha": layer.has_alpha(),
                }
                try:
                    info["blend_mode"] = str(layer.get_mode())
                except:
                    info["blend_mode"] = "unknown"
                layers_info.append(info)
            except Exception as e:
                layers_info.append({"name": f"Layer {i}", "error": str(e)})

        file_info = {}
        try:
            f = image.get_file()
            if f:
                file_info["path"] = f.get_path() if hasattr(f, "get_path") else None
                file_info["basename"] = f.get_basename() if hasattr(f, "get_basename") else None
        except:
            pass

        res_x = res_y = None
        try:
            res_x, res_y = image.get_resolution()
        except:
            pass

        base_map = {0: "RGB", 1: "Grayscale", 2: "Indexed"}

        return {
            "status": "success",
            "results": {
                "basic": {
                    "width": image.get_width(),
                    "height": image.get_height(),
                    "base_type": base_map.get(int(image.get_base_type()), "Unknown"),
                    "resolution_x": res_x,
                    "resolution_y": res_y,
                    "is_dirty": image.is_dirty() if hasattr(image, "is_dirty") else False,
                },
                "structure": {
                    "num_layers": len(layers),
                    "layers": layers_info,
                },
                "file": file_info,
            },
        }

    def _handle_get_gimp_info(self, params):
        """Get GIMP environment information."""
        info = {
            "session": {"num_open_images": len(Gimp.get_images())},
            "gimp": {
                "version": None,
                "resources_loaded": None,
                "api_family": "3.x",
            },
            "system": {
                "platform": platform.platform(),
                "python_version": platform.python_version(),
            },
            "capabilities": {
                "mcp_pro_server": True,
                "length_prefix_framing": USE_LENGTH_PREFIX,
                "persistent_connections": True,
                "reports_version": True,
                "reports_resources_loaded": True,
            },
        }
        try:
            info["gimp"]["version"] = Gimp.version()
        except Exception:
            pass
        try:
            if hasattr(Gimp, "resources_loaded"):
                try:
                    info["gimp"]["resources_loaded"] = Gimp.resources_loaded()
                except TypeError:
                    info["gimp"]["resources_loaded"] = "available_requires_callback"
        except Exception:
            pass
        return {"status": "success", "results": info}

    def _handle_get_context_state(self, params):
        """Get current GIMP context state."""
        state = {}
        try:
            fg = Gimp.context_get_foreground()
            state["foreground_color"] = str(fg)
            if hasattr(fg, "get_rgba"):
                state["foreground_rgba"] = list(fg.get_rgba())
        except:
            pass
        try:
            bg = Gimp.context_get_background()
            state["background_color"] = str(bg)
            if hasattr(bg, "get_rgba"):
                state["background_rgba"] = list(bg.get_rgba())
        except:
            pass
        try:
            state["brush_size"] = Gimp.context_get_brush_size()
        except:
            pass
        try:
            state["opacity"] = Gimp.context_get_opacity()
        except:
            pass

        return {"status": "success", "results": state}


Gimp.main(MCPProPlugin.__gtype__, sys.argv)
