"""
增强的 MCP 客户端实现

支持多种传输方式的 MCP 客户端
这个实现展示了如何使用不同的传输方式连接到 MCP 服务器

支持的传输方式：
1. Memory: 内存传输（用于测试，直接传递 FastMCP 实例）
2. Stdio: 标准输入输出传输（本地进程，Python/Node.js 脚本）
3. HTTP: HTTP 传输（远程服务器）
4. SSE: Server-Sent Events 传输（实时通信）

使用示例：
```python
# 1. 内存传输（测试）
from fastmcp import FastMCP
server = FastMCP("TestServer")
client = MCPClient(server)

# 2. Stdio 传输（本地脚本）
client = MCPClient("server.py")
client = MCPClient(["python", "server.py"])

# 3. HTTP 传输（远程服务器）
client = MCPClient("https://api.example.com/mcp")

# 4. SSE 传输（实时通信）
client = MCPClient("https://api.example.com/mcp", transport_type="sse")

# 5. 配置传输（高级用法）
config = {
    "transport": "stdio",
    "command": "python",
    "args": ["server.py"],
    "env": {"DEBUG": "1"}
}
client = MCPClient(config)
```
"""

from typing import Dict, Any, List, Optional, Union
import asyncio
import os

from fastmcp import Client as FastClient, FastMCP
from fastmcp.client.transports import PythonStdioTransport, SSETransport, StreamableHttpTransport


