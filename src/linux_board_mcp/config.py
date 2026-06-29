"""Environment-driven configuration for linux_board_mcp.

All configuration is read from environment variables so the MCP client
(Claude Code / Cline / Cursor) can inject it via mcp.json `env` block.
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

Transport = Literal["ssh", "adb-usb", "adb-wifi", "serial", "none"]
BoardProbe = Literal["", "pyocd"]

# Max duration for capture_serial (seconds).
SERIAL_CAPTURE_MAX_SECONDS = 300


@dataclass(frozen=True)
class SerialSettings:
    """UART parameters for capture_serial (BOARD_SERIAL_* env vars)."""

    port: str
    baud: int = 115200
    bytesize: int = 8
    parity: str = "N"
    stopbits: int = 1
    login_user: str | None = None
    login_password: str | None = None

    @classmethod
    def from_config(cls, cfg: "Config") -> "SerialSettings":
        return cls(
            port=cfg.serial_port,
            baud=cfg.serial_baud,
            bytesize=cfg.serial_bytesize,
            parity=cfg.serial_parity,
            stopbits=cfg.serial_stopbits,
            login_user=cfg.serial_login_user,
            login_password=cfg.serial_login_password,
        )

    @property
    def configured(self) -> bool:
        return bool(self.port)

    def describe(self) -> str:
        return f"{self.port}@{self.baud}/{self.bytesize}{self.parity.upper()}{self.stopbits}"


@dataclass
class Config:
    transport: Transport
    server_name: str

    # SSH
    ssh_host: str
    ssh_port: int
    ssh_user: str
    ssh_key: str | None
    ssh_password: str | None

    # ADB
    adb_binary: str
    adb_serial: str | None      # device serial (USB) or `host:port` (wifi)
    adb_wifi_host: str | None
    adb_wifi_port: int

    # Serial UART
    serial_port: str
    serial_baud: int
    serial_bytesize: int
    serial_parity: str
    serial_stopbits: int
    serial_login_user: str | None
    serial_login_password: str | None

    # MCU debug probe
    probe_type: BoardProbe
    probe_target: str
    probe_frequency: int

    # Behavior
    default_timeout: float
    audit_log_path: Path
    allow_extra_shell_prefixes: tuple[str, ...]

    @classmethod
    def from_env(cls) -> "Config":
        transport = os.environ.get("BOARD_TRANSPORT", "ssh").lower().strip()
        if transport not in ("ssh", "adb-usb", "adb-wifi", "serial", "none"):
            raise ValueError(
                "BOARD_TRANSPORT must be one of ssh / adb-usb / adb-wifi / serial / none, "
                f"got {transport!r}"
            )

        if transport == "serial" and not os.environ.get("BOARD_SERIAL_PORT"):
            raise ValueError("BOARD_SERIAL_PORT is required when BOARD_TRANSPORT=serial")

        extra = os.environ.get("BOARD_EXTRA_SHELL_PREFIXES", "")
        extra_prefixes = tuple(p.strip() for p in extra.split(",") if p.strip())

        ssh_key = _resolve_ssh_key(os.environ.get("BOARD_KEY"))
        ssh_password = os.environ.get("BOARD_PASSWORD") or None
        if transport == "ssh" and not ssh_key and not ssh_password:
            print(
                "[linux_board_mcp] warning: ssh mode needs BOARD_KEY or BOARD_PASSWORD "
                "(board is contacted on first tool call, not at startup)",
                file=sys.stderr,
            )

        return cls(
            transport=transport,  # type: ignore[arg-type]
            server_name=os.environ.get("BOARD_NAME", "linux-board"),
            ssh_host=os.environ.get("BOARD_HOST", "192.168.7.2"),
            ssh_port=int(os.environ.get("BOARD_PORT", "22")),
            ssh_user=os.environ.get("BOARD_USER", "root"),
            ssh_key=ssh_key,
            ssh_password=ssh_password,
            adb_binary=os.environ.get("ADB_BINARY", "adb"),
            adb_serial=os.environ.get("ADB_SERIAL") or None,
            adb_wifi_host=os.environ.get("ADB_WIFI_HOST") or None,
            adb_wifi_port=int(os.environ.get("ADB_WIFI_PORT", "5555")),
            serial_port=os.environ.get("BOARD_SERIAL_PORT", ""),
            serial_baud=int(os.environ.get("BOARD_SERIAL_BAUD", "115200")),
            serial_bytesize=int(os.environ.get("BOARD_SERIAL_BYTESIZE", "8")),
            serial_parity=os.environ.get("BOARD_SERIAL_PARITY", "N"),
            serial_stopbits=int(os.environ.get("BOARD_SERIAL_STOPBITS", "1")),
            serial_login_user=os.environ.get("BOARD_SERIAL_USER")
            or os.environ.get("BOARD_USER")
            or None,
            serial_login_password=os.environ.get("BOARD_SERIAL_PASSWORD")
            or os.environ.get("BOARD_PASSWORD")
            or None,
            default_timeout=float(os.environ.get("BOARD_TIMEOUT", "15")),
            audit_log_path=Path(
                os.environ.get(
                    "BOARD_AUDIT_LOG",
                    str(Path.home() / ".linux_board_mcp" / "audit.log"),
                )
            ).expanduser(),
            allow_extra_shell_prefixes=extra_prefixes,
            probe_type=_parse_probe_type(
                os.environ.get("BOARD_PROBE_TYPE", "")
            ),
            probe_target=os.environ.get("BOARD_PROBE_TARGET", ""),
            probe_frequency=int(
                os.environ.get("BOARD_PROBE_FREQUENCY", "250000")
            ),
        )


def _resolve_ssh_key(raw: str | None) -> str | None:
    """Return key path only when the file exists; warn and ignore otherwise."""
    if not raw:
        return None
    key_path = Path(raw).expanduser()
    if key_path.is_file():
        return str(key_path)
    print(
        f"[linux_board_mcp] warning: BOARD_KEY {key_path} not found, "
        "ignoring (use BOARD_PASSWORD or fix the path)",
        file=sys.stderr,
    )
    return None


def _parse_probe_type(raw: str) -> "BoardProbe":
    """Validate BOARD_PROBE_TYPE env var."""
    v = raw.strip().lower()
    if not v:
        return ""  # type: ignore[return-value]
    valid = ("pyocd",)
    if v not in valid:
        print(
            f"[linux_board_mcp] warning: unknown BOARD_PROBE_TYPE {raw!r}, "
            f"expected one of {valid} — MCU tools will not be available",
            file=sys.stderr,
        )
        return ""  # type: ignore[return-value]
    return v  # type: ignore[return-value]
