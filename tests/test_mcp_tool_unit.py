from lingye_agent.tools import MCPTool


def test_mcp_tool_does_not_discover_on_init_by_default(monkeypatch):
    def fail_if_called(self):
        raise AssertionError("MCPTool should discover tools lazily by default")

    monkeypatch.setattr(MCPTool, "_discover_tools", fail_if_called)

    tool = MCPTool(server_command=["python", "server.py"], auto_expand=False)

    assert tool._available_tools == []


def test_mcp_tool_make_client_uses_package_relative_import():
    tool = MCPTool(
        server_command=["python", "tests/_mcp_stdio_server.py"],
        auto_expand=False,
    )

    client = tool._make_client()

    assert client.__class__.__module__ == "lingye_agent.protocols.mcp.client"


def test_mcp_tool_discovery_timeout():
    async def never_returns(self):
        import asyncio

        await asyncio.sleep(1)
        return []

    tool = MCPTool(
        server_command=["python", "server.py"],
        auto_expand=True,
        discovery_timeout=0.01,
    )
    tool._async_list_tools = never_returns.__get__(tool, MCPTool)

    discovered = tool._discover_tools()

    assert discovered == []
    assert tool._tools_discovered is True
