"""Transport implementations: SSH and ADB (USB / WiFi)."""

from .base import CommandResult, Transport, TransportError
from .ssh import SshTransport
from .adb import AdbTransport


def build_transport(cfg) -> Transport:
    """Factory: pick the right transport based on config."""
    if cfg.transport == "ssh":
        return SshTransport(
            host=cfg.ssh_host,
            port=cfg.ssh_port,
            user=cfg.ssh_user,
            key=cfg.ssh_key,
            password=cfg.ssh_password,
            default_timeout=cfg.default_timeout,
        )
    if cfg.transport == "adb-usb":
        return AdbTransport(
            mode="usb",
            adb_binary=cfg.adb_binary,
            serial=cfg.adb_serial,
            default_timeout=cfg.default_timeout,
        )
    if cfg.transport == "adb-wifi":
        if not cfg.adb_wifi_host:
            raise ValueError("ADB_WIFI_HOST is required when BOARD_TRANSPORT=adb-wifi")
        return AdbTransport(
            mode="wifi",
            adb_binary=cfg.adb_binary,
            wifi_host=cfg.adb_wifi_host,
            wifi_port=cfg.adb_wifi_port,
            default_timeout=cfg.default_timeout,
        )
    raise ValueError(f"unknown transport: {cfg.transport}")


__all__ = [
    "CommandResult",
    "Transport",
    "TransportError",
    "SshTransport",
    "AdbTransport",
    "build_transport",
]
