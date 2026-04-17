# Lingye_Agent

> 一个面向研究与产品的**模块化 LLM Agent 框架**：多范式 Agent + 多类型记忆 + RAG + MCP 协议 + GSSC 上下文工程。

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Status](https://img.shields.io/badge/Status-Alpha-orange.svg)]()

---

## 目录

- [项目简介](#项目简介)
- [核心特性](#核心特性)
- [架构总览](#架构总览)
- [快速开始](#快速开始)
- [模块说明](#模块说明)
- [使用示例](#使用示例)
- [示例应用 (`app/`)](#示例应用-app)
- [配置与环境变量](#配置与环境变量)
- [扩展指南](#扩展指南)
- [项目结构](#项目结构)
- [Roadmap](#roadmap)
- [License](#license)

---

## 项目简介

**Lingye_Agent** 是一个用 Python 编写的 Agent 框架，把构建一个能"思考、记忆、调用工具、长期演进"的智能体所需的全部基础设施做了清晰拆分：

- **核心层 (`core/`)**：LLM 抽象、Agent 基类、流式事件、生命周期钩子。
- **Agent 层 (`agents/`)**：内置 6 种主流 Agent 范式（Simple / FunctionCall / ReAct / Plan-Solve / Reflection / ContextAware）。
- **工具层 (`tools/`)**：可插拔工具体系 + `@tool_action` 自动展开 + MCP 协议接入。
- **记忆层 (`memory/`)**：4 类记忆（工作 / 情景 / 语义 / 感知）+ Qdrant 向量库 + Neo4j 图库 + 多源 embedding。
- **上下文层 (`context/`)**：GSSC（Gather-Select-Structure-Compress）流水线，按 token 预算智能裁剪上下文。
- **协议层 (`protocols/`)**：MCP 客户端，支持 stdio / HTTP / SSE / 内存四种传输。
- **应用层 (`app/`)**：5 个端到端示例（PDF 学习助手、代码库维护、文档生成、Tavily 搜索…）。

> 设计目标：**每一层都能单独使用，也能组合出复杂的长程智能体。**

---

## 核心特性

### 多 Provider LLM 统一接口
内置自动检测：`openai / aihubmix / deepseek / qwen / modelscope / kimi / zhipu / ollama / vllm / local`，写一遍代码切换 provider 只改 `.env`。

### 6 种 Agent 范式开箱即用
| Agent | 适用场景 |
|---|---|
| `SimpleAgent` | 基础对话 + 文本式工具调用 |
| `FunctionCallAgent` | OpenAI 原生 function calling，最稳定 |
| `ReActAgent` | 推理-行动循环，适合需要外部信息的任务 |
| `PlanAndSolveAgent` | 先规划后执行，适合多步骤推理 |
| `ReflectionAgent` | 自我反思迭代优化，适合代码 / 文档生成 |
| `ContextAwareAgent` | 自动从记忆和 RAG 构建上下文 |

### 4 类认知记忆系统
- **WorkingMemory** — 短期工作记忆，TTL + 容量上限
- **EpisodicMemory** — 情景记忆，带时间索引
- **SemanticMemory** — 语义/知识记忆，向量检索
- **PerceptualMemory** — 多模态感知记忆（文本 / 图像 / 音频）

支持**记忆遗忘策略**（基于重要性 / 时间 / 容量）和**记忆整合**（短期 → 长期）。

### 完整的 RAG 管线
- 多格式入库：PDF / Word / Excel / PPT / 图片 / 音频 / 网页（基于 MarkItDown）
- 多源 embedding：本地 sentence-transformers / 阿里云 DashScope / TF-IDF 兜底
- 高级检索：MQE（多查询扩展）+ HyDE（假设性文档）+ Cross-Encoder 重排
- 多租户：通过 `rag_namespace` 隔离不同知识库

### MCP 协议原生支持
- 一行代码接入任何 MCP 服务器：`MCPTool.from_config("tavily")`
- 自动展开 MCP 子工具为独立 Tool，与 function calling 完美对接
- 内置演示服务器，无需任何外部依赖即可测试

### GSSC 上下文工程
`ContextBuilder` 自动从历史 / 记忆 / RAG / 工具结果四源收集 → 按相关性+新近性打分筛选 → 结构化模板组织 → token 预算内压缩。中文 jieba 分词友好。

### 流式输出 + 生命周期钩子
统一的 `StreamEvent` / `LifecycleHook` 体系，方便对接 SSE / WebSocket 前端。

---

## 架构总览

```
┌────────────────────────────────────────────────────────────────────┐
│                       app/  (业务应用层)                           │
│   PDF助手 │ 代码库维护 │ 项目助手 │ 文档生成 │ Tavily搜索        │
└──────────────┬─────────────────────────────────────────────────────┘
               │
┌──────────────▼─────────────────────────────────────────────────────┐
│                     agents/  (Agent 范式)                          │
│  SimpleAgent  FunctionCallAgent  ReActAgent  PlanAndSolveAgent     │
│  ReflectionAgent          ContextAwareAgent                        │
└──┬───────────────┬───────────────┬───────────────┬─────────────────┘
   │               │               │               │
┌──▼────────┐ ┌────▼──────┐ ┌──────▼────────┐ ┌────▼──────────────┐
│ context/  │ │  tools/   │ │   memory/     │ │   protocols/      │
│ GSSC 流水线│ │ Tool/MCP/ │ │ 4类记忆+RAG   │ │  MCP Client       │
│            │ │ Registry  │ │ Qdrant/Neo4j  │ │  (stdio/http/sse) │
└──┬─────────┘ └────┬──────┘ └───────┬───────┘ └────┬──────────────┘
   │                │                │              │
   └────────────────┴────────┬───────┴──────────────┘
                             │
              ┌──────────────▼──────────────┐
              │         core/ (基础)        │
              │ Agent  LingyeLLM  Message   │
              │ StreamEvent  LifecycleHook  │
              └─────────────────────────────┘
```

---

## 快速开始

### 1. 安装

```bash
git clone <your-repo-url> Lingye_Agent
cd Lingye_Agent

python -m venv .venv
# Windows:
.venv\Scripts\activate
# Linux/Mac:
source .venv/bin/activate

pip install -r requirements.txt
```

### 2. 配置环境变量

```bash
cp .env.example .env
# 至少配置一个 LLM provider 的 API Key
# 例如：LLM_API_KEY=sk-xxx 与 LLM_BASE_URL=https://aihubmix.com/v1
```

详见 [.env.example](.env.example)。

### 3. Hello, Agent！

```python
from dotenv import load_dotenv
from core import LingyeLLM
from agents import SimpleAgent

load_dotenv()

agent = SimpleAgent(
    name="助手",
    llm=LingyeLLM(),
    system_prompt="你是一个有帮助的 AI 助手。"
)

response = agent.run("用一句话解释什么是 RAG")
print(response)
```

### 4. 加上工具调用

```python
from core import LingyeLLM
from agents import FunctionCallAgent
from tools import ToolRegistry, simple_calculate

registry = ToolRegistry()
registry.register_function(
    name="calculator",
    description="数学计算工具，支持 +、-、*、/、sqrt",
    func=simple_calculate
)

agent = FunctionCallAgent(
    name="计算助手",
    llm=LingyeLLM(),
    tool_registry=registry,
)

print(agent.run("计算 sqrt(144) + 12 * 8 等于多少"))
```

### 5. 加上记忆与 RAG

```python
from agents import ContextAwareAgent
from core import LingyeLLM

agent = ContextAwareAgent(
    name="知识助手",
    llm=LingyeLLM(),
    user_id="alice",
    knowledge_base_path="./my_kb",
    system_prompt="你会自动查询知识库和过往记忆。"
)

print(agent.run("我之前问过的关于 RAG 的问题，整理一下要点"))
```

---

## 模块说明

### `core/` — 框架基础

| 文件 | 作用 |
|---|---|
| `agent.py` | `Agent` 抽象基类：`run()` / `add_message()` / `clear_history()` |
| `llm.py` | `LingyeLLM`：多 provider 自动检测、统一 `invoke / stream_invoke / think` |
| `message.py` | `Message`：role / content / timestamp / metadata |
| `config.py` | `Config`：全局配置（temperature、max_tokens 等），支持 `from_env()` |
| `streaming.py` | `StreamEvent` / `StreamEventType` / `StreamBuffer` + SSE/JSONLines 转换 |
| `lifecycle.py` | `EventType` / `AgentEvent` / `ExecutionContext` / `LifecycleHook` |
| `database_config.py` | Qdrant / Neo4j 配置统一管理（`from_env()` + 健康检查） |
| `exceptions.py` | `LingyeAgentsException` 异常体系 |

### `agents/` — Agent 范式实现

每个 Agent 都继承 `core.Agent`，支持：
- 历史管理：`add_message` / `clear_history`
- 工具调用：通过 `tool_registry` 参数注入
- 流式输出：`stream_run()` / `arun_stream()`（部分 Agent）

具体范式特点见 [核心特性](#6-种-agent-范式开箱即用)。

### `tools/` — 工具体系

```python
# 三种注册方式：
# ① Tool 子类（推荐）
class MyTool(Tool):
    def run(self, parameters): ...
    def get_parameters(self): ...

# ② 函数式注册（最简）
registry.register_function("my_tool", "描述", my_func)

# ③ @tool_action 装饰器自动展开
class MyTool(Tool):
    @tool_action("my_action", "描述")
    def my_action(self, x: int, y: str = "default") -> str:
        """方法 docstring 即工具描述
        Args:
            x: 参数 X 的描述
            y: 参数 Y 的描述
        """
        ...
# 注册时会自动从签名 + docstring 生成 ToolParameter
```

内置工具：

| 工具 | 用途 |
|---|---|
| `simple_calculate` | 安全的算术表达式求值 |
| `TerminalTool` | 沙箱化命令行（白名单 + 工作目录限制 + 超时） |
| `NoteTool` | 结构化笔记（Markdown + YAML front-matter） |
| `MemoryTool` | 接入 `MemoryManager` 的 8 种记忆操作 |
| `RAGTool` | 完整 RAG（add/search/ask/管理知识库） |
| `MCPTool` | 接入任意 MCP 服务器，自动展开子工具 |
| `AdvancedSearchTool` | Tavily / SerpApi 多源搜索 |
| `ToolChain` | 多工具顺序编排 |
| `AsyncToolExecutor` | 工具并行执行 |

### `memory/` — 认知记忆系统

```
MemoryManager
├── WorkingMemory   (短期：TTL + 容量)
├── EpisodicMemory  (情景：时间索引)
├── SemanticMemory  (语义：向量检索)
└── PerceptualMemory(感知：CLIP/CLAP 多模态)

存储后端：
├── QdrantVectorStore  (向量)
├── Neo4jGraphStore    (图)
└── SQLiteDocumentStore(原文)

Embedding 三级回退：
DashScope (云端) → sentence-transformers (本地) → TF-IDF (兜底)
```

### `context/` — GSSC 上下文工程

```python
from context import ContextBuilder, ContextConfig

builder = ContextBuilder(
    memory_tool=memory_tool,
    rag_tool=rag_tool,
    config=ContextConfig(max_tokens=8000, reserve_ratio=0.15)
)

context = builder.build(
    user_query="用户问题",
    conversation_history=[...],
    system_instructions="系统指令"
)
# → 自动收集 → 打分 → 结构化 → 压缩，输出最优 prompt
```

输出模板：`[Role & Policies] / [Task] / [State] / [Evidence] / [Context] / [Output]`

### `protocols/` — MCP 客户端

```python
from protocols.mcp import MCPClient

# 1. 内存（FastMCP 实例，测试用）
async with MCPClient(server) as c: ...

# 2. stdio（本地脚本/命令）
async with MCPClient("server.py") as c: ...
async with MCPClient(["npx", "-y", "@mcp/foo"]) as c: ...

# 3. HTTP / SSE（远程）
async with MCPClient("https://api.example.com/mcp") as c: ...
async with MCPClient(url, transport_type="sse") as c: ...
```

通过 `config/mcp_servers.json` 集中管理常用 MCP 服务器（Tavily / Perplexity / Obsidian / GitHub / Filesystem）。

---

## 使用示例

### ReAct Agent + 工具

```python
from core import LingyeLLM
from agents import ReActAgent
from tools import ToolRegistry, simple_calculate

registry = ToolRegistry()
registry.register_function("calculator", "计算器", simple_calculate)

agent = ReActAgent(
    name="ReAct助手",
    llm=LingyeLLM(),
    tool_registry=registry,
    max_steps=5
)

print(agent.run("一个圆的半径是 7.5，它的面积是多少？"))
```

### Plan-and-Solve Agent

```python
from agents import PlanAndSolveAgent
from core import LingyeLLM

agent = PlanAndSolveAgent(name="规划助手", llm=LingyeLLM())
print(agent.run("帮我把 '人工智能在医疗中的应用' 这个题目拆成 5 个子主题并各写一段"))
```

### 接入 MCP 服务器（Tavily 搜索）

```python
# .env 中配置 TAVILY_API_KEY
from agents import SimpleAgent
from core import LingyeLLM
from tools import MCPTool

agent = SimpleAgent(name="搜索助手", llm=LingyeLLM())
agent.add_tool(MCPTool.from_config("tavily"))

print(agent.run("帮我搜索 Anthropic 最新发布的论文"))
```

### 流式输出（异步）

```python
import asyncio
from agents import ReflectionAgent
from core import LingyeLLM

agent = ReflectionAgent(name="反思助手", llm=LingyeLLM(), max_iterations=2)

async def main():
    async for event in agent.arun_stream("写一段 Python 快排"):
        print(f"[{event.type.value}]", event.data.get("chunk", ""), end="")

asyncio.run(main())
```

---

## 示例应用 (`app/`)

| 应用 | 说明 | 入口 |
|---|---|---|
| **PDF 学习助手** | Gradio Web UI，加载 PDF + RAG 问答 + 学习记忆回顾 | `app/PDF_learning_assistant.py` |
| **代码库维护助手** | FunctionCall + Terminal + Note + Memory 长程探索代码库 | `app/codebase_maintainer.py` |
| **项目助手** | NoteTool + ContextBuilder 的长期项目管家 | `app/project_assistant.py` |
| **多 Agent 文档生成** | GitHub 搜索 Agent + 文档撰写 Agent 协作 | `app/doc_assistant.py` |
| **Tavily 搜索助手** | MCP 接入 Tavily 的极简示例 | `app/tavily_search.py` |

运行示例：

```bash
python app/PDF_learning_assistant.py
python app/codebase_maintainer.py
```

---

## 配置与环境变量

完整模板见 [`.env.example`](.env.example)，关键项：

```ini
# ① LLM（至少配一组）
LLM_API_KEY=sk-xxx
LLM_BASE_URL=https://aihubmix.com/v1
LLM_MODEL_ID=coding-glm-5-free

# ② 向量库（RAG / 语义记忆需要）
QDRANT_URL=http://localhost:6333
QDRANT_API_KEY=

# ③ 图库（可选，关系推理用）
NEO4J_URI=neo4j+s://xxx.databases.neo4j.io
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=xxx

# ④ Embedding（local 完全离线 / dashscope 云端）
EMBED_MODEL_TYPE=local
EMBED_MODEL_NAME=E:/models/all-MiniLM-L6-v2
EMBED_OFFLINE=1

# ⑤ MCP 服务器凭证
TAVILY_API_KEY=
GITHUB_PERSONAL_ACCESS_TOKEN=
```

### 离线本地部署小贴士

1. **本地 Embedding**：先把 `sentence-transformers/all-MiniLM-L6-v2` 下载到本地路径，配置 `EMBED_MODEL_NAME` 为绝对路径，并设 `EMBED_OFFLINE=1`。
2. **本地 LLM**：用 Ollama / vLLM，配置 `OLLAMA_HOST` 或 `VLLM_HOST`。
3. **本地 Qdrant**：`docker run -p 6333:6333 qdrant/qdrant`。

---

## 扩展指南

### 自定义一个 Tool

```python
from tools import Tool, ToolParameter
from typing import Dict, Any, List

class WeatherTool(Tool):
    def __init__(self):
        super().__init__(name="weather", description="查询城市天气")

    def get_parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(name="city", type="string", description="城市名", required=True)
        ]

    def run(self, parameters: Dict[str, Any]) -> str:
        city = parameters["city"]
        # ... 调用真实 API
        return f"{city} 今天晴 25°C"
```

### 自定义一个 Agent 范式

```python
from core import Agent, Message

class MyAgent(Agent):
    def run(self, input_text: str, **kwargs) -> str:
        # 1. 构建 messages
        messages = [{"role": "system", "content": self.system_prompt}]
        for m in self._history:
            messages.append({"role": m.role, "content": m.content})
        messages.append({"role": "user", "content": input_text})

        # 2. 调用 LLM
        response = self.llm.invoke(messages)

        # 3. 维护历史
        self.add_message(Message(input_text, "user"))
        self.add_message(Message(response, "assistant"))
        return response
```

### 扩展记忆类型

继承 `memory.BaseMemory`，实现 `add / retrieve / update / remove / has_memory / clear / get_stats` 七个抽象方法即可。

---

## 项目结构

```
Lingye_Agent/
├── core/                        # 框架基础
│   ├── agent.py                 # Agent 抽象基类
│   ├── llm.py                   # 多 provider LLM 客户端
│   ├── message.py               # 消息数据结构
│   ├── config.py                # 全局配置
│   ├── streaming.py             # 流式事件
│   ├── lifecycle.py             # 生命周期钩子
│   ├── memory.py                # 简单的轨迹记忆
│   ├── database_config.py       # 数据库配置
│   └── exceptions.py            # 异常体系
│
├── agents/                      # Agent 范式
│   ├── simple_agent.py
│   ├── function_call_agent.py
│   ├── react_agent.py
│   ├── plan_solve_agent.py
│   ├── reflection_agent.py
│   └── context_aware_agent.py
│
├── tools/                       # 工具体系
│   ├── base.py                  # Tool / ToolParameter / @tool_action
│   ├── registry.py              # ToolRegistry
│   ├── simple_calculate.py
│   ├── terminal_tool.py
│   ├── note_tool.py
│   ├── memory_tool.py
│   ├── rag_tool.py
│   ├── advanced_search.py
│   ├── chain.py                 # ToolChain
│   ├── async_executor.py
│   └── protocol/
│       └── mcp_tool.py          # MCPTool
│
├── memory/                      # 记忆系统
│   ├── base.py                  # BaseMemory / MemoryItem / MemoryConfig
│   ├── manager.py               # MemoryManager 统一接口
│   ├── embedding.py             # 多源 embedding
│   ├── types/                   # 4 类记忆实现
│   │   ├── working.py
│   │   ├── episodic.py
│   │   ├── semantic.py
│   │   └── perceptual.py
│   ├── storage/                 # 存储后端
│   │   ├── qdrant_store.py
│   │   ├── neo4j_store.py
│   │   └── document_store.py
│   └── rag/
│       ├── document.py
│       └── pipeline.py          # RAG 管线
│
├── context/                     # 上下文工程
│   └── builder.py               # GSSC 流水线
│
├── protocols/                   # 协议层
│   └── mcp/
│       └── client.py            # MCP 客户端
│
├── app/                         # 示例应用
│   ├── PDF_learning_assistant.py
│   ├── codebase_maintainer.py
│   ├── project_assistant.py
│   ├── doc_assistant.py
│   └── tavily_search.py
│
├── test/                        # 测试用例
├── config/
│   └── mcp_servers.json         # MCP 服务器集中配置
├── memory_data/                 # 记忆持久化目录
├── .env.example                 # 环境变量模板
├── requirements.txt
└── README.md
```

---

## Roadmap

### 已完成
- [x] 多 provider LLM 统一接口
- [x] 6 种 Agent 范式
- [x] 4 类记忆 + Qdrant / Neo4j 后端
- [x] 完整 RAG 管线（含 MQE / HyDE / Reranker）
- [x] MCP 协议（stdio / HTTP / SSE / 内存）
- [x] GSSC 上下文工程

### 进行中 / 计划中
- [ ] **服务化层**：FastAPI + WebSocket/SSE 对外接口
- [ ] **前端 UI**：完整的 Chat + Agent 配置 + 记忆/知识库管理界面
- [ ] **持久化对话**：用户 / 会话 / 消息持久化（SQLAlchemy）
- [ ] **可观测性**：结构化日志 + token 计费 + tracing
- [ ] **多 Agent 编排**：Workflow / Graph 引擎
- [ ] **缓存层**：LLM 响应 + Embedding 缓存（Redis）
- [ ] **Guardrails**：输入审核 + 输出 schema 校验
- [ ] **Code Interpreter / Browser** 等更多沙箱工具
- [ ] **评估框架**：任务完成率 / 忠实度 / 回归测试
- [ ] **Docker / K8s** 一键部署

详见 `todo.md`。

---

## License

[MIT License](LICENSE) © Lingye_Agent Contributors
