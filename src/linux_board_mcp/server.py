"""Wires the transport, safety, and tool layers into a FastMCP server."""

from __future__ import annotations

import sys

from mcp.server.fastmcp import FastMCP

from .audit import AuditLog
from .config import Config
from .tools.readonly import ReadOnlyTools
from .tools.writable import WritableTools
from .transports import build_transport


def build_server(cfg: Config) -> FastMCP:
    transport = build_transport(cfg)
    audit = AuditLog(cfg.audit_log_path)
    ro = ReadOnlyTools(transport, audit, extra_prefixes=cfg.allow_extra_shell_prefixes)
    rw = WritableTools(transport, audit)

    mcp = FastMCP(cfg.server_name)

    # ---- Read-only tools ----

    @mcp.tool()
    async def board_info() -> str:
        """Return basic identity (transport, uname, uptime) of the board."""
        return await ro.board_info()

    @mcp.tool()
    async def read_dmesg(lines: int = 100, grep: str | None = None) -> str:
        """Tail dmesg on the board. Optionally filter by an extended regex.

        Use this first when investigating boot failures, driver errors,
        oopses, or any "what just happened" question.
        """
        return await ro.read_dmesg(lines=lines, grep=grep)

    @mcp.tool()
    async def read_sysfs(path: str) -> str:
        """Read a file under /sys/ (allowlist applies). Path must be absolute."""
        return await ro.read_sysfs(path)

    @mcp.tool()
    async def read_proc(path: str) -> str:
        """Read a file under /proc/ (e.g. /proc/cpuinfo, /proc/interrupts)."""
        return await ro.read_proc(path)

    @mcp.tool()
    async def list_dir(path: str, long: bool = False) -> str:
        """List directory contents. Allowed under /sys, /proc, /dev, /tmp, /var, /etc, /run."""
        return await ro.list_dir(path, long=long)

    @mcp.tool()
    async def lsmod() -> str:
        """List currently loaded kernel modules."""
        return await ro.lsmod()

    @mcp.tool()
    async def modinfo(module: str) -> str:
        """Show metadata about a kernel module."""
        return await ro.modinfo(module)

    @mcp.tool()
    async def read_gpio(gpio_number: int) -> str:
        """Read a GPIO value via legacy /sys/class/gpio (gpio must be exported)."""
        return await ro.read_gpio(gpio_number)

    @mcp.tool()
    async def read_iio(device: str, channel: str) -> str:
        """Read an IIO channel raw value.

        device: literal dir name (e.g. 'iio:device0') OR the 'name' file
                contents (e.g. 'bmp280').
        channel: filename inside the device dir (e.g. 'in_voltage0_raw').
        """
        return await ro.read_iio(device, channel)

    @mcp.tool()
    async def dump_devicetree(subpath: str = "") -> str:
        """List nodes under /proc/device-tree (optionally below `subpath`)."""
        return await ro.dump_devicetree(subpath)

    @mcp.tool()
    async def run_shell(cmd: str) -> str:
        """Run an allow-listed read-only shell command on the board.

        Reject any command that needs to change state — use a dedicated
        writable tool instead. See safety.ALLOW_SHELL_PREFIXES for the list.
        """
        return await ro.run_shell(cmd)

    @mcp.tool()
    async def pull_file(remote_path: str, local_path: str) -> str:
        """Copy a file off the board to the machine running this server.

        remote_path is an absolute path on the board; local_path is the
        destination (overwritten if it exists). Use it to retrieve crash
        dumps, configs, or logs for closer inspection.
        """
        return await ro.pull_file(remote_path, local_path)

    @mcp.tool()
    async def adb_devices() -> str:
        """List adb devices (`adb devices -l`) — adb transports only.

        Diagnostic for when an adb board won't connect: shows whether it
        is visible, offline, or unauthorized.
        """
        return await ro.adb_devices()

    # ---- Writable tools (configure your MCP client to confirm before each call) ----

    @mcp.tool()
    async def install_module(ko_path: str, params: str = "") -> str:
        """DESTRUCTIVE: push a local .ko to the board and insmod it.

        ko_path is on the developer machine. It will be transferred to
        /tmp/<basename> on the board before insmod.
        """
        return await rw.install_module(ko_path, params)

    @mcp.tool()
    async def remove_module(name: str) -> str:
        """DESTRUCTIVE: rmmod a kernel module by name."""
        return await rw.remove_module(name)

    @mcp.tool()
    async def write_sysfs(path: str, value: str) -> str:
        """DESTRUCTIVE: write a value to a sysfs node (writable allowlist only)."""
        return await rw.write_sysfs(path, value)

    @mcp.tool()
    async def set_gpio(gpio_number: int, value: int) -> str:
        """DESTRUCTIVE: drive an exported GPIO to 0 or 1."""
        return await rw.set_gpio(gpio_number, value)

    @mcp.tool()
    async def export_gpio(gpio_number: int, direction: str = "out") -> str:
        """DESTRUCTIVE: export a GPIO and set its direction ('in' or 'out')."""
        return await rw.export_gpio(gpio_number, direction)

    @mcp.tool()
    async def reboot_board(force: bool = False) -> str:
        """DESTRUCTIVE: reboot the board. force=True uses SysRq (no fs sync)."""
        return await rw.reboot_board(force=force)

    # Transport connection happens lazily on the first tool call. Use
    # `board_info` from the client to verify the board is reachable.
    print(
        f"[linux_board_mcp] ready: name={cfg.server_name} target={transport.describe()}",
        file=sys.stderr,
    )

    return mcp
