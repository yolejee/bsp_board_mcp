"""ADB transport — wraps the `adb` CLI as a subprocess.

Supports two modes:
  - mode="usb":  device is plugged in over USB. Optionally select by serial.
  - mode="wifi": connect over the network using `adb connect host:port`.

Why subprocess instead of a Python adb library? The official `adb` binary
is the reference implementation; embedded vendors test against it. Python
libraries lag on newer adb protocol features and TLS-pairing edge cases.
"""

from __future__ import annotations

import asyncio
from typing import Literal

from .base import CommandResult, Transport, TransportError

AdbMode = Literal["usb", "wifi"]


class AdbTransport(Transport):
    name = "adb"

    def __init__(
        self,
        mode: AdbMode,
        adb_binary: str = "adb",
        serial: str | None = None,
        wifi_host: str | None = None,
        wifi_port: int = 5555,
        default_timeout: float = 15.0,
    ) -> None:
        if mode not in ("usb", "wifi"):
            raise ValueError(f"adb mode must be usb/wifi, got {mode!r}")
        if mode == "wifi" and not wifi_host:
            raise ValueError("wifi mode requires wifi_host")

        self.mode = mode
        self.adb_binary = adb_binary
        self.serial = serial
        self.wifi_host = wifi_host
        self.wifi_port = wifi_port
        self.default_timeout = default_timeout

        self._wifi_target = f"{wifi_host}:{wifi_port}" if mode == "wifi" else None
        self._connected = False

    # ----- target selection -----

    def _target_args(self) -> list[str]:
        """Args to prefix every adb call so it lands on the right device."""
        if self.mode == "wifi":
            # After `adb connect`, the device shows up with serial = host:port.
            return ["-s", self._wifi_target]  # type: ignore[list-item]
        if self.serial:
            return ["-s", self.serial]
        return []

    async def _adb(self, args: list[str], timeout: float | None = None) -> CommandResult:
        argv = [self.adb_binary, *self._target_args(), *args]
        to = timeout or self.default_timeout
        try:
            proc = await asyncio.create_subprocess_exec(
                *argv,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            try:
                stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=to)
            except asyncio.TimeoutError:
                proc.kill()
                await proc.wait()
                raise TransportError(f"adb command timed out after {to}s: {' '.join(argv[:6])}")
        except FileNotFoundError as e:
            raise TransportError(
                f"adb binary not found at {self.adb_binary!r}; "
                "install platform-tools and put adb on PATH or set ADB_BINARY"
            ) from e

        return CommandResult(
            stdout=stdout.decode("utf-8", errors="replace"),
            stderr=stderr.decode("utf-8", errors="replace"),
            rc=proc.returncode if proc.returncode is not None else -1,
        )

    # ----- lifecycle -----

    async def connect(self) -> None:
        if self.mode == "wifi":
            r = await self._adb(["connect", self._wifi_target], timeout=10)  # type: ignore[list-item]
            combined = (r.stdout + r.stderr).lower()
            # adb is unhelpfully successful when it fails — has to parse output.
            if "connected" not in combined and "already connected" not in combined:
                raise TransportError(
                    f"adb connect {self._wifi_target} failed: {r.stdout.strip()} {r.stderr.strip()}"
                )

        # Wait for device to be visible.
        r = await self._adb(["wait-for-device"], timeout=15)
        if r.rc != 0:
            raise TransportError(f"adb wait-for-device failed: {r.stderr.strip()}")
        self._connected = True

    async def disconnect(self) -> None:
        self._connected = False
        if self.mode == "wifi" and self._wifi_target:
            await self._adb(["disconnect", self._wifi_target], timeout=5)

    async def _ensure_connected(self) -> None:
        """Run connect() once, lazily, before the first command.

        Critical for wifi mode: without the `adb connect host:port` that
        connect() performs, every `adb -s host:port shell` would fail
        because adb has never been told about that target. For usb mode
        this also does a wait-for-device so a missing board fails clearly.
        """
        if not self._connected:
            await self.connect()

    # ----- core API -----

    async def run(self, cmd: str, timeout: float | None = None) -> CommandResult:
        # `adb shell` runs the command through the device's /system/bin/sh
        # (Android) or /bin/sh (typical embedded Linux with adbd). We pass
        # the command as a single arg so adb doesn't re-quote our quoting.
        await self._ensure_connected()
        r = await self._adb(["shell", cmd], timeout=timeout)
        # adb merges stdout/stderr unless `exec-out` is used; the exit code
        # of `adb shell` is the exit code of the remote command on modern
        # adb (>=23). On older adb, it's always 0 unless adb itself failed.
        return r

    async def push(self, local_path: str, remote_path: str) -> None:
        await self._ensure_connected()
        r = await self._adb(["push", local_path, remote_path], timeout=60)
        if r.rc != 0:
            raise TransportError(
                f"adb push {local_path} -> {remote_path} failed: "
                f"{r.stderr.strip() or r.stdout.strip()}"
            )

    async def pull(self, remote_path: str, local_path: str) -> None:
        await self._ensure_connected()
        r = await self._adb(["pull", remote_path, local_path], timeout=60)
        if r.rc != 0:
            raise TransportError(
                f"adb pull {remote_path} -> {local_path} failed: "
                f"{r.stderr.strip() or r.stdout.strip()}"
            )

    async def is_alive(self) -> bool:
        try:
            r = await self.run("true", timeout=5)
            return r.rc == 0
        except TransportError:
            return False

    def describe(self) -> str:
        if self.mode == "wifi":
            return f"adb-wifi://{self._wifi_target}"
        if self.serial:
            return f"adb-usb://{self.serial}"
        return "adb-usb://(default)"

    # ----- helpers exposed for diagnostic tools -----

    async def list_devices(self) -> str:
        """Run `adb devices -l` — useful when adb-usb fails to find the board."""
        # NOTE: this one bypasses target args because it lists all devices.
        argv = [self.adb_binary, "devices", "-l"]
        try:
            proc = await asyncio.create_subprocess_exec(
                *argv,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=5)
        except (FileNotFoundError, asyncio.TimeoutError) as e:
            raise TransportError(f"adb devices failed: {e}") from e
        return stdout.decode("utf-8", errors="replace")
