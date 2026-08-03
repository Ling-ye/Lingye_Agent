# Lingye Agent 使用指南

[返回中文首页](../README.md) | [English guide](guide.en.md)

## 1. 环境与安装

Lingye Agent 需要 Python 3.10–3.13。核心安装只包含 Agent、LLM 抽象、上下文、基础记忆和基础工具；数据库、文档解析、MCP 与 UI 通过 extras 安装。

~~~bash
python -m venv .venv
# Windows PowerShell
.venv\Scripts\Activate.ps1
# Linux / macOS
source .venv/bin/activate

python -m pip install -e ".[dev]"
~~~

需要完整本地开发环境时：

~~~bash
python -m pip install -e ".[rag,graph,mcp,nlp,doc,ui,dev]"
~~~

复制 .env.example 为 .env。不要提交 .env、数据库、索引、模型权重或真实凭据。

## 2. LLM 配置

LingyeLLM 使用 OpenAI-compatible 请求格式。常用配置：

| 变量 | 用途 |
|---|---|
| LLM_API_KEY | 当前端点的 API Key |
| LLM_BASE_URL | OpenAI-compatible API 根地址 |
| LLM_MODEL_ID | 模型标识 |
| LLM_TIMEOUT | 请求超时秒数 |
| TEMPERATURE | 默认采样温度 |
| MAX_TOKENS | 默认最大输出 token |

Provider 专用变量可覆盖通用配置。使用 Ollama 或 vLLM 时，配置对应的 HOST 和模型标识。

## 3. Agent 范式

| Agent | 用途 |
|---|---|
| SimpleAgent | 基础对话和文本式工具调用 |
| FunctionCallAgent | 使用模型原生 tool/function calling |
| ReActAgent | 交替执行推理和工具动作 |
| PlanAndSolveAgent | 先生成计划，再逐步求解 |
| ReflectionAgent | 生成、评价并迭代答案 |
| ContextAwareAgent | 从记忆与 RAG 构建上下文 |

所有 Agent 继承核心 Agent 抽象，并通过 LingyeLLM、system_prompt、Config 和 ToolRegistry 组合行为。不同 Agent 的同步、异步和流式能力并不完全相同，使用前应检查对应类的方法。

## 4. 工具系统

ToolRegistry 支持 Tool 子类、函数注册和 tool_action 装饰器。

~~~python
from lingye_agent import ToolRegistry
from lingye_agent.tools import simple_calculate

registry = ToolRegistry()
registry.register_function(
    name="calculator",
    description="执行基础算术表达式",
    func=simple_calculate,
)

result = registry.execute_tool("calculator", "sqrt(16) + 2 * 3")
print(result)
~~~

内置模块包括 TerminalTool、NoteTool、MemoryTool、RAGTool、MCPTool、AdvancedSearchTool、ToolChain 和 AsyncToolExecutor。涉及命令执行、网络和外部服务的工具需要单独设置权限、凭据与超时。

## 5. 记忆与存储

MemoryManager 组织四类记忆：

- WorkingMemory：带容量与 TTL 的短期状态。
- EpisodicMemory：按时间和会话组织的事件。
- SemanticMemory：使用向量或图检索语义信息。
- PerceptualMemory：保存文本、图像或音频相关感知记录。

SQLite 文档存储会在运行时自动创建数据库目录。memory_data、knowledge_base 和 data_science_kb 属于本地运行数据，不应提交到 Git。

Qdrant 与 Neo4j 是可选后端；启用前需安装对应 extra，并确认向量维度、集合名、数据库名和网络配置一致。

## 6. RAG

RAG 相关能力位于 lingye_agent.memory.rag 与 RAGTool。典型流程是文档解析、切分、embedding、入库、检索和可选重排。

~~~python
from lingye_agent.tools import RAGTool

rag = RAGTool(
    name="knowledge",
    description="项目知识库",
    knowledge_base_path="./knowledge_base",
)
~~~

文档解析依赖 doc extra；本地 embedding 和重排依赖 rag extra。云端 embedding 需要对应服务凭据。离线模式下应将 EMBED_MODEL_NAME 指向已存在的本地模型目录，并启用 EMBED_OFFLINE。

## 7. MCP

安装 mcp extra 后，可使用 MCPTool 或底层 MCPClient。

~~~python
from lingye_agent.tools import MCPTool

tool = MCPTool.from_config("tavily")
~~~

服务器配置集中在 config/mcp_servers.json。客户端支持内存、stdio、HTTP 和 SSE 场景；具体可用性取决于 FastMCP 版本和服务端实现。不要把访问令牌写入 JSON 配置，使用环境变量引用。

## 8. 上下文与缓存

ContextBuilder 使用 GSSC 流程收集、筛选、组织并压缩对话、记忆、RAG 和工具结果。

~~~python
from lingye_agent.context import ContextBuilder, ContextConfig

builder = ContextBuilder(
    memory_tool=memory_tool,
    rag_tool=rag_tool,
    config=ContextConfig(max_tokens=8000, reserve_ratio=0.15),
)

context = builder.build(
    user_query="总结当前任务",
    conversation_history=[],
    system_instructions="只使用提供的证据",
)
~~~

optimize_for_cache 会稳定 system 前缀、工具 schema 顺序和易变标识，同时保留 user 内容与工具调用配对关系。

## 9. 流式事件与生命周期

core.streaming 提供 StreamEvent、StreamEventType 和序列化辅助；core.lifecycle 提供 AgentEvent、ExecutionContext 和 LifecycleHook。具体 Agent 只暴露其已实现的 stream_run 或 arun_stream 方法，不应假设所有 Agent 都支持同一种流式接口。

## 10. 示例

| 文件 | 场景 |
|---|---|
| examples/PDF_learning_assistant.py | PDF、RAG 与 Gradio |
| examples/codebase_maintainer.py | 工具与长期代码库任务 |
| examples/project_assistant.py | NoteTool 与上下文构建 |
| examples/doc_assistant.py | 多 Agent 文档生成 |
| examples/tavily_search.py | MCP 搜索 |

示例可能需要 all extra、外部数据库、MCP 服务或 API Key。先检查文件顶部导入和 .env.example，再运行对应入口。

## 11. 项目结构

~~~text
lingye_agent/
├── agents/       # Agent 范式
├── cache/        # 稳定前缀与工具 schema 优化
├── context/      # GSSC 上下文构建
├── core/         # Agent、LLM、消息、事件和配置
├── memory/       # 记忆类型、RAG 与存储
├── protocols/    # MCP 客户端和服务端
└── tools/        # 工具、注册表和执行器

examples/         # 可运行示例
tests/            # 单元与集成测试
config/           # 非敏感配置模板
~~~

## 12. 验证与限制

快速发布检查：

~~~bash
python -m pytest -q tests/test_release_contract.py tests/test_function_call_agent_unit.py tests/test_simple_calculator.py::test_calculator_tool
python -m build
python -m twine check dist/*
python scripts/verify_release_artifact.py dist/lingye_agent-0.1.0-py3-none-any.whl
~~~

完整测试套件包含外部服务和较慢初始化，目前不作为 v0.1.0 的阻断门槛。提交问题时请提供 Python 版本、操作系统、安装 extras、最小复现和完整错误栈，并删除所有密钥。
