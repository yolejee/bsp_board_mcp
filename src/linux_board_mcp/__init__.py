"""linux_board_mcp — MCP server for operating an embedded Linux board."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("linux-board-mcp")
except PackageNotFoundError:  # running from a source tree that isn't installed
    __version__ = "0.0.0+unknown"

__all__ = ["__version__"]
