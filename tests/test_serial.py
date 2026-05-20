"""Unit tests for serial transport helpers and config."""

import pytest

from linux_board_mcp.audit import AuditLog
from linux_board_mcp.config import Config, SERIAL_CAPTURE_MAX_SECONDS
from linux_board_mcp.tools.readonly import ReadOnlyTools
from linux_board_mcp.transports import build_transport
from linux_board_mcp.transports.base import Transport
from linux_board_mcp.transports.serial import SerialTransport, _parse_parity, _parse_stopbits
from linux_board_mcp.config import SerialSettings


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


class TestCaptureSerial:
    def test_rejects_without_port(self, tmp_path):
        t = RecordingTransportStub()
        ro = ReadOnlyTools(t, AuditLog(tmp_path / "audit.log"), serial_settings=SerialSettings(port=""))
        out = __import__("asyncio").run(ro.capture_serial(seconds=5))
        assert out.startswith("REJECTED")

    def test_clamps_seconds(self, tmp_path, monkeypatch):
        monkeypatch.setenv("BOARD_SERIAL_PORT", "COM3")
        cfg = Config.from_env()
        ro = ReadOnlyTools(
            RecordingTransportStub(),
            AuditLog(tmp_path / "audit.log"),
            serial_settings=SerialSettings.from_config(cfg),
        )
        import unittest.mock as mock

        with mock.patch(
            "linux_board_mcp.tools.readonly.capture_serial_output",
            return_value="boot\n",
        ) as cap:
            out = __import__("asyncio").run(ro.capture_serial(seconds=9999))
        cap.assert_called_once()
        assert cap.call_args[0][2] == float(SERIAL_CAPTURE_MAX_SECONDS)
        assert cap.call_args[1]["reboot"] is False
        assert "boot" in out

    def test_reboot_capture_passes_flags(self, tmp_path, monkeypatch):
        monkeypatch.setenv("BOARD_SERIAL_PORT", "COM3")
        cfg = Config.from_env()
        ro = ReadOnlyTools(
            RecordingTransportStub(),
            AuditLog(tmp_path / "audit.log"),
            serial_settings=SerialSettings.from_config(cfg),
        )
        import unittest.mock as mock

        with mock.patch(
            "linux_board_mcp.tools.readonly.capture_serial_output",
            return_value="U-Boot\n",
        ) as cap:
            out = __import__("asyncio").run(
                ro.capture_serial(seconds=10, reboot=True, force=True)
            )
        assert cap.call_args[1]["reboot"] is True
        assert cap.call_args[1]["force"] is True
        assert "reboot+capture" in out
        assert "U-Boot" in out


class RecordingTransportStub(Transport):
    name = "fake"

    async def connect(self) -> None:
        pass

    async def disconnect(self) -> None:
        pass

    async def run(self, cmd, timeout=None):
        from linux_board_mcp.transports.base import CommandResult

        return CommandResult("", "", 0)

    async def push(self, local_path, remote_path) -> None:
        pass

    async def pull(self, remote_path, local_path) -> None:
        pass

    async def is_alive(self) -> bool:
        return True

    def describe(self) -> str:
        return "fake://test"

