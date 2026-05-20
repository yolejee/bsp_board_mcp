"""Read-only tools.

Each function returns a string (or formatted multi-line string) so the
MCP client can show it directly to the LLM. Errors are returned as
strings prefixed with `ERROR:` rather than raised, so the model sees
them and can recover.
"""

from __future__ import annotations

import asyncio

from .. import safety
from ..audit import AuditLog
from ..config import SERIAL_CAPTURE_MAX_SECONDS, SerialSettings
from ..transports.adb import AdbTransport
from ..transports.base import Transport, TransportError
from ..transports.serial import SerialTransport, capture_serial_output


# All tools share a single Transport + AuditLog passed in by server.py.
class ReadOnlyTools:
    def __init__(
        self,
        transport: Transport,
        audit: AuditLog,
        extra_prefixes: tuple[str, ...] = (),
        serial_settings: SerialSettings | None = None,
    ):
        self.t = transport
        self.audit = audit
        self.extra_prefixes = extra_prefixes
        self.serial_settings = serial_settings or SerialSettings(port="")

    # ----- internal helper -----

    async def _run(self, cmd: str, *, tool: str, args: dict, timeout: float | None = None) -> str:
        try:
            r = await self.t.run(cmd, timeout=timeout)
        except TransportError as e:
            msg = f"BOARD_UNREACHABLE: {e}"
            self.audit.write(tool, args, msg, ok=False)
            return msg
        out = r.format()
        self.audit.write(tool, args, out[:200], rc=r.rc, ok=(r.rc == 0))
        return out

    # ----- dmesg -----

    async def read_dmesg(self, lines: int = 100, grep: str | None = None) -> str:
        """Read the tail of dmesg from the board.

        Args:
            lines: how many trailing lines to fetch (default 100).
            grep: optional extended regex to filter lines.
        """
        lines = max(1, min(int(lines), 5000))
        if grep:
            # grep the whole buffer FIRST, then tail — so `lines` caps the
            # number of matches shown. (Tailing first would make grep only
            # see the last `lines` lines and miss early-boot messages.)
            cmd = f"dmesg | grep -E {safety.quote(grep)} | tail -n {lines}"
        else:
            cmd = f"dmesg | tail -n {lines}"
        return await self._run(cmd, tool="read_dmesg", args={"lines": lines, "grep": grep})

    # ----- generic sysfs/proc/dir read -----

    async def read_sysfs(self, path: str) -> str:
        """Read a file under /sys/. Only paths inside the sysfs allowlist are accepted."""
        ok, reason = safety.check_path(path, safety.SYSFS_READ_ROOTS)
        if not ok:
            return f"REJECTED: {reason}"
        return await self._run(
            f"cat {safety.quote(path)}",
            tool="read_sysfs",
            args={"path": path},
        )

    async def read_proc(self, path: str) -> str:
        """Read a file under /proc/."""
        ok, reason = safety.check_path(path, safety.PROC_READ_ROOTS)
        if not ok:
            return f"REJECTED: {reason}"
        return await self._run(
            f"cat {safety.quote(path)}",
            tool="read_proc",
            args={"path": path},
        )

    async def list_dir(self, path: str, long: bool = False) -> str:
        """List a directory. Allowed under /sys, /proc, /dev, /tmp, /var, /etc."""
        allowed_roots = ("/sys/", "/proc/", "/dev/", "/tmp/", "/var/", "/etc/", "/run/")
        ok, reason = safety.check_path(path, allowed_roots)
        if not ok:
            return f"REJECTED: {reason}"
        flag = "-la" if long else "-1"
        return await self._run(
            f"ls {flag} {safety.quote(path)}",
            tool="list_dir",
            args={"path": path, "long": long},
        )

    # ----- kernel modules -----

    async def lsmod(self) -> str:
        """List currently loaded kernel modules (`lsmod`)."""
        return await self._run("lsmod", tool="lsmod", args={})

    async def modinfo(self, module: str) -> str:
        """Show metadata about a kernel module (`modinfo <name>`)."""
        if not module or not module.replace("_", "").replace("-", "").isalnum():
            return "REJECTED: module name must be alphanumeric (with - or _)"
        return await self._run(
            f"modinfo {safety.quote(module)}",
            tool="modinfo",
            args={"module": module},
        )

    # ----- GPIO / IIO helpers (read-only) -----

    async def read_gpio(self, gpio_number: int) -> str:
        """Read a GPIO line via legacy sysfs (/sys/class/gpio/gpio<N>/value).

        Note: requires the GPIO to already be exported. Newer kernels prefer
        the libgpiod /dev/gpiochip* API — use `read_sysfs` with the chip
        path or `run_shell("gpioget ...")` for that.
        """
        if not isinstance(gpio_number, int) or gpio_number < 0 or gpio_number > 4096:
            return "REJECTED: gpio_number must be an integer in [0, 4096]"
        path = f"/sys/class/gpio/gpio{gpio_number}/value"
        return await self.read_sysfs(path)

    async def read_iio(self, device: str, channel: str) -> str:
        """Read a raw IIO channel.

        device:  name under /sys/bus/iio/devices/ — e.g. 'iio:device0' or
                 a logical name resolved via 'name' file.
        channel: channel filename — e.g. 'in_voltage0_raw', 'in_temp_raw'.
        """
        if not device or not channel:
            return "REJECTED: device and channel are required"
        # Allow both literal device dir names and resolved names.
        if device.startswith("iio:device"):
            dev_path = f"/sys/bus/iio/devices/{device}"
        else:
            # Try to look up by 'name' file.
            lookup = (
                'for d in /sys/bus/iio/devices/iio:device*; do '
                f'  [ "$(cat "$d/name" 2>/dev/null)" = {safety.quote(device)} ]'
                ' && echo "$d" && break; '
                "done"
            )
            try:
                r = await self.t.run(lookup, timeout=5)
            except TransportError as e:
                return f"BOARD_UNREACHABLE: {e}"
            dev_path = r.stdout.strip()
            if not dev_path:
                return f"ERROR: no IIO device named {device!r} found"

        if not channel.replace("_", "").isalnum():
            return "REJECTED: channel name must be alphanumeric/underscore"
        full = f"{dev_path}/{channel}"
        return await self._run(
            f"cat {safety.quote(full)}",
            tool="read_iio",
            args={"device": device, "channel": channel, "path": full},
        )

    # ----- raw UART capture (independent of active transport) -----

    async def capture_serial(
        self,
        seconds: int = 10,
        reboot: bool = False,
        force: bool = False,
    ) -> str:
        """Capture raw UART output for N seconds (BOARD_SERIAL_* from mcp.json).

        reboot=False: passive sniff (no bytes sent).
        reboot=True: write `sync; reboot` (or SysRq if force=True) on the same
        open port, then read immediately for N seconds — no shell marker wait,
        no second connection. Destructive when reboot=True.
        """
        if not self.serial_settings.configured:
            return (
                "REJECTED: BOARD_SERIAL_PORT is not set. "
                "Add BOARD_SERIAL_* env vars (see linux-board-serial in mcp.json)."
            )

        seconds = max(1, min(int(seconds), SERIAL_CAPTURE_MAX_SECONDS))
        args = {
            "seconds": seconds,
            "port": self.serial_settings.port,
            "reboot": reboot,
            "force": force,
        }
        released_serial = False

        if (
            isinstance(self.t, SerialTransport)
            and self.t.port == self.serial_settings.port
        ):
            await self.t.disconnect()
            released_serial = True

        try:
            loop = asyncio.get_event_loop()
            s = self.serial_settings
            text = await loop.run_in_executor(
                None,
                lambda: capture_serial_output(
                    s.port,
                    s.baud,
                    float(seconds),
                    bytesize=s.bytesize,
                    parity=s.parity,
                    stopbits=s.stopbits,
                    reboot=reboot,
                    force=force,
                ),
            )
        except TransportError as e:
            msg = f"SERIAL_CAPTURE_FAILED: {e}"
            self.audit.write("capture_serial", args, msg, ok=False)
            return msg
        except OSError as e:
            msg = f"SERIAL_CAPTURE_FAILED: {e}"
            self.audit.write("capture_serial", args, msg, ok=False)
            return msg
        finally:
            if released_serial:
                await self.t.connect()

        mode = "reboot+capture" if reboot else "sniff"
        header = (
            f"serial: {self.serial_settings.describe()}, "
            f"{mode} {seconds}s\n"
        )
        out = header + text
        self.audit.write("capture_serial", args, out[:200], ok=True)
        return out

    # ----- device tree -----

    async def dump_devicetree(self, subpath: str = "") -> str:
        """Dump a subtree under /proc/device-tree (decoded with fdtdump if available)."""
        root = "/proc/device-tree"
        target = f"{root}/{subpath.lstrip('/')}" if subpath else root
        ok, reason = safety.check_path(target, ("/proc/device-tree/",) if subpath else ("/proc/",))
        if not ok and subpath:
            return f"REJECTED: {reason}"
        # Use `find` to list nodes + `cat` for property values; works
        # without fdtdump installed.
        cmd = (
            f"find {safety.quote(target)} -maxdepth 6 -print "
            f"| head -n 500"
        )
        return await self._run(cmd, tool="dump_devicetree", args={"subpath": subpath})

    # ----- escape hatch -----

    async def run_shell(self, cmd: str) -> str:
        """Run an allow-listed read-only shell command on the board.

        Anything that changes state must go through a dedicated writable
        tool, not this. The allow-list is intentionally conservative.
        """
        ok, reason = safety.check_shell_command(cmd, self.extra_prefixes)
        if not ok:
            msg = f"REJECTED: {reason}"
            self.audit.write("run_shell", {"cmd": cmd}, msg, ok=False)
            return msg
        return await self._run(cmd, tool="run_shell", args={"cmd": cmd})

    # ----- connectivity diagnostics -----

    async def board_info(self) -> str:
        """Return basic identity of the board (uname, uptime, transport)."""
        try:
            uname = await self.t.run("uname -a", timeout=5)
            uptime = await self.t.run("uptime", timeout=5)
        except TransportError as e:
            msg = f"BOARD_UNREACHABLE: {e}"
            self.audit.write("board_info", {}, msg, ok=False)
            return msg
        out = (
            f"transport: {self.t.describe()}\n"
            f"uname: {uname.stdout.strip()}\n"
            f"uptime: {uptime.stdout.strip()}"
        )
        self.audit.write("board_info", {}, out[:200], ok=True)
        return out

    # ----- adb diagnostics -----

    async def adb_devices(self) -> str:
        """List adb devices (`adb devices -l`). Only valid for adb transports.

        Diagnostic for when an adb board fails to connect — shows whether
        it is visible, offline, or unauthorized.
        """
        if not isinstance(self.t, AdbTransport):
            return (
                "REJECTED: adb_devices only applies to adb transports "
                f"(current transport: {self.t.name})"
            )
        try:
            out = await self.t.list_devices()
        except TransportError as e:
            msg = f"BOARD_UNREACHABLE: {e}"
            self.audit.write("adb_devices", {}, msg, ok=False)
            return msg
        self.audit.write("adb_devices", {}, out[:200], ok=True)
        return out
