"""Entry point: `python -m linux_board_mcp`."""

from __future__ import annotations

import sys

from .config import Config
from .server import build_server


def main() -> int:
    try:
        cfg = Config.from_env()
    except ValueError as e:
        print(f"[linux_board_mcp] config error: {e}", file=sys.stderr)
        return 2

    mcp = build_server(cfg)
    # FastMCP.run() blocks on stdio transport until the client disconnects.
    mcp.run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
