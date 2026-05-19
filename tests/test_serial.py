"""Unit tests for serial transport helpers and config."""

import pytest

from linux_board_mcp.config import Config
from linux_board_mcp.transports import build_transport
from linux_board_mcp.transports.serial import SerialTransport, _parse_parity, _parse_stopbits


class TestSerialConfig:
    def test_from_env_serial(self, monkeypatch):
        monkeypatch.setenv("BOARD_TRANSPORT", "serial")
        monkeypatch.setenv("BOARD_SERIAL_PORT", "COM3")
        monkeypatch.setenv("BOARD_SERIAL_BAUD", "1500000")
        monkeypatch.setenv("BOARD_SERIAL_BYTESIZE", "8")
        monkeypatch.setenv("BOARD_SERIAL_PARITY", "N")
        monkeypatch.setenv("BOARD_SERIAL_STOPBITS", "1")
        monkeypatch.setenv("BOARD_USER", "root")
        monkeypatch.setenv("BOARD_PASSWORD", "secret")
        cfg = Config.from_env()
        assert cfg.transport == "serial"
        assert cfg.serial_port == "COM3"
        assert cfg.serial_baud == 1500000
        assert cfg.serial_login_user == "root"
        assert cfg.serial_login_password == "secret"

    def test_serial_requires_port(self, monkeypatch):
        monkeypatch.setenv("BOARD_TRANSPORT", "serial")
        monkeypatch.delenv("BOARD_SERIAL_PORT", raising=False)
        with pytest.raises(ValueError, match="BOARD_SERIAL_PORT"):
            Config.from_env()


class TestSerialHelpers:
    def test_parse_parity(self):
        assert _parse_parity("none") == _parse_parity("N")

    def test_parse_stopbits(self):
        assert _parse_stopbits(1) is not None

    def test_split_output(self):
        raw = "hello\nworld\n__LINUX_BOARD_MCP_abc123__:0\n# "
        stdout, rc = SerialTransport._split_output(raw, "__LINUX_BOARD_MCP_abc123__")
        assert rc == 0
        assert "hello" in stdout
        assert "world" in stdout

    def test_build_transport(self, monkeypatch):
        monkeypatch.setenv("BOARD_TRANSPORT", "serial")
        monkeypatch.setenv("BOARD_SERIAL_PORT", "COM3")
        cfg = Config.from_env()
        t = build_transport(cfg)
        assert t.name == "serial"
        assert "COM3" in t.describe()

