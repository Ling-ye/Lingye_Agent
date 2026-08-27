# Lingye Agent 架构与接口指南

[返回中文首页](../README.md) | [English guide](guide.en.md)

## 1. 分层架构与设计原则

Lingye Agent 采用显式编排。每种 Agent 策略自己控制模型调用、工具循环和结束条件，共用的部分放在核心类型和组合对象里。顺着一个具体的 Agent 类，就能看完一次请求的控制流；工具、上下文和存储也可以单独替换。

| 层 | 主要入口 | 职责 | 设计思路 |
|---|---|---|---|
| 应用层 | `examples/`、用户代码 | 组合 Agent、工具和数据源，提供交互入口 | 业务流程留在应用侧，框架只提供可组合部件 |
| Agent 策略层 | `lingye_agent.agents` | 决定何时调用模型、工具以及何时结束 | 一种策略对应一个清晰执行循环 |
| 核心运行层 | `Agent`、`LingyeLLM`、`Message`、`Config` | 统一模型访问、消息格式、公共状态和配置 | 保持最小公共抽象，策略差异由子类表达 |
| 工具层 | `ToolRegistry`、`Tool` | 描述、注册并执行函数、结构化工具和 MCP 工具 | 模型负责选择和生成参数，Registry 负责实际执行 |
| 上下文层 | `ContextBuilder`、`optimize_for_cache` | 在 token 预算内组织信息并稳定请求前缀 | 上下文选择与 Agent 决策分离，可单独验证 |
| 知识与状态层 | `MemoryManager`、`RAGTool` | 管理短期状态、历史经验、语义索引和外部知识 | 记忆与 RAG 分工处理状态和资料检索 |
| 协议与存储层 | MCP、SQLite、Qdrant、Neo4j | 连接进程外工具和持久化基础设施 | 外部副作用与凭据由宿主环境控制 |

依赖方向从应用层指向策略和核心层；Agent 按需组合工具与上下文，上下文再读取 Memory 或 RAG。MCP、数据库和模型端点位于进程边界之外，通过适配器接入。

~~~text
Application
   └─ Agent strategy
      ├─ Agent + LingyeLLM + per-strategy prompt/state
      ├─ ToolRegistry ──> local Tool / function / MCP
      └─ ContextBuilder
         ├─ MemoryTool ──> in-memory / SQLite / Qdrant / Neo4j
         └─ RAGTool ──> Qdrant
~~~

## 2. 运行环境与依赖边界

