"""Behavioural tests for tools and transports.

A fake transport (no board, no subprocess) locks in the two P0 fixes:
read_dmesg's grep-before-tail order, and the ADB transport's lazy connect.
"""

import asyncio

from linux_board_mcp.audit import AuditLog
from linux_board_mcp.tools.readonly import ReadOnlyTools
from linux_board_mcp.tools.writable import WritableTools
from linux_board_mcp.transports.adb import AdbTransport
from linux_board_mcp.transports.base import CommandResult, Transport


class RecordingTransport(Transport):
    """Transport stub that records every command it is asked to run."""

    name = "fake"

    def __init__(self) -> None:
        self.commands: list[str] = []

    async def connect(self) -> None:
        pass

    async def disconnect(self) -> None:
        pass

    async def run(self, cmd: str, timeout: float | None = None) -> CommandResult:
        self.commands.append(cmd)
        return CommandResult(stdout="", stderr="", rc=0)

    async def push(self, local_path: str, remote_path: str) -> None:
        pass

    async def pull(self, remote_path: str, local_path: str) -> None:
        pass

    async def is_alive(self) -> bool:
        return True

    def describe(self) -> str:
        return "fake://test"


class StubAdb(AdbTransport):
    """AdbTransport with only the subprocess layer (`_adb`) stubbed out, so
    the real connect() / _ensure_connected() / run() logic is exercised.
    """

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.adb_calls: list[list[str]] = []

    async def _adb(self, args, timeout=None):
        self.adb_calls.append(list(args))
        # `adb connect` must report success for connect() to accept it.
        stdout = "connected to target" if args[:1] == ["connect"] else ""
        return CommandResult(stdout=stdout, stderr="", rc=0)


# ----- read_dmesg: grep must run before tail -----

class TestReadDmesg:
    def _tools(self, tmp_path):
        t = RecordingTransport()
        return t, ReadOnlyTools(t, AuditLog(tmp_path / "audit.log"))

    def test_plain_tails(self, tmp_path):
        t, ro = self._tools(tmp_path)
        asyncio.run(ro.read_dmesg(lines=50))
        assert t.commands[-1] == "dmesg | tail -n 50"

    def test_grep_runs_before_tail(self, tmp_path):
        t, ro = self._tools(tmp_path)
        asyncio.run(ro.read_dmesg(lines=50, grep="rtc"))
        cmd = t.commands[-1]
        assert cmd == "dmesg | grep -E rtc | tail -n 50"
        # the whole point of the fix: grep the full buffer, then tail
        assert cmd.index("grep") < cmd.index("tail")


# ----- ADB transport: lazy connect -----

class TestAdbLazyConnect:
    def test_wifi_run_issues_adb_connect(self):
        t = StubAdb(mode="wifi", wifi_host="10.0.0.2", wifi_port=5555)
        asyncio.run(t.run("uname -a"))
        # without the lazy-connect fix `adb connect` is never issued and
        # every `adb -s host:port shell` would fail
        assert ["connect", "10.0.0.2:5555"] in t.adb_calls

    def test_connect_happens_once(self):
        t = StubAdb(mode="usb", serial="ABC123")
        asyncio.run(t.run("ls"))
        asyncio.run(t.run("pwd"))
        # connect()'s wait-for-device must appear exactly once across 2 runs
        assert t.adb_calls.count(["wait-for-device"]) == 1

    def test_explicit_connect_is_not_repeated(self):
        t = StubAdb(mode="usb", serial="ABC123")
        asyncio.run(t.connect())
        asyncio.run(t.run("ls"))
        # explicit connect() sets the flag, so run() must not reconnect
        assert t.adb_calls.count(["wait-for-device"]) == 1


# ----- pull_file: input validation -----

class TestPullFile:
    def test_rejects_relative_remote_path(self, tmp_path):
        rw = WritableTools(RecordingTransport(), AuditLog(tmp_path / "audit.log"))
        out = asyncio.run(rw.pull_file("relative/path", str(tmp_path / "x")))
        assert out.startswith("REJECTED")
