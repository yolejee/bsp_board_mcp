"""MCP tool implementations split by risk class.

`readonly` tools run without prompting in most clients.
`writable` tools change board state — clients should be configured to
prompt for approval before each call.
"""

from . import readonly, writable

__all__ = ["readonly", "writable"]
