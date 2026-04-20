"""MCPServer 简单示例。"""

from lingye_agent.protocols.mcp import MCPServer


def create_example_server() -> MCPServer:
    """创建一个示例 MCP 服务器"""
    server = MCPServer(
        name="example-server",
        description="A simple example MCP server with calculator and greeting tools",
    )

    def calculator(expression: str) -> str:
        """计算数学表达式

        Args:
            expression: 要计算的数学表达式，例如 "2 + 2" 或 "10 * 5"
        """
        try:
            # 安全的表达式求值（仅支持基本运算）
            allowed_chars = set("0123456789+-*/() .")
            if not all(c in allowed_chars for c in expression):
                return "Error: Invalid characters in expression"
            result = eval(expression)
            return f"Result: {result}"
        except Exception as e:
            return f"Error: {str(e)}"

    def greet(name: str) -> str:
        """生成友好的问候语

        Args:
            name: 要问候的人的名字
        """
        return f"Hello, {name}! Welcome to the MCP server example."

    server.add_tool(calculator, name="calculator", description="Calculate a mathematical expression")
    server.add_tool(greet, name="greet", description="Generate a friendly greeting")

    return server


if __name__ == "__main__":
    server = create_example_server()
    print(f"Starting {server.name}...")
    print(f"{server.description}")
    print("Protocol: MCP")
    print("Transport: stdio")
    print()
    server.run()
