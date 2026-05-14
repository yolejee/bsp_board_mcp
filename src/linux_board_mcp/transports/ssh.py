"""SSH transport using asyncssh.

Connections are opened per-call (short-lived) to keep the implementation
simple and survive board reboots. asyncssh ~5ms overhead per connection
is dwarfed by command runtime on embedded boards.
"""

from __future__ import annotations

import asyncio

import asyncssh

from .base import CommandResult, Transport, TransportError


class SshTransport(Transport):
    name = "ssh"

    def __init__(
        self,
        host: str,
        port: int = 22,
        user: str = "root",
        key: str | None = None,
        password: str | None = None,
        default_timeout: float = 15.0,
    ) -> None:
        self.host = host
        self.port = port
        self.user = user
        self.key = key
        self.password = password
        self.default_timeout = default_timeout

    async def connect(self) -> None:
        # Sanity check during startup.
        async with await self._open() as _:
            return

    async def disconnect(self) -> None:
        return

    def _connect_kwargs(self) -> dict:
        kw: dict = {
            "host": self.host,
            "port": self.port,
            "username": self.user,
            "known_hosts": None,
        }
        if self.key:
            kw["client_keys"] = [self.key]
        if self.password:
            kw["password"] = self.password
        return kw

    async def _open(self):
        try:
            return await asyncio.wait_for(
                asyncssh.connect(**self._connect_kwargs()),
                timeout=self.default_timeout,
            )
        except (OSError, asyncssh.Error, asyncio.TimeoutError) as e:
            raise TransportError(f"ssh connect to {self.user}@{self.host}:{self.port} failed: {e}") from e

    async def run(self, cmd: str, timeout: float | None = None) -> CommandResult:
        to = timeout or self.default_timeout
        try:
            async with await self._open() as conn:
                r = await asyncio.wait_for(conn.run(cmd, check=False), timeout=to)
                return CommandResult(
                    stdout=r.stdout or "",
                    stderr=r.stderr or "",
                    rc=int(r.exit_status if r.exit_status is not None else -1),
                )
        except asyncio.TimeoutError as e:
            raise TransportError(f"ssh command timed out after {to}s: {cmd[:120]}") from e
        except asyncssh.Error as e:
            raise TransportError(f"ssh run failed: {e}") from e

    async def push(self, local_path: str, remote_path: str) -> None:
        try:
            async with await self._open() as conn:
                await asyncssh.scp(local_path, (conn, remote_path))
        except (OSError, asyncssh.Error) as e:
            raise TransportError(f"scp push {local_path} -> {remote_path} failed: {e}") from e

    async def pull(self, remote_path: str, local_path: str) -> None:
        try:
            async with await self._open() as conn:
                await asyncssh.scp((conn, remote_path), local_path)
        except (OSError, asyncssh.Error) as e:
            raise TransportError(f"scp pull {remote_path} -> {local_path} failed: {e}") from e

    async def is_alive(self) -> bool:
        try:
            r = await self.run("true", timeout=5)
            return r.rc == 0
        except TransportError:
            return False

    def describe(self) -> str:
        return f"ssh://{self.user}@{self.host}:{self.port}"
