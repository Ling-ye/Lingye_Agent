"""
Stdio 传输测试用 MCP 服务器

通过标准输入输出运行，供 test_mcp_tool.py 的 Stdio/Python 脚本测试使用。
启动方式: python test/_mcp_stdio_server.py
"""

from datetime import datetime
from fastmcp import FastMCP

server = FastMCP("StdioTestServer")


@server.tool()
def echo(message: str) -> str:
    """原样回显消息"""
    return message


@server.tool()
def get_time() -> str:
    """返回服务器当前时间"""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


@server.tool()
def reverse(text: str) -> str:
    """反转字符串"""
    return text[::-1]


@server.tool()
def word_count(text: str) -> int:
    """统计文本中的单词数"""
    return len(text.split())


if __name__ == "__main__":
    server.run(transport="stdio")
