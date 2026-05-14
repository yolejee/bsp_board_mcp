"""Environment-driven configuration for linux_board_mcp.

All configuration is read from environment variables so the MCP client
(Claude Code / Cline / Cursor) can inject it via mcp.json `env` block.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Literal


Transport = Literal["ssh", "adb-usb", "adb-wifi"]


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

    # Behavior
    default_timeout: float
    audit_log_path: Path
    allow_extra_shell_prefixes: tuple[str, ...]

    @classmethod
    def from_env(cls) -> "Config":
        transport = os.environ.get("BOARD_TRANSPORT", "ssh").lower().strip()
        if transport not in ("ssh", "adb-usb", "adb-wifi"):
            raise ValueError(
                f"BOARD_TRANSPORT must be one of ssh / adb-usb / adb-wifi, got {transport!r}"
            )

        extra = os.environ.get("BOARD_EXTRA_SHELL_PREFIXES", "")
        extra_prefixes = tuple(p.strip() for p in extra.split(",") if p.strip())

        return cls(
            transport=transport,  # type: ignore[arg-type]
            server_name=os.environ.get("BOARD_NAME", "linux-board"),
            ssh_host=os.environ.get("BOARD_HOST", "192.168.7.2"),
            ssh_port=int(os.environ.get("BOARD_PORT", "22")),
            ssh_user=os.environ.get("BOARD_USER", "root"),
            ssh_key=os.environ.get("BOARD_KEY") or None,
            ssh_password=os.environ.get("BOARD_PASSWORD") or None,
            adb_binary=os.environ.get("ADB_BINARY", "adb"),
            adb_serial=os.environ.get("ADB_SERIAL") or None,
            adb_wifi_host=os.environ.get("ADB_WIFI_HOST") or None,
            adb_wifi_port=int(os.environ.get("ADB_WIFI_PORT", "5555")),
            default_timeout=float(os.environ.get("BOARD_TIMEOUT", "15")),
            audit_log_path=Path(
                os.environ.get(
                    "BOARD_AUDIT_LOG",
                    str(Path.home() / ".linux_board_mcp" / "audit.log"),
                )
            ).expanduser(),
            allow_extra_shell_prefixes=extra_prefixes,
        )
