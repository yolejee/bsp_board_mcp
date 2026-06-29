"""Wires the transport, safety, and tool layers into a FastMCP server.

Three operating modes are selected by config:

* **Linux mode** (``BOARD_TRANSPORT`` ∈ ssh/adb-usb/adb-wifi/serial, no probe):
  all read-only + writable Linux shell tools, plus ``capture_serial``.
* **MCU mode** (``BOARD_TRANSPORT=none`` + ``BOARD_PROBE_TYPE``): no Linux
  transport — the target is a bare-metal MCU with no shell.  Only
  ``capture_serial`` (passive UART sniff) and the ``mcu_*`` probe tools are
  registered.  Linux shell tools are intentionally omitted: they would only
  send commands the MCU cannot answer.
* **Hybrid** (real transport + probe): both sets registered.
"""

from __future__ import annotations

import sys

from mcp.server.fastmcp import FastMCP

from .audit import AuditLog
from .config import Config, SerialSettings
from .tools.mcu import McuTools
from .tools.readonly import ReadOnlyTools
from .tools.writable import WritableTools
from .transports import build_transport


def build_server(cfg: Config) -> FastMCP:
    audit = AuditLog(cfg.audit_log_path)
    mcp = FastMCP(cfg.server_name)

    serial_settings = SerialSettings.from_config(cfg)
    transport = build_transport(cfg)  # None when BOARD_TRANSPORT=none

    # ---- capture_serial ------------------------------------------------
    # Available in every mode that has a serial port configured.  It only
    # passively reads UART (plus an optional reset byte), so it works for
    # both Linux consoles and bare-metal MCU log output.  In MCU mode the
    # `reboot` flag is meaningless (no shell to reset) — use mcu_reset.
    capture_provider: ReadOnlyTools | None = None
    if serial_settings.configured:
        capture_provider = ReadOnlyTools(
            transport,  # may be None in MCU mode; capture_serial handles that
            audit,
            serial_settings=serial_settings,
        )

        @mcp.tool()
        async def capture_serial(
            seconds: int = 10,
            reboot: bool = False,
            force: bool = False,
        ) -> str:
            """Capture raw UART output for N seconds on BOARD_SERIAL_* (mcp.json).

            Passive sniff of the serial port — works for both Linux board
            consoles and bare-metal MCU log output.

            reboot=True sends a reset sequence over the same open port then
            reads immediately (Linux boards only — for an MCU, use mcu_reset
            instead). force=True uses SysRq instant reboot. seconds clamped
            1–300. Close other apps using the COM port before calling.
            """
            return await capture_provider.capture_serial(
                seconds=seconds, reboot=reboot, force=force
            )

    # ---- Linux shell tools (only when a real transport exists) --------
    if transport is not None:
        ro = ReadOnlyTools(
            transport,
            audit,
            extra_prefixes=cfg.allow_extra_shell_prefixes,
            serial_settings=serial_settings,
        )
        rw = WritableTools(transport, audit)
        _register_linux_tools(mcp, ro, rw)

    # ---- MCU probe tools (only when a debug probe is configured) ------
    if cfg.probe_type:
        from .probes import build_probe

        probe = build_probe(cfg)
        mcu = McuTools(probe, audit)
        _register_mcu_tools(mcp, mcu)
        print(
            f"[linux_board_mcp] MCU tools registered: probe={probe.describe()}",
            file=sys.stderr,
        )

    # ---- ready banner --------------------------------------------------
    if transport is not None:
        target_desc = transport.describe()
        hint = "ssh/adb/serial connects on first tool call — run board_info to verify"
    else:
        target_desc = "none (MCU mode)"
        hint = "no Linux transport — use mcu_* tools via debug probe"
    print(
        f"[linux_board_mcp] ready: name={cfg.server_name} target={target_desc} ({hint})",
        file=sys.stderr,
    )

    return mcp


