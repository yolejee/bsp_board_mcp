"""Append-only audit log for every tool invocation.

Path is configurable via BOARD_AUDIT_LOG env var. The directory is created
lazily on first write so the server starts even if the audit path is on a
network share that's temporarily unavailable.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any


class AuditLog:
    def __init__(self, path: Path) -> None:
        self.path = path
        self._prepared = False

    def _prepare(self) -> None:
        if self._prepared:
            return
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._prepared = True

    def write(
        self,
        tool: str,
        args: dict[str, Any],
        result_summary: str,
        *,
        rc: int | None = None,
        ok: bool = True,
    ) -> None:
        try:
            self._prepare()
            entry = {
                "ts": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
                "tool": tool,
                "args": {k: _truncate(v) for k, v in args.items()},
                "ok": ok,
                "rc": rc,
                "result": result_summary[:400],
            }
            with self.path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        except OSError:
            # Never let auditing failures kill a tool call.
            pass


def _truncate(v: Any, limit: int = 200) -> Any:
    if isinstance(v, str) and len(v) > limit:
        return v[:limit] + f"...<+{len(v) - limit}>"
    return v
