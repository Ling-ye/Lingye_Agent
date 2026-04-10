"""MCP Tool - 基于 fastmcp 连接和调用 MCP 服务器"""

from typing import Dict, Any, List, Optional
import asyncio
import concurrent.futures
from ..base import Tool, ToolParameter
from dotenv import load_dotenv

load_dotenv()


class MCPTool(Tool):
    """MCP (Model Context Protocol) 工具

    连接到 MCP 服务器并调用其工具、资源和提示词。
    环境变量统一从 .env 文件加载。

    使用示例:
        # 连接外部服务器（所需密钥写入 .env）
        tool = MCPTool(server_command=["npx", "-y", "@modelcontextprotocol/server-github"])

        # 使用内置演示服务器
        tool = MCPTool()

        # 使用 FastMCP 实例（内存传输）
        from fastmcp import FastMCP
        server = FastMCP("MyServer")
        tool = MCPTool(server=server)
    """

    def __init__(
        self,
        name: str = "mcp",
        description: Optional[str] = None,
        server_command: Optional[List[str]] = None,
        server_args: Optional[List[str]] = None,
        server: Optional[Any] = None,
        auto_expand: bool = True,
    ):
        """
        Args:
            name: 工具名称
            description: 工具描述（默认自动生成）
            server_command: 服务器启动命令，如 ["npx", "-y", "@modelcontextprotocol/server-github"]
            server_args: 附加服务器参数
            server: FastMCP 实例（用于内存传输）
        """
        self.server_command = server_command
        self.server_args = server_args or []
        self.server = server
        self.auto_expand = auto_expand

        if not server_command and not server:
            self.server = self._create_builtin_server()

        self._available_tools = self._discover_tools()

        if description is None:
            count = len(self._available_tools)
            description = (
                f"MCP工具服务器，提供 {count} 个工具。" if count else "MCP工具服务器。"
            )

        super().__init__(name=name, description=description, expandable=auto_expand)

    def _create_builtin_server(self):
        """创建内置演示服务器"""
        try:
            from fastmcp import FastMCP
        except ImportError:
            raise ImportError("需要 fastmcp 库，请运行: pip install fastmcp")

        server = FastMCP("BuiltinServer")

        @server.tool()
        def add(a: float, b: float) -> float:
            """加法"""
            return a + b

        @server.tool()
        def subtract(a: float, b: float) -> float:
            """减法"""
            return a - b

        @server.tool()
        def multiply(a: float, b: float) -> float:
            """乘法"""
            return a * b

        @server.tool()
        def divide(a: float, b: float) -> float:
            """除法"""
            if b == 0:
                raise ValueError("除数不能为零")
            return a / b

        @server.tool()
        def greet(name: str = "World") -> str:
            """问候"""
            return f"Hello, {name}!当这只是一个测试服务器"

        return server

    def _discover_tools(self) -> List[Dict[str, Any]]:
        """发现 MCP 服务器提供的工具列表"""
        try:
            tools = self._run_async(self._async_list_tools())
            if tools:
                print(
                    f"[MCPTool] 发现 {len(tools)} 个工具: {[t['name'] for t in tools]}"
                )
            else:
                print("[MCPTool] 警告: 服务器未返回任何工具")
            return tools
        except Exception as e:
            print(f"[MCPTool] 发现工具失败: {type(e).__name__}: {e}")
            return []

    async def _async_list_tools(self) -> List[Dict[str, Any]]:
        from protocols.mcp.client import MCPClient

        source = self.server if self.server else self.server_command
        async with MCPClient(source, self.server_args) as client:
            return await client.list_tools()

    def _run_async(self, coro):
        """在任意上下文中安全运行协程"""
        try:
            asyncio.get_running_loop()

            # 已有事件循环，在新线程中运行
            def _run():
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    return loop.run_until_complete(coro)
                finally:
                    loop.close()

            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                return executor.submit(_run).result()
        except RuntimeError:
            return asyncio.run(coro)

    def run(self, parameters: Dict[str, Any]) -> str:
        """
        执行 MCP 操作

        Args:
            parameters:
                action: list_tools | call_tool | list_resources | read_resource | list_prompts | get_prompt
                tool_name: 工具名称（call_tool 需要）
                arguments: 工具参数（call_tool 需要）
                uri: 资源 URI（read_resource 需要）
                prompt_name: 提示词名称（get_prompt 需要）
                prompt_arguments: 提示词参数（get_prompt 可选）
        """
        action = parameters.get("action", "").lower()
        if not action and "tool_name" in parameters:
            action = "call_tool"
        if not action:
            return "错误：必须指定 action 或 tool_name 参数"

        try:
            return self._run_async(self._async_run(action, parameters))
        except Exception as e:
            error_msg = f"MCP 操作失败 (action={action}): {type(e).__name__}: {e}"
            print(f"[MCPTool] {error_msg}")
            return error_msg

    async def _async_run(self, action: str, parameters: Dict[str, Any]) -> str:
        from protocols.mcp.client import MCPClient

        source = self.server if self.server else self.server_command
        async with MCPClient(source, self.server_args) as client:
            if action == "list_tools":
                tools = await client.list_tools()
                if not tools:
                    return "没有可用工具"
                lines = [f"找到 {len(tools)} 个工具:"]
                for t in tools:
                    lines.append(f"  - {t['name']}: {t['description']}")
                return "\n".join(lines)

            elif action == "call_tool":
                tool_name = parameters.get("tool_name")
                if not tool_name:
                    return "错误：缺少 tool_name 参数"
                result = await client.call_tool(
                    tool_name, parameters.get("arguments", {})
                )
                return f"工具 '{tool_name}' 执行结果:\n{result}"

            elif action == "list_resources":
                resources = await client.list_resources()
                if not resources:
                    return "没有可用资源"
                lines = [f"找到 {len(resources)} 个资源:"]
                for r in resources:
                    lines.append(f"  - {r['uri']}: {r['name']}")
                return "\n".join(lines)

            elif action == "read_resource":
                uri = parameters.get("uri")
                if not uri:
                    return "错误：缺少 uri 参数"
                content = await client.read_resource(uri)
                return f"资源 '{uri}' 内容:\n{content}"

            elif action == "list_prompts":
                prompts = await client.list_prompts()
                if not prompts:
                    return "没有可用提示词"
                lines = [f"找到 {len(prompts)} 个提示词:"]
                for p in prompts:
                    lines.append(f"  - {p['name']}: {p['description']}")
                return "\n".join(lines)

            elif action == "get_prompt":
                prompt_name = parameters.get("prompt_name")
                if not prompt_name:
                    return "错误：缺少 prompt_name 参数"
                messages = await client.get_prompt(
                    prompt_name, parameters.get("prompt_arguments", {})
                )
                lines = [f"提示词 '{prompt_name}':"]
                for msg in messages:
                    lines.append(f"  [{msg['role']}] {msg['content']}")
                return "\n".join(lines)

            else:
                return f"错误：不支持的操作 '{action}'"

    def get_parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="action",
                type="string",
                description="操作类型: list_tools | call_tool | list_resources | read_resource | list_prompts | get_prompt",
                required=True,
            ),
            ToolParameter(
                name="tool_name",
                type="string",
                description="工具名称（call_tool 需要）",
                required=False,
            ),
            ToolParameter(
                name="arguments",
                type="object",
                description="工具参数（call_tool 需要）",
                required=False,
            ),
            ToolParameter(
                name="uri",
                type="string",
                description="资源 URI（read_resource 需要）",
                required=False,
            ),
            ToolParameter(
                name="prompt_name",
                type="string",
                description="提示词名称（get_prompt 需要）",
                required=False,
            ),
            ToolParameter(
                name="prompt_arguments",
                type="object",
                description="提示词参数（get_prompt 可选）",
                required=False,
            ),
        ]
