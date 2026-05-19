"""Serial UART transport using pyserial.

Runs shell commands over a console (login prompt or direct shell, e.g.
Rockchip fiq-debugger @ 1500000 8N1). Each command is suffixed with a
unique end marker so we know when output is complete.
"""

from __future__ import annotations

import asyncio
import base64
import re
import time
import uuid
from pathlib import Path
import serial
from serial import (
    EIGHTBITS,
    FIVEBITS,
    PARITY_EVEN,
    PARITY_NONE,
    PARITY_ODD,
    SEVENBITS,
    SIXBITS,
    STOPBITS_ONE,
    STOPBITS_TWO,
)

from .. import safety
from .base import CommandResult, Transport, TransportError

_MARKER_RE = re.compile(r"__LINUX_BOARD_MCP_([0-9a-f]+)__:(-?\d+)\s*$", re.MULTILINE)


def _parse_parity(value: str):
    v = value.strip().upper()
    if v in ("N", "NONE", "NO"):
        return PARITY_NONE
    if v in ("E", "EVEN"):
        return PARITY_EVEN
    if v in ("O", "ODD"):
        return PARITY_ODD
    raise ValueError(f"BOARD_SERIAL_PARITY must be N/E/O, got {value!r}")


def _parse_stopbits(value: int) -> float:
    if value == 1:
        return STOPBITS_ONE
    if value == 2:
        return STOPBITS_TWO
    raise ValueError(f"BOARD_SERIAL_STOPBITS must be 1 or 2, got {value}")


def _parse_bytesize(value: int) -> int:
    mapping = {5: FIVEBITS, 6: SIXBITS, 7: SEVENBITS, 8: EIGHTBITS}
    if value not in mapping:
        raise ValueError(f"BOARD_SERIAL_BYTESIZE must be 5–8, got {value}")
    return mapping[value]