class MCPClient:
    """MCP 客户端，支持多种传输方式"""

    def __init__(self,
                 server_source: Union[str, List[str], FastMCP, Dict[str, Any]],
                 server_args: Optional[List[str]] = None,
                 transport_type: Optional[str] = None,
                 env: Optional[Dict[str, str]] = None,
                 **transport_kwargs):
        """
        初始化MCP 客户端

        Args:
            server_source: 服务器源，支持多种格式：
                - FastMCP 实例: 内存传输（用于测试）
                - 字符串路径: Python 脚本路径（如 "server.py"）
                - HTTP URL: 远程服务器（如 "https://api.example.com/mcp"）
                - 命令列表: 完整命令（如 ["python", "server.py"]）
                - 配置字典: 传输配置
            server_args: 服务器参数列表（可选）
            transport_type: 强制指定传输类型 ("stdio", "http", "sse", "memory")
            env: 环境变量字典（传递给MCP服务器进程）
            **transport_kwargs: 传输特定的额外参数

        """
        self.server_args = server_args or []
        self.transport_type = transport_type
        # MCP SDK 默认只继承 PATH 等白名单变量，不含 TOKEN/KEY 等凭证，
        # 因此未指定 env 时继承完整 os.environ（load_dotenv 已加载 .env）
        self.env = env if env is not None else os.environ.copy()
        self.transport_kwargs = transport_kwargs
        self.server_source = self._prepare_server_source(server_source)
        self.client: Optional[FastClient] = None
        self._context_manager = None

    def _prepare_server_source(self, server_source: Union[str, List[str], FastMCP, Dict[str, Any]]):
        """准备服务器源，根据类型创建合适的传输配置"""
        
        # 1. FastMCP 实例 - 内存传输
        if isinstance(server_source, FastMCP):
            print(f"[内存传输] {server_source.name}")
            return server_source
        
        # 2. 配置字典 - 根据配置创建传输
        if isinstance(server_source, dict):
            print(f"[配置传输] transport={server_source.get('transport', 'stdio')}")
            return self._create_transport_from_config(server_source)
        
        # 3. HTTP URL - HTTP/SSE 传输
        if isinstance(server_source, str) and (server_source.startswith("http://") or server_source.startswith("https://")):
            transport_type = self.transport_type or "http"
            print(f"[{transport_type.upper()} 传输] {server_source}")
            if transport_type == "sse":
                return SSETransport(url=server_source, **self.transport_kwargs)
            else:
                return StreamableHttpTransport(url=server_source, **self.transport_kwargs)

        # 4. Python 脚本路径 - Stdio 传输
        if isinstance(server_source, str) and server_source.endswith(".py"):
            print(f"[Stdio/Python 传输] {server_source}")
            return PythonStdioTransport(
                script_path=server_source,
                args=self.server_args,
                env=self.env if self.env else None,
                **self.transport_kwargs
            )

        # 5. 命令列表 - Stdio 传输
        if isinstance(server_source, list) and len(server_source) >= 1:
            print(f"[Stdio/命令 传输] {' '.join(server_source)}")
            if server_source[0] == "python" and len(server_source) > 1 and server_source[1].endswith(".py"):
                # Python 脚本
                return PythonStdioTransport(
                    script_path=server_source[1],
                    args=server_source[2:] + self.server_args,
                    env=self.env if self.env else None,
                    **self.transport_kwargs
                )
            else:
                # 其他命令，使用通用 Stdio 传输
                from fastmcp.client.transports import StdioTransport
                return StdioTransport(
                    command=server_source[0],
                    args=server_source[1:] + self.server_args,
                    env=self.env if self.env else None,
                    **self.transport_kwargs
                )
        
        # 6. 其他情况 - 直接返回，让 FastMCP 自动推断
        print(f"[自动推断传输] {server_source}")
        return server_source

    def _create_transport_from_config(self, config: Dict[str, Any]):
        """从配置字典创建传输"""
        transport_type = config.get("transport", "stdio")
        
        if transport_type == "stdio":
            # 检查是否是 Python 脚本
            args = config.get("args", [])
            if args and args[0].endswith(".py"):
                return PythonStdioTransport(
                    script_path=args[0],
                    args=args[1:] + self.server_args,
                    env=config.get("env") or self.env,
                    cwd=config.get("cwd"),
                    **self.transport_kwargs
                )
            else:
                # 使用通用 Stdio 传输
                from fastmcp.client.transports import StdioTransport
                return StdioTransport(
                    command=config.get("command", "python"),
                    args=args + self.server_args,
                    env=config.get("env") or self.env,
                    cwd=config.get("cwd"),
                    **self.transport_kwargs
                )
        elif transport_type == "sse":
            return SSETransport(
                url=config["url"],
                headers=config.get("headers"),
                auth=config.get("auth"),
                **self.transport_kwargs
            )
        elif transport_type == "http":
            return StreamableHttpTransport(
                url=config["url"],
                headers=config.get("headers"),
                auth=config.get("auth"),
                **self.transport_kwargs
            )
        else:
            raise ValueError(f"Unsupported transport type: {transport_type}")

    async def __aenter__(self):
        """异步上下文管理器入口"""
        print("[MCPClient] 连接到 MCP 服务器...")
        try:
            self.client = FastClient(self.server_source)
            self._context_manager = self.client
            await self._context_manager.__aenter__()
            print("[MCPClient] 连接成功")
        except Exception as e:
            print(f"[MCPClient] 连接失败: {type(e).__name__}: {e}")
            raise
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        if self._context_manager:
            try:
                await self._context_manager.__aexit__(exc_type, exc_val, exc_tb)
            except Exception as e:
                print(f"[MCPClient] 断开连接时出错: {type(e).__name__}: {e}")
            finally:
                self.client = None
                self._context_manager = None
        if exc_type:
            print(f"[MCPClient] 连接已断开 (异常: {exc_type.__name__}: {exc_val})")
        else:
            print("[MCPClient] 连接已断开")

    async def list_tools(self) -> List[Dict[str, Any]]:
        """列出所有可用的工具"""
        if not self.client:
            raise RuntimeError("Client not connected. Use 'async with client:' context manager.")

        result = await self.client.list_tools()

        # 处理不同的返回格式
        if hasattr(result, 'tools'):
            tools = result.tools
        elif isinstance(result, list):
            tools = result
        else:
            tools = []

        return [
            {
                "name": tool.name,
                "description": tool.description or "",
                "input_schema": tool.inputSchema if hasattr(tool, 'inputSchema') else {}
            }
            for tool in tools
        ]

    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """调用 MCP 工具"""
        if not self.client:
            raise RuntimeError("Client not connected. Use 'async with client:' context manager.")

        try:
            result = await self.client.call_tool(tool_name, arguments)
        except Exception as e:
            print(f"[MCPClient] 工具 '{tool_name}' 调用异常: {type(e).__name__}: {e}")
            raise

        if hasattr(result, 'isError') and result.isError:
            error_text = ""
            if hasattr(result, 'content') and result.content:
                error_text = " | ".join(getattr(c, 'text', str(c)) for c in result.content)
            print(f"[MCPClient] 工具 '{tool_name}' 返回错误: {error_text}")
            return f"[MCP错误] {error_text}"

        # 解析结果 - FastMCP 返回 ToolResult 对象
        if hasattr(result, 'content') and result.content:
            if len(result.content) == 1:
                content = result.content[0]
                if hasattr(content, 'text'):
                    return content.text
                elif hasattr(content, 'data'):
                    return content.data
            return [
                getattr(c, 'text', getattr(c, 'data', str(c)))
                for c in result.content
            ]
        return None

    async def list_resources(self) -> List[Dict[str, Any]]:
        """列出所有可用的资源"""
        if not self.client:
            raise RuntimeError("Client not connected. Use 'async with client:' context manager.")

        result = await self.client.list_resources()

        if hasattr(result, 'resources'):
            resources = result.resources
        elif isinstance(result, list):
            resources = result
        else:
            resources = []

        return [
            {
                "uri": str(resource.uri),
                "name": getattr(resource, 'name', '') or "",
                "description": getattr(resource, 'description', '') or "",
                "mime_type": getattr(resource, 'mimeType', None)
            }
            for resource in resources
        ]

    async def read_resource(self, uri: str) -> Any:
        """读取资源内容"""
        if not self.client:
            raise RuntimeError("Client not connected. Use 'async with client:' context manager.")

        result = await self.client.read_resource(uri)

        # 解析资源内容
        if hasattr(result, 'contents') and result.contents:
            if len(result.contents) == 1:
                content = result.contents[0]
                if hasattr(content, 'text'):
                    return content.text
                elif hasattr(content, 'blob'):
                    return content.blob
            return [
                getattr(c, 'text', getattr(c, 'blob', str(c)))
                for c in result.contents
            ]
        return None

    async def list_prompts(self) -> List[Dict[str, Any]]:
        """列出所有可用的提示词模板"""
        if not self.client:
            raise RuntimeError("Client not connected. Use 'async with client:' context manager.")

        result = await self.client.list_prompts()

        if hasattr(result, 'prompts'):
            prompts = result.prompts
        elif isinstance(result, list):
            prompts = result
        else:
            prompts = []

        return [
            {
                "name": prompt.name,
                "description": getattr(prompt, 'description', '') or "",
                "arguments": getattr(prompt, 'arguments', [])
            }
            for prompt in prompts
        ]

    async def get_prompt(self, prompt_name: str, arguments: Optional[Dict[str, str]] = None) -> List[Dict[str, Any]]:
        """获取提示词内容"""
        if not self.client:
            raise RuntimeError("Client not connected. Use 'async with client:' context manager.")

        result = await self.client.get_prompt(prompt_name, arguments or {})

        # 解析提示词消息
        if hasattr(result, 'messages') and result.messages:
            return [
                {
                    "role": msg.role,
                    "content": getattr(msg.content, 'text', str(msg.content)) if hasattr(msg.content, 'text') else str(msg.content)
                }
                for msg in result.messages
            ]
        return []

    async def ping(self) -> bool:
        """测试服务器连接"""
        if not self.client:
            raise RuntimeError("Client not connected. Use 'async with client:' context manager.")
        
        try:
            await self.client.ping()
            return True
        except Exception:
            return False

    def get_transport_info(self) -> Dict[str, Any]:
        """获取传输信息"""
        if not self.client:
            return {"status": "not_connected"}
        
        transport = getattr(self.client, 'transport', None)
        if transport:
            return {
                "status": "connected",
                "transport_type": type(transport).__name__,
                "transport_info": str(transport)
            }
        return {"status": "unknown"}
