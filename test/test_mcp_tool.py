import os
import sys

CURRENT_DIR = os.path.dirname(__file__)
PROJECT_ROOT = os.path.dirname(CURRENT_DIR)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from dotenv import load_dotenv

load_dotenv()

from core import LingyeLLM
from agents import SimpleAgent
from tools import MCPTool

# 连接 GitHub MCP 服务器
# 需要在 .env 中配置: GITHUB_PERSONAL_ACCESS_TOKEN=<your_token>
github_tool = MCPTool(
    name="github",
    description="通过 MCP 协议访问 GitHub，支持搜索仓库、查看 Issue、读取文件等操作",
    server_command=["npx", "-y", "@modelcontextprotocol/server-github"],
)

agent = SimpleAgent(name="GitHub 助手", llm=LingyeLLM())
agent.add_tool(github_tool)

# 测试：搜索 GitHub 上与 MCP 相关的热门仓库
response = agent.run(
    "帮我在 GitHub 上搜索与 'create_pull_request' 相关的热门仓库，列出前5个并简单介绍"
)
print(response)