包元数据要求 Python 3.10 或更高版本。GitHub Actions 在 `ubuntu-latest` 上使用 Python 3.10–3.13 验证基础 / 开发依赖的发布契约。创建虚拟环境、复制配置和运行第一个 Agent 的步骤，见 README 的[新手快速部署](../README.md#新手快速部署)。

| 安装方式 | 安装命令 | 适用场景 |
|---|---|---|
| 源码 editable 安装 | `python -m pip install -e .` | 运行 `examples/`、使用根 `config/`、调试或扩展源码 |
| Release wheel | `python -m pip install "https://github.com/Ling-ye/Lingye_Agent/releases/download/v0.1.0/lingye_agent-0.1.0-py3-none-any.whl"` | 在已有 Python 应用中使用 `lingye_agent` 包 |

可选依赖按能力拆分：

| Extra | 增加的能力 | 进程外前置条件 |
|---|---|---|
| `rag` | Qdrant 客户端、本地 embedding、TF-IDF | Qdrant 或对应向量服务；embedding 模型或服务 |
| `graph` | Neo4j 图存储 | Neo4j 服务和凭据 |
| `mcp` | FastMCP 客户端与服务端 | 对应 MCP 服务；stdio 场景可能需要 Node.js / npm |
| `nlp` | jieba 与 DashScope SDK | `ContextBuilder` 直接使用 jieba |
| `doc` | MarkItDown PDF 解析 | 输入文件权限；其他格式按解析器准备依赖 |
| `ui` | Gradio 示例依赖 | 示例所需的模型、数据库和网络服务 |
| `all` | 项目声明的全部运行时 extras | 各能力对应的进程外服务 |
| `dev` | 测试、构建与包检查工具 | 源码 checkout |

第三方 MCP npm 包、外部数据库、模型文件和部分搜索 Provider SDK 由具体场景单独准备；`all` 只聚合 `pyproject.toml` 声明的 Python 运行时 extras。

## 3. 核心接口与 LLM 配置

`LingyeLLM` 基于 OpenAI Python SDK，通过 OpenAI-compatible 接口调用模型。最小通用配置如下：

| 变量 | 作用 |
|---|---|
| `LLM_API_KEY` | 模型端点的 API Key |
| `LLM_BASE_URL` | OpenAI-compatible API 根地址 |
| `LLM_MODEL_ID` | 模型标识 |
| `LLM_TIMEOUT` | 可选，请求超时秒数，默认 180 |

也可以使用 `.env.example` 中的 Provider 专用 Key。Provider 的选择取决于显式参数、专用环境变量以及 Key 或 URL 特征。当前实现可识别 OpenAI、AIHubMix、DeepSeek、Qwen、ModelScope、Kimi、智谱、Ollama、vLLM 和通用本地端点。

~~~python
from dotenv import load_dotenv
from lingye_agent import LingyeLLM

load_dotenv()

llm = LingyeLLM(
    temperature=0.2,
    max_tokens=1200,
)
~~~

`temperature` 和 `max_tokens` 由 `LingyeLLM` 的构造参数决定。调用方如果使用 `Config.from_env()`，需要把读出的 `TEMPERATURE` 和 `MAX_TOKENS` 显式传给 `LingyeLLM`。

托管模型会产生网络请求，也可能产生 Provider 费用。本地 Ollama 或 vLLM 需要用户自己启动服务并准备模型。

### 核心运行接口

| 接口 | 输入 | 返回或状态变化 | 调用约束 |
|---|---|---|---|
| `Agent.run(input_text, **kwargs)` | 当前用户输入和策略参数 | 最终文本；具体类按自身实现更新历史或记忆 | 子类必须实现；工具循环和结束条件由具体策略负责 |
| `Agent.add_message()` / `get_history()` / `clear_history()` | `Message` 或无参数 | 写入、复制读取或清空基类 `_history` | 各 Agent 是否在下一次 `run()` 使用该历史，以具体实现为准 |
| `LingyeLLM.invoke(messages, **kwargs)` | OpenAI 格式消息和请求参数 | 完整文本响应 | 调用配置的模型端点，异常统一包装为框架异常 |
| `LingyeLLM.think()` / `stream_invoke()` | 消息、温度和可选输出控制 | 文本片段迭代器 | 调用方负责消费迭代器；`stream_invoke()` 默认不向终端回显 |
| `Message(content, role)` / `to_dict()` | 文本与 `user`、`assistant`、`system` 或 `tool` 角色 | 带时间和元数据的消息；或模型请求字典 | `to_dict()` 只输出 `role` 和 `content` |
| `Config.from_env()` | 进程环境变量 | `Config` 对象 | 读取框架运行配置；模型构造参数仍由调用方显式传给 `LingyeLLM` |

## 4. 工具调用执行时序

`FunctionCallAgent` 的调用链如下。模型负责决策，工具由 Registry 执行：

~~~mermaid
sequenceDiagram
    participant App as Application
    participant Agent as FunctionCallAgent
    participant Registry as ToolRegistry
    participant LLM as Model endpoint

    App->>Agent: run(user_input)
    Agent->>Registry: build tool schemas
    Agent->>LLM: system + history + user + tools
    alt model returns tool_calls
        LLM-->>Agent: assistant(tool_calls)
        Agent->>Registry: execute Tool or function
        Registry-->>Agent: tool result
        Agent->>LLM: assistant(tool_calls) + tool(result)
    else model returns final content
        LLM-->>Agent: final answer
    end
    Agent-->>App: answer
~~~

关键约束：

1. 模型负责选择工具和生成参数，Registry 负责实际执行。
2. Agent 保留 assistant 的 `tool_calls` 消息，并把执行结果作为 `role=tool` 消息配对追加。
3. 循环受 `max_tool_iterations` 限制；达到上限后，Agent 以 `tool_choice="none"` 请求模型收束答案。
4. `optimize_for_cache` 在模型调用前处理消息和 schema，但不执行工具，也不保存业务状态。

## 5. Agent 策略层：能力与选择

六种 Agent 继承同一个 `Agent` 基类，但各自掌管执行流程。`SimpleAgent` 和 `FunctionCallAgent` 会把基类历史带入下一次 `run()`。`ReActAgent`、`PlanAndSolveAgent` 和 `ReflectionAgent` 每次从当前输入开始执行，并记录结果。`ContextAwareAgent` 使用独立的 `conversation_history`，交给 GSSC 组织上下文。`ReActAgent` 和 `PlanAndSolveAgent` 还使用各自的提示模板。

| Agent | 主要执行循环 | 工具支持 | 流式 / 异步现状 |
|---|---|---|---|
| `SimpleAgent` | 普通对话；解析 `[TOOL_CALL:...]` 文本标记后迭代 | 文本循环执行注册的 `Tool` 对象 | `stream_run()` 用于模型文本的增量返回 |
| `FunctionCallAgent` | 原生 `tools` / `tool_calls` 消息循环 | `Tool` 对象和 `register_function()` 函数 | `stream_run()` 当前一次性返回同步结果 |
| `ReActAgent` | Thought → Action → Observation，直到 `Finish` 或步数上限 | `Tool` 对象和函数 | 同步 `run()` |
| `PlanAndSolveAgent` | Planner 生成 Python 列表，Executor 逐步调用模型 | 使用纯模型的规划与执行循环 | 同步 `run()` |
| `ReflectionAgent` | 初次生成 → 反思 → 改写，最多迭代 N 轮 | Registry 作为构造参数保留；执行循环专注于模型反思 | `arun_stream()` 用 start / finish / error 事件包装同步执行 |
| `ContextAwareAgent` | GSSC 构建上下文 → 模型调用 → 写回情景记忆 | MemoryTool / RAGTool 用于上下文构建 | 同步 `run()` |

选型建议：

- 优先从 `SimpleAgent` 验证模型配置。
- 需要可靠的结构化参数时，优先选择 `FunctionCallAgent`。
- 需要显式观察“思考—行动—结果”循环时选择 `ReActAgent`。
- 任务天然可拆解时使用 `PlanAndSolveAgent`，并评估额外调用延迟。
- 输出质量需要多轮自检时使用 `ReflectionAgent`，并设置合理的迭代上限。
- 只有在 Qdrant、embedding、模型和运行时数据边界已经准备好时，再使用 `ContextAwareAgent`。

## 6. 工具层：接口与扩展

工具层支持三种注册方式：

1. 继承 `Tool`，提供结构化参数和 `run()`。
2. 使用 `register_function()` 注册“字符串输入 → 字符串输出”的轻量函数。
3. 使用 `@tool_action` 声明动作，并在 `Tool` 构造时设置 `expandable=True`，才会把复合工具展开成多个独立工具。

### 工具接口契约

| 接口 | 职责 | 返回或副作用 |
|---|---|---|
| `Tool.get_parameters()` | 定义名称、类型、说明、必填性和默认值 | `list[ToolParameter]`，用于参数校验和 tool schema |
| `Tool.run(parameters)` | 执行一个结构化工具 | 文本结果；工具自身负责业务副作用 |
| `Tool.to_openai_schema()` | 把参数定义转换为原生 function calling schema | OpenAI 工具定义字典 |
| `ToolRegistry.register_tool()` | 注册 `Tool`，并按 `expandable` 设置展开子工具 | 更新 Registry 中的结构化工具集合 |
| `ToolRegistry.register_function()` | 注册字符串输入、字符串输出的轻量函数 | 更新 Registry 中的函数集合 |
| `ToolRegistry.execute_tool()` | 按名称执行结构化工具或函数 | 返回工具文本；当前 Registry 会把执行异常转换为错误字符串 |

### 注册简单函数

~~~python
from lingye_agent import ToolRegistry
from lingye_agent.tools import simple_calculate

registry = ToolRegistry()
registry.register_function(
    name="calculator",
    description="计算基础算术表达式",
    func=simple_calculate,
)

print(registry.execute_tool("calculator", "sqrt(16) + 2 * 3"))
~~~

### 实现结构化 Tool

~~~python
from typing import Any
from lingye_agent import Tool, ToolParameter, ToolRegistry


class UppercaseTool(Tool):
    def __init__(self) -> None:
        super().__init__(name="uppercase", description="Convert text to uppercase")

    def get_parameters(self) -> list[ToolParameter]:
        return [
            ToolParameter(
                name="text",
                type="string",
                description="Text to convert",
            )
        ]

    def run(self, parameters: dict[str, Any]) -> str:
        return str(parameters["text"]).upper()


registry = ToolRegistry()
registry.register_tool(UppercaseTool())
print(registry.execute_tool("uppercase", parameters={"text": "Lingye"}))
~~~

内置模块包括 `TerminalTool`、`NoteTool`、`MemoryTool`、`RAGTool`、`MCPTool`、`AdvancedSearchTool`、`ToolChain` 和 `AsyncToolExecutor`。工具可能返回正常文本、错误字符串，也可能抛出异常。宿主应用要分别处理这些结果。

`TerminalTool` 用命令表、工作目录和超时限制执行范围，以当前 Python 进程权限运行 Python、Node 或 shell 命令。调用方要校验模型输出，进程和操作系统隔离则由宿主环境负责。

## 7. 上下文层：GSSC 构建

`ContextBuilder` 会直接导入 jieba，因此需要安装 `nlp` extra。下面只用对话历史和系统指令构建上下文：

~~~python
from lingye_agent.context import ContextBuilder, ContextConfig
from lingye_agent.core import Message

builder = ContextBuilder(
    config=ContextConfig(
        max_tokens=2000,
        reserve_ratio=0.2,
        min_relevance=0.2,
    )
)

context = builder.build(
    user_query="如何降低 Python 服务的内存占用？",
    conversation_history=[
        Message("服务使用 Pandas 处理 CSV。", "user"),
        Message("先测量峰值内存和数据规模。", "assistant"),
    ],
    system_instructions="只给出可验证的优化建议。",
)

print(context)
~~~

GSSC 目前分四个阶段处理上下文：

| 阶段 | 当前行为 | 设计目的 |
|---|---|---|
| Gather | 收集系统指令、记忆结果、RAG 结果、最近 10 条历史和额外 `ContextPacket` | 统一多来源输入 |
| Select | 用 jieba 词项重叠、新近性、相关性阈值和 token 预算筛选 | 保留相关且放得下的信息 |
| Structure | 组织为 Role & Policies、State、Evidence、Context、Output、Task 等区段 | 让模型看到稳定、可读的上下文结构 |
| Compress | 超预算时按行截断到可用 token 数 | 确保请求不继续膨胀 |

`enable_mmr` 和 `mmr_lambda` 目前只是预留配置。需要语义摘要时，调用方可以扩展 Compress 阶段。

## 8. 上下文层：Prompt-cache 预处理

`optimize_for_cache(messages, tools)` 是调用模型前的确定性预处理：

- 合并并前置 system 消息。
- 只在 system 文本中规范时间戳、UUID 和易变 ID。
- 按工具名稳定排序 schema，并规范 `properties` 和 `required` 的顺序。
- 深拷贝输入，不修改调用方对象。
- 保留用户文本以及 assistant `tool_calls` 与紧邻 tool 消息的顺序。

这个函数只规范请求。Prompt Cache 是否命中、能降低多少延迟、如何计费，都由模型 Provider 决定。

## 9. 知识与状态层：记忆模型

| 类型 | 用途 | 当前存储与依赖 | 生命周期 |
|---|---|---|---|
| Working | 当前会话状态、短期事实 | 进程内容器；可选 TF-IDF 增强 | 进程结束后消失 |
| Episodic | 带时间和会话的交互事件 | 文本 embedding；SQLite 保存条目，Qdrant 建向量索引 | 可跨进程持久化 |
| Semantic | 概念、事实和关系检索 | 文本 embedding 与 Qdrant 为主路径，Neo4j / spaCy 为可降级增强 | 可持久化 |
| Perceptual | 文本、图像、音频相关记录 | 文本 embedding；SQLite 保存条目，Qdrant 按模态索引；CLIP / CLAP 可选 | 可持久化 |

`MemoryManager` 统一管理四类记忆。`add_memory()` 返回记忆 ID，`retrieve_memories()` 返回按重要性和时间排序的 `MemoryItem` 列表，`update_memory()` 与 `remove_memory()` 返回操作是否成功。生命周期由 `forget_memories()`、`consolidate_memories()` 和 `clear_all_memories()` 管理；执行清理前，调用方要先定义业务确认和恢复策略。

如需启用 spaCy 增强，要另外安装 spaCy 及其语言模型，并自行验证。

Working Memory 可以单独使用：

~~~python
from lingye_agent.memory import MemoryManager

memory = MemoryManager(
    user_id="demo",
    enable_working=True,
    enable_episodic=False,
    enable_semantic=False,
    enable_perceptual=False,
)

memory.add_memory(
    content="The project uses Python 3.11.",
    memory_type="working",
    importance=0.8,
    auto_classify=False,
)

print(memory.retrieve_memories("Python", memory_types=["working"]))
~~~

`MemoryTool` 默认启用 working、episodic 和 semantic。完整初始化需要 `rag` 依赖、embedding 和 Qdrant。Qdrant 在进程外运行；`QDRANT_URL` 为空时，默认连接 `localhost:6333`。

SQLite 文件默认写入 `memory_data/`。Git 会忽略这个目录以及 `knowledge_base/`、`data_science_kb/`，但其中的数据仍以本地明文保存。敏感信息要放进受保护的独立存储。

## 10. 知识与状态层：RAG 流程

RAG 的主路径是：

~~~text
document / text
  → parse
  → deterministic chunking + overlap
  → embedding
  → Qdrant index
  → retrieve / optional Multi-Query or HyDE expansion
  → retrieved context with source metadata
  → optional ask action generates an LLM answer
~~~

前置条件：

- 安装 `rag`；解析 PDF 时安装 `doc`。其他格式按 MarkItDown 对应的依赖要求另行安装，并以实际验证结果为准。
- 启动或配置 Qdrant，并保持集合的向量维度与 embedding 一致。
- 配置本地 embedding 目录或托管 embedding 服务。
- 配置有效的 `LingyeLLM` 模型端点；当前 `RAGTool` 构造阶段会无条件创建 LLM 客户端，因此即使只使用 add / search 动作也需要这项配置。

下面完成最小初始化，并关闭高级检索以减少调用：

~~~python
from lingye_agent.tools import RAGTool

rag = RAGTool(
    knowledge_base_path="./knowledge_base",
    rag_namespace="project-docs",
)

print(rag.run({
    "action": "add_text",
    "text": "Lingye Agent supports several explicit agent patterns.",
    "namespace": "project-docs",
}))

print(rag.run({
    "action": "search",
    "query": "Which agent patterns are available?",
    "namespace": "project-docs",
    "enable_advanced_search": False,
    "limit": 3,
}))
~~~

`RAGTool` 构造时会初始化目录、embedding、Qdrant 和 LLM。高级检索使用 Multi-Query 或 HyDE 查询扩展；`ask` 动作在检索后调用 LLM 生成答案。

`RAGTool.run(parameters)` 根据 `action` 执行不同操作：

| 动作 | 行为 |
|---|---|
| `add_document` / `add_text` | 写入知识库 |
| `search` | 返回检索结果 |
| `ask` | 检索后调用 LLM 生成回答 |
| `stats` | 返回命名空间统计 |
| `clear` | 清理指定命名空间 |

调用方要为写入和清理操作设置文件权限、命名空间隔离和确认流程。

## 11. 协议层：MCP 集成

安装 `mcp` extra 后，可以连接内存、stdio、HTTP 或 SSE MCP 服务。项目还提供 FastMCP server wrapper。

源码 checkout 可显式引用根配置：

~~~python
from lingye_agent.tools import MCPTool

tool = MCPTool.from_config(
    "tavily",
    config_path="config/mcp_servers.json",
)
~~~

从仓库根目录运行这个示例。运行前准备好 Node.js / npm、对应 npm 包、`TAVILY_API_KEY` 和网络连接。Wheel 用户需要提供自己的配置路径，也可以直接传 `server_command` / `server_url`。

安全边界：

- 未显式提供 `env` 时，当前 stdio MCP 客户端会把整个进程环境传给子进程。连接第三方服务时应构造只包含其运行所需系统变量和凭据的环境。
- 根配置中的 filesystem server 默认暴露启动目录 `.`；应从最小权限目录启动，避免暴露整个仓库或用户目录。
- HTTP / SSE MCP 会把调用参数发送到远程服务；先审查服务端、认证方式和数据策略。

## 12. 运行时事件与生命周期

`lingye_agent.core.streaming` 提供 `StreamEvent`、SSE / JSON Lines 转换和缓冲类型；`core.lifecycle` 提供事件、执行上下文和 Hook 类型。各 Agent 按自身执行模型使用这些基础类型。

各 Agent 的流式行为：

- `SimpleAgent.stream_run()` 增量消费普通模型文本。
- `FunctionCallAgent.stream_run()` 目前先完成同步调用，再一次性 yield 最终结果。
- `ReflectionAgent.arun_stream()` 用 start / finish / error 事件包装同步 `run()`。
- 其他 Agent 以同步 `run()` 为主要入口。

接入 WebSocket 或 SSE 前，先验证所选 Agent 的实际行为。基础事件类型只能说明数据结构，不能代替运行时验证。

## 13. 扩展接口契约

### 新增 Agent

继承 `Agent` 并实现 `run()`。新策略要明确：

1. system prompt、历史和当前输入如何组织。
2. 是否调用 `optimize_for_cache`。
3. 工具协议、参数校验和最大迭代次数。
4. 何时写入 `_history`，失败时是否保留中间状态。
5. 同步、异步和流式方法分别保证什么。

### 新增工具

优先用 `Tool` + `ToolParameter` 表达结构化参数；只有简单的字符串转换才使用 `register_function()`。涉及命令、文件、网络或数据库写入时，把权限、超时、可重试性和副作用写进宿主应用，而不是依赖模型自行约束。

### 新增记忆类型或存储

新记忆类型需继承 `BaseMemory`，并接入 `MemoryManager` 的构造流程。文档存储沿用现有抽象。替换向量或图存储时，还要调整内置记忆与 SQLite、Qdrant 或 Neo4j 的组合关系。扩展实现必须说明权威数据源、索引失败后的处理方式、清理语义和多用户隔离。最后用业务存储回执确认持久化结果。

Agent、Tool 与 Memory 都通过显式继承和组合扩展。

## 14. 示例与仓库集成

| 文件 | 展示的组合 | 主要前置条件 |
|---|---|---|
| [`PDF_learning_assistant.py`](../examples/PDF_learning_assistant.py) | PDF、RAG、Memory、Gradio | 源码 checkout；`rag,doc,ui`；`gradio>=6`；模型、embedding、Qdrant |
| [`codebase_maintainer.py`](../examples/codebase_maintainer.py) | 工具、Working Memory、GSSC 与代码库分析 | `nlp`；模型；可信工作区及命令权限 |
| [`project_assistant.py`](../examples/project_assistant.py) | NoteTool、Memory、RAG、GSSC 的组合设计 | `rag,nlp`；模型、embedding、Qdrant；本地笔记目录；运行前需把 NoteTool 字符串返回值适配为 GSSC packet |
| [`doc_assistant.py`](../examples/doc_assistant.py) | 两个 Agent 与两个 MCP 工具的顺序组合 | `mcp`、Node.js / npm、GitHub Token、模型与网络；filesystem MCP 当前使用 `.`，应从受限 cwd 启动或先改路径 |
| [`tavily_search.py`](../examples/tavily_search.py) | MCP 搜索 | `mcp`、Node.js / npm、Tavily Key、网络；当前脚本还需把 `from_config` 显式指向根配置 |

从源码根目录启动 PDF 界面：

~~~bash
python -m pip install -e ".[rag,doc,ui]" "gradio>=6"
python examples/PDF_learning_assistant.py
~~~

界面默认使用 `http://127.0.0.1:7860`。当前示例采用 Gradio 6 的消息结构，需要另外安装 `gradio>=6`。创建助手时会连接模型、embedding 和 Qdrant。

~~~text
lingye_agent/
├── agents/       # 六种 Agent 执行策略
├── cache/        # 请求前缀和工具 schema 稳定化
├── context/      # GSSC 上下文构建
├── core/         # Agent、LLM、消息、配置和事件基础类型
├── memory/       # 记忆类型、RAG 与存储适配
├── protocols/    # MCP 客户端和服务端包装
└── tools/        # 工具、注册表、链与执行器

examples/         # 源码集成示例
tests/            # 单元测试和外部服务场景
config/           # 源码工作区使用的非敏感配置模板
~~~

## 15. 安全与数据边界

- `.env`、API Key、数据库、索引、知识库内容、模型权重和用户数据不得提交。
- 模型、embedding、搜索和远程 MCP 可能接收提示词、检索片段或工具参数；数据脱敏和多租户授权由宿主应用负责。
- `TerminalTool` 以当前进程权限执行命令；操作系统级隔离由宿主环境提供。
- MCP stdio 子进程和第三方 npm / Python 包都要单独审查。先确认包的来源，再尽量少传环境变量。
- SQLite 运行时数据以明文存储；敏感场景需要宿主应用提供磁盘加密、访问控制、备份和删除策略。
- Git 默认忽略 `memory_data/`、`knowledge_base/` 和 `data_science_kb/`。示例还会在当前目录生成 `<project>_notes/`、`<project>_kb/`、`report.md`、`learning_report_*.json` 或 `maintainer_report_*.json`，这些路径未必匹配现有忽略规则。请把运行目录放在仓库外，或提前添加精确的本地忽略规则。
- 工具的最大迭代次数用于控制循环；宿主应用还需配置调用预算、速率限制和费用上限。

## 16. 验证与排错

以下命令在源码 checkout 根目录运行，需先安装 `python -m pip install -e ".[dev]"`。离线快速发布检查：

~~~bash
python -m pytest -q tests/test_release_contract.py tests/test_function_call_agent_unit.py tests/test_simple_calculator.py::test_calculator_tool
~~~

构建与检查：

~~~bash
python -m build
python -m twine check dist/*.whl dist/*.tar.gz
python scripts/verify_release_artifact.py dist/lingye_agent-0.1.0-py3-none-any.whl
~~~

Twine 只检查命令中的 wheel 和 sdist。`SHA256SUMS` 是独立的校验和文件，要单独处理。

完整套件：

~~~bash
python -m pytest
~~~

完整测试包含慢速初始化，也包含模型、Qdrant、Neo4j、MCP、搜索和本地测试服务器场景。部分测试会发起真实网络请求、产生 Provider 费用或写入外部系统。运行前先审查所选测试，并使用隔离的最小权限凭据。快速检查只覆盖发布契约和少量离线单元路径，真实外部集成要分别验证。

| 现象 | 优先检查 |
|---|---|
| 导入 `lingye_agent.context` 失败并提示 jieba | 安装 `nlp` extra |
| `MemoryTool` 初始化失败 | `rag` extra、embedding 配置、Qdrant `localhost:6333` 或 `QDRANT_URL` |
| `RAGTool` 初始化失败 | 模型端点 / LLM 配置，以及 `rag`、embedding 和 Qdrant 前置条件 |
| 模型工具调用没有发生 | 端点是否支持原生 tool calling；工具 schema 和 `tool_choice` 是否正确 |
| MCP 配置文件不存在 | 源码下显式传 `config_path="config/mcp_servers.json"`；wheel 用户提供自己的路径 |
| MCP stdio 无法启动 | Python / Node / npx 是否在 PATH；第三方包、参数和最小环境是否完整 |
| Gradio 示例无法启动 | 是否使用源码 checkout，并安装该示例的全部 extras 和外部服务 |

提交 Issue 时请提供 Python 版本、操作系统、安装 extras、最小复现、完整错误栈和准确的外部服务状态，并删除所有密钥与私人数据。
