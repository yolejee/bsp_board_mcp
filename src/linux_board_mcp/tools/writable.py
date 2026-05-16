"""Writable / destructive tools.

Each of these changes board state. Configure your MCP client to require
explicit user approval per call. The tool itself also enforces a deny-by-
default policy on paths and arguments.
"""

from __future__ import annotations

import os
import re

from .. import safety
from ..audit import AuditLog
from ..transports.base import Transport, TransportError

_MOD_NAME_RE = re.compile(r"^[A-Za-z0-9_\-]+$")


class WritableTools:
    def __init__(self, transport: Transport, audit: AuditLog):
        self.t = transport
        self.audit = audit

    async def _run(self, cmd: str, *, tool: str, args: dict, timeout: float = 30.0) -> str:
        try:
            r = await self.t.run(cmd, timeout=timeout)
        except TransportError as e:
            msg = f"BOARD_UNREACHABLE: {e}"
            self.audit.write(tool, args, msg, ok=False)
            return msg
        out = r.format()
        self.audit.write(tool, args, out[:200], rc=r.rc, ok=(r.rc == 0))
        return out

    # ----- kernel modules -----

    async def install_module(self, ko_path: str, params: str = "") -> str:
        """Push a local .ko to the board and insmod it.

        ko_path: path on the developer machine (not the board).
        params:  module parameters string, e.g. "debug=1 chan=4".
        """
        if not ko_path.endswith(".ko"):
            return "REJECTED: ko_path must end with .ko"
        if not os.path.isfile(ko_path):
            return f"REJECTED: local file {ko_path!r} not found"
        if any(c in params for c in (";", "&", "|", "<", ">", "\n", "`", "$(")):
            return "REJECTED: params contains shell metacharacters"

        remote = f"/tmp/{os.path.basename(ko_path)}"
        try:
            await self.t.push(ko_path, remote)
        except TransportError as e:
            msg = f"PUSH_FAILED: {e}"
            self.audit.write("install_module", {"ko": ko_path}, msg, ok=False)
            return msg

        cmd = f"insmod {safety.quote(remote)} {params}".strip()
        return await self._run(
            cmd,
            tool="install_module",
            args={"ko_path": ko_path, "remote": remote, "params": params},
        )

    async def remove_module(self, name: str) -> str:
        """rmmod a module by name."""
        if not _MOD_NAME_RE.match(name):
            return "REJECTED: module name must match [A-Za-z0-9_-]"
        return await self._run(
            f"rmmod {safety.quote(name)}",
            tool="remove_module",
            args={"name": name},
        )

    # ----- sysfs writes -----

    async def write_sysfs(self, path: str, value: str) -> str:
        """Write a value to a sysfs node (within the writable allowlist)."""
        ok, reason = safety.check_sysfs_write_target(path)
        if not ok:
            msg = f"REJECTED: {reason}"
            self.audit.write("write_sysfs", {"path": path, "value": value}, msg, ok=False)
            return msg
        if "\n" in value or "\0" in value or len(value) > 256:
            return "REJECTED: value contains control chars or exceeds 256 bytes"

        # Use `printf '%s'` instead of `echo` to avoid shell echo's
        # backslash-escape interpretation on busybox.
        cmd = f"printf %s {safety.quote(value)} > {safety.quote(path)}"
        return await self._run(
            cmd,
            tool="write_sysfs",
            args={"path": path, "value": value},
        )

    # ----- GPIO write -----

    async def set_gpio(self, gpio_number: int, value: int) -> str:
        """Set a previously-exported GPIO to 0 or 1 via legacy sysfs."""
        if not isinstance(gpio_number, int) or gpio_number < 0 or gpio_number > 4096:
            return "REJECTED: gpio_number out of range"
        if value not in (0, 1):
            return "REJECTED: value must be 0 or 1"
        return await self.write_sysfs(
            f"/sys/class/gpio/gpio{gpio_number}/value", str(value)
        )

    async def export_gpio(self, gpio_number: int, direction: str = "out") -> str:
        """Export a GPIO and set its direction (legacy sysfs API)."""
        if direction not in ("in", "out"):
            return "REJECTED: direction must be 'in' or 'out'"
        if not isinstance(gpio_number, int) or gpio_number < 0 or gpio_number > 4096:
            return "REJECTED: gpio_number out of range"
        n = str(gpio_number)
        # /sys/class/gpio/export and /sys/class/gpio/gpio<N>/direction are
        # both inside the writable allowlist.
        r1 = await self.write_sysfs("/sys/class/gpio/export", n)
        r2 = await self.write_sysfs(
            f"/sys/class/gpio/gpio{gpio_number}/direction", direction
        )
        return f"export:\n{r1}\n---\ndirection:\n{r2}"

    # ----- power / reboot -----

    async def reboot_board(self, force: bool = False) -> str:
        """Reboot the board. Almost always fatal to the current session.

        force=True uses SysRq emergency-reboot to bypass clean shutdown.
        Only set when ssh/adb shell is wedged.
        """
        if force:
            # Magic SysRq sequence — instant reboot, no fs sync.
            cmd = "echo b > /proc/sysrq-trigger"
        else:
            cmd = "sync; reboot"
        return await self._run(
            cmd, tool="reboot_board", args={"force": force}, timeout=5
        )
