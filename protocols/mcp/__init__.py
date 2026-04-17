"""MCP 协议相关接口导出。"""

from typing import TYPE_CHECKING, Any

__all__ = ["MCPClient", "MCPServer", "MCPServerBuilder"]

if TYPE_CHECKING:
    from .client import MCPClient
    from .server import MCPServer, MCPServerBuilder


def __getattr__(name: str) -> Any:
    """按需导入，避免包初始化时加载不必要依赖。"""
    if name == "MCPClient":
        from .client import MCPClient

        return MCPClient

    if name in {"MCPServer", "MCPServerBuilder"}:
        from .server import MCPServer, MCPServerBuilder

        exports = {
            "MCPServer": MCPServer,
            "MCPServerBuilder": MCPServerBuilder,
        }
        return exports[name]

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
