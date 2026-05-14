"""Transport abstract base."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


class TransportError(Exception):
    """Raised when the transport layer fails to reach the board."""


@dataclass
class CommandResult:
    stdout: str
    stderr: str
    rc: int

    def format(self) -> str:
        out = f"[exit={self.rc}]\n{self.stdout}"
        if self.stderr:
            out += f"\n[stderr]\n{self.stderr}"
        return out


class Transport(ABC):
    """Common interface for SSH / ADB transports.

    Commands are passed as already-quoted shell strings because both
    SSH and `adb shell` run them through a remote shell on the board.
    Callers MUST sanitize / quote arguments themselves (see safety.py).
    """

    name: str = "base"

    @abstractmethod
    async def connect(self) -> None: ...

    @abstractmethod
    async def disconnect(self) -> None: ...

    @abstractmethod
    async def run(self, cmd: str, timeout: float | None = None) -> CommandResult: ...

    @abstractmethod
    async def push(self, local_path: str, remote_path: str) -> None: ...

    @abstractmethod
    async def pull(self, remote_path: str, local_path: str) -> None: ...

    @abstractmethod
    async def is_alive(self) -> bool: ...

    @abstractmethod
    def describe(self) -> str:
        """Short human-readable string for audit logs / error messages."""