class SerialTransport(Transport):
    name = "serial"

    def __init__(
        self,
        port: str,
        baud: int = 115200,
        bytesize: int = 8,
        parity: str = "N",
        stopbits: int = 1,
        login_user: str | None = None,
        login_password: str | None = None,
        default_timeout: float = 15.0,
    ) -> None:
        self.port = port
        self.baud = baud
        self.bytesize = bytesize
        self.parity = parity
        self.stopbits = stopbits
        self.login_user = login_user
        self.login_password = login_password
        self.default_timeout = default_timeout

        self._ser: serial.Serial | None = None
        self._lock = asyncio.Lock()

    def _open_serial(self) -> serial.Serial:
        try:
            return serial.Serial(
                port=self.port,
                baudrate=self.baud,
                bytesize=_parse_bytesize(self.bytesize),
                parity=_parse_parity(self.parity),
                stopbits=_parse_stopbits(self.stopbits),
                timeout=0.05,
                write_timeout=5,
            )
        except serial.SerialException as e:
            raise TransportError(f"serial open {self.port!r} failed: {e}") from e

    async def connect(self) -> None:
        async with self._lock:
            await asyncio.get_event_loop().run_in_executor(None, self._connect_sync)

    def _connect_sync(self) -> None:
        if self._ser and self._ser.is_open:
            return
        self._ser = self._open_serial()
        time.sleep(0.3)
        self._drain()
        self._maybe_login()
        self._write_raw(b"\n")
        time.sleep(0.2)
        self._drain()

    def _maybe_login(self) -> None:
        buf = self._read_until(3.0)
        for _ in range(6):
            low = buf.lower()
            if "login:" in low and self.login_user:
                self._write_raw(self.login_user.encode("utf-8") + b"\n")
                buf = self._read_until(3.0)
                continue
            if "password:" in low and self.login_password:
                self._write_raw(self.login_password.encode("utf-8") + b"\n")
                buf = self._read_until(3.0)
                continue
            break

    async def disconnect(self) -> None:
        async with self._lock:
            await asyncio.get_event_loop().run_in_executor(None, self._disconnect_sync)

    def _disconnect_sync(self) -> None:
        if self._ser and self._ser.is_open:
            self._ser.close()
        self._ser = None

    def _wrap_command(self, cmd: str) -> tuple[str, str]:
        mid = uuid.uuid4().hex[:12]
        marker = f"__LINUX_BOARD_MCP_{mid}__"
        wrapped = f"({cmd}) 2>&1; echo {marker}:$?"
        return wrapped, marker

    @staticmethod
    def _split_output(raw: str, marker: str) -> tuple[str, int]:
        normalized = raw.replace("\r\n", "\n").replace("\r", "\n")
        pattern = re.compile(re.escape(marker) + r":(-?\d+)")
        m = pattern.search(normalized)
        if not m:
            raise TransportError(
                f"serial: end marker {marker!r} not found in output "
                f"(last 200 chars: {normalized[-200:]!r})"
            )
        rc = int(m.group(1))
        stdout = normalized[: m.start()]
        lines = [
            ln
            for ln in stdout.splitlines()
            if "__LINUX_BOARD_MCP_" not in ln
            and " 2>&1; echo " not in ln
            and ln.strip() not in ("$?", "_:$?")
        ]
        return "\n".join(lines).strip(), rc

    def _drain(self) -> None:
        if not self._ser:
            return
        while self._ser.in_waiting:
            self._ser.read(self._ser.in_waiting)

    def _write_raw(self, data: bytes) -> None:
        if not self._ser:
            raise TransportError("serial port is not open")
        self._ser.write(data)
        self._ser.flush()

    def _read_until(self, timeout: float) -> str:
        if not self._ser:
            return ""
        buf = ""
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            waiting = self._ser.in_waiting
            if waiting:
                buf += self._ser.read(waiting).decode("utf-8", errors="replace")
            else:
                time.sleep(0.02)
        return buf

    def _run_sync(self, cmd: str, timeout: float) -> CommandResult:
        if not self._ser or not self._ser.is_open:
            raise TransportError("serial port is not open")

        wrapped, marker = self._wrap_command(cmd)
        self._drain()
        self._write_raw(wrapped.encode("utf-8") + b"\n")

        buf = ""
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            waiting = self._ser.in_waiting
            if waiting:
                chunk = self._ser.read(waiting).decode("utf-8", errors="replace")
                buf += chunk.replace("\r\n", "\n").replace("\r", "\n")
                if marker in buf and _MARKER_RE.search(buf):
                    break
            else:
                time.sleep(0.02)

        norm = buf.replace("\r\n", "\n").replace("\r", "\n")
        if marker not in norm:
            raise TransportError(
                f"serial command timed out after {timeout}s: {cmd[:120]!r}"
            )

        stdout, rc = self._split_output(norm, marker)
        return CommandResult(stdout=stdout, stderr="", rc=rc)

    async def run(self, cmd: str, timeout: float | None = None) -> CommandResult:
        to = timeout or self.default_timeout
        async with self._lock:
            loop = asyncio.get_event_loop()
            if not self._ser or not self._ser.is_open:
                await loop.run_in_executor(None, self._connect_sync)
            try:
                return await loop.run_in_executor(None, self._run_sync, cmd, to)
            except TransportError:
                raise
            except serial.SerialException as e:
                raise TransportError(f"serial run failed: {e}") from e

    async def push(self, local_path: str, remote_path: str) -> None:
        data = Path(local_path).read_bytes()
        b64 = base64.b64encode(data).decode("ascii")
        remote_b64 = f"{remote_path}.b64"
        chunk = 3000
        await self.run(f"rm -f {safety.quote(remote_b64)}", timeout=30)
        for i in range(0, len(b64), chunk):
            part = b64[i : i + chunk]
            await self.run(
                f"printf '%s' {safety.quote(part)} >> {safety.quote(remote_b64)}",
                timeout=60,
            )
        r = await self.run(
            f"base64 -d {safety.quote(remote_b64)} > {safety.quote(remote_path)} "
            f"&& rm -f {safety.quote(remote_b64)}",
            timeout=60,
        )
        if r.rc != 0:
            raise TransportError(
                f"serial push {local_path} -> {remote_path} failed: {r.stdout[-500:]}"
            )

    async def pull(self, remote_path: str, local_path: str) -> None:
        r = await self.run(f"base64 {safety.quote(remote_path)}", timeout=60)
        if r.rc != 0:
            raise TransportError(
                f"serial pull {remote_path} failed: {r.stdout[-500:]}"
            )
        b64_line = re.compile(r"^[A-Za-z0-9+/]+=*$")
        chunks = [
            line.strip()
            for line in r.stdout.splitlines()
            if b64_line.match(line.strip())
        ]
        try:
            raw = base64.b64decode("".join(chunks), validate=True)
        except Exception as e:
            raise TransportError(f"serial pull: invalid base64 from board: {e}") from e
        Path(local_path).write_bytes(raw)

    async def is_alive(self) -> bool:
        try:
            r = await self.run("true", timeout=5)
            return r.rc == 0
        except TransportError:
            return False

    def describe(self) -> str:
        return (
            f"serial://{self.port}@{self.baud}"
            f"/{self.bytesize}{self.parity.upper()}{self.stopbits}"
        )
