"""Transport implementations: SSH, ADB (USB / WiFi), and serial UART."""

from .adb import AdbTransport
from .base import CommandResult, Transport, TransportError
from .serial import SerialTransport
from .ssh import SshTransport


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
    if cfg.transport == "serial":
        return SerialTransport(
            port=cfg.serial_port,
            baud=cfg.serial_baud,
            bytesize=cfg.serial_bytesize,
            parity=cfg.serial_parity,
            stopbits=cfg.serial_stopbits,
            login_user=cfg.serial_login_user,
            login_password=cfg.serial_login_password,
            default_timeout=cfg.default_timeout,
        )
    raise ValueError(f"unknown transport: {cfg.transport}")


__all__ = [
    "CommandResult",
    "Transport",
    "TransportError",
    "SshTransport",
    "AdbTransport",
    "SerialTransport",
    "build_transport",
]