def _register_linux_tools(mcp: FastMCP, ro: ReadOnlyTools, rw: WritableTools) -> None:
    """Register the read-only + writable Linux shell tools."""

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
    async def adb_devices() -> str:
        """List adb devices (`adb devices -l`) — adb transports only.

        Diagnostic for when an adb board won't connect: shows whether it
        is visible, offline, or unauthorized.
        """
        return await ro.adb_devices()

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

    @mcp.tool()
    async def run_command(cmd: str, timeout: float = 30.0) -> str:
        """DESTRUCTIVE: run an arbitrary shell command on the board.

        Unlike run_shell (read-only allowlist), this can start/stop processes,
        run scripts, and modify board state. Each call requires user approval.
        Deny patterns block the most dangerous commands (rm, dd, mkfs, reboot).
        """
        return await rw.run_command(cmd, timeout)

    @mcp.tool()
    async def pull_file(remote_path: str, local_path: str) -> str:
        """SENSITIVE: copy a file off the board to the machine running this server.

        remote_path is any absolute path on the board; local_path is the
        destination (overwritten if it exists). It can read arbitrary board
        files and write the developer machine, so it is gated like a writable
        tool — keep per-call approval on. Use it to retrieve crash dumps,
        configs, or logs for closer inspection.
        """
        return await rw.pull_file(remote_path, local_path)

    @mcp.tool()
    async def push_file(local_path: str, remote_path: str) -> str:
        """DESTRUCTIVE: copy a file from the dev machine onto the board.

        local_path is on the developer machine (must exist and be a regular file).
        remote_path is the absolute destination path on the board (overwritten if
        it exists). This writes to any path on the board, so it is gated behind
        per-call approval. Use it to deploy binaries, scripts, or configs.
        """
        return await rw.push_file(local_path, remote_path)


def _register_mcu_tools(mcp: FastMCP, mcu: McuTools) -> None:
    """Register the bare-metal MCU debug tools (via JTAG/SWD probe)."""

    @mcp.tool()
    async def mcu_chip_info() -> str:
        """Return target chip identity (CPU core, flash/RAM size, vendor)
        read via the debug probe."""
        return await mcu.chip_info()

    @mcp.tool()
    async def mcu_read_mem(addr: int, size: int = 256) -> str:
        """Read a block of memory from the target MCU.

        Returns a hexdump (offset, hex bytes, ASCII preview).
        addr: start address (supports hex notation like 0x08000000).
        size: bytes to read (clamped to 1–4096, default 256).
        """
        return await mcu.read_mem(addr, size)

    @mcp.tool()
    async def mcu_write_mem(addr: int, data_hex: str) -> str:
        """DESTRUCTIVE: write bytes to target MCU memory.

        addr: destination address (supports hex notation).
        data_hex: hex bytes, e.g. "deadbeef" or "00 11 22 ff" (whitespace OK).
        Max 1024 bytes per call.
        """
        return await mcu.write_mem(addr, data_hex)

    @mcp.tool()
    async def mcu_read_reg(reg: str) -> str:
        """Read a CPU core register.

        ARM Cortex-M registers: r0-r15, sp, lr, pc, xpsr, msp, psp,
        primask, basepri, faultmask, control.
        """
        return await mcu.read_reg(reg)

    @mcp.tool()
    async def mcu_write_reg(reg: str, value: int) -> str:
        """DESTRUCTIVE: write a value to a CPU core register.

        ARM Cortex-M registers: r0-r15, sp, lr, pc, xpsr, msp, psp,
        primask, basepri, faultmask, control.
        """
        return await mcu.write_reg(reg, value)

    @mcp.tool()
    async def mcu_reset(halt: bool = True) -> str:
        """DESTRUCTIVE: reset the target MCU.

        halt=True (default): stop at the reset vector so you can inspect
        initial state before firmware runs.
        halt=False: let firmware start executing immediately after reset.
        """
        return await mcu.reset(halt=halt)

    @mcp.tool()
    async def mcu_halt() -> str:
        """DESTRUCTIVE: halt (pause) the target CPU.

        After halting you can read memory and registers to inspect state.
        """
        return await mcu.halt()

    @mcp.tool()
    async def mcu_resume() -> str:
        """DESTRUCTIVE: resume the target CPU from a halted state."""
        return await mcu.resume()

    @mcp.tool()
    async def mcu_flash(local_path: str, base_addr: int = 0) -> str:
        """DESTRUCTIVE: program firmware (.bin or .hex) onto the target MCU.

        local_path: firmware file on the developer machine.
        base_addr: flash base address for .bin files (default 0 = start of
        flash). Ignored for .hex (addresses come from the file).
        Auto-detects .bin vs .hex by file extension.
        """
        return await mcu.flash(local_path, base_addr)

    @mcp.tool()
    async def mcu_erase(
        addr: int | None = None, size: int | None = None,
    ) -> str:
        """DESTRUCTIVE: erase flash on the target MCU.

        No arguments: mass erase (entire chip).
        addr + size: erase the region starting at addr for size bytes.
        """
        return await mcu.erase(addr, size)
