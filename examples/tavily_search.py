"""
Tavily AI 搜索助手

使用 MCPTool.from_config 快速接入 Tavily MCP 服务器，
Agent 接收用户查询后调用 Tavily 执行 AI 优化搜索并返回结构化结果。

前置条件：
    1. Node.js / npm 已安装
    2. 在 .env 中配置 TAVILY_API_KEY（从 https://tavily.com 获取）
"""

import os

from lingye_agent.core import LingyeLLM
from lingye_agent.agents import SimpleAgent
from lingye_agent.tools import MCPTool
from dotenv import load_dotenv

load_dotenv()

print("=" * 70)
print("Tavily AI 搜索助手")
print("=" * 70)

# ============================================================
# 创建 Tavily 搜索 Agent
# ============================================================
print("\n【步骤1】创建 Tavily 搜索 Agent...")

searcher = SimpleAgent(
    name="Tavily搜索专家",
    llm=LingyeLLM(),
    system_prompt="""你是一个 AI 搜索专家，使用 Tavily 搜索引擎获取最新信息。

你的工作流程：
1. 分析用户的查询意图
2. 使用 Tavily 搜索工具执行搜索
3. 整理搜索结果，返回结构化的摘要

输出格式要求：
- 搜索主题
- 关键发现（按重要性排序的要点列表）
- 信息来源

保持客观、准确，标注信息来源。""",
)

tavily_tool = MCPTool.from_config("tavily")
searcher.add_tool(tavily_tool)

# ============================================================
# 执行搜索任务
# ============================================================
print("\n" + "=" * 70)
print("开始执行搜索任务...")
print("=" * 70)

try:
    query = "2025年最值得关注的AI Agent框架有哪些？各自的特点是什么？"
    print(f"\n搜索查询: {query}")
    print("-" * 70)

    result = searcher.run(query)

    print("\n搜索结果:")
    print("=" * 70)
    print(result)
    print("=" * 70)

    print("\n任务完成！")

except Exception as e:
    print(f"\n错误: {e}")
    import traceback
    traceback.print_exc()
