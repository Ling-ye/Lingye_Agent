# Lingye Agent

[English](README.en.md) | 简体中文

> 一个模块化 Python 框架，用来学习、实验和构建 LLM Agent。多种 Agent 策略、工具调用、记忆、RAG、MCP 与上下文工程都放在同一套代码中。

[![CI](https://github.com/Ling-ye/Lingye_Agent/actions/workflows/ci.yml/badge.svg)](https://github.com/Ling-ye/Lingye_Agent/actions/workflows/ci.yml)
[![Release](https://img.shields.io/github/v/release/Ling-ye/Lingye_Agent?display_name=tag)](https://github.com/Ling-ye/Lingye_Agent/releases)
[![Python](https://img.shields.io/badge/Python-3.10--3.13-blue.svg)](https://www.python.org/)
[![Status](https://img.shields.io/badge/Status-Beta-yellow.svg)](#项目状态)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

## 项目简介

Lingye Agent 把 Agent 的决策循环、模型调用、工具执行、上下文构建和知识存储拆成一组可以自由组合的模块。先用一个简单的对话 Agent 跑通模型，再按任务需要接入函数工具、长期记忆、知识库或 MCP 服务。

项目内置六种执行策略：Simple、Function Call、ReAct、Plan-and-Solve、Reflection 和 Context-Aware。六种策略共用模型、消息和工具等基础类型，各自保留独立的执行流程。读代码时可以直接比较它们如何做决策，也便于拿来开发原型。

## 能做什么

- **对话助手**：使用 OpenAI-compatible 模型，快速构建带系统提示词和历史记录的助手。
- **工具型 Agent**：让模型调用计算器、本地函数和自定义工具。调用方式可以选原生 function calling，也可以用显式 ReAct 循环。
- **复杂任务处理**：用 Plan-and-Solve 拆解步骤，或用 Reflection 对结果进行多轮评价和改写。
- **知识库问答**：组合文档解析、embedding、Qdrant 和 RAG，构建面向项目资料的检索助手。
- **长期项目助手**：使用工作、情景、语义和感知记忆，保存当前状态、历史经验和可检索信息。
- **MCP 集成**：连接 stdio、HTTP 或 SSE MCP 服务，把外部能力纳入统一工具调用流程。
- **上下文工程实验**：通过 GSSC 和请求预处理控制 token 预算、上下文结构与稳定前缀。

## 新手快速部署

先准备 Python 3.10 或更高版本，以及一个 OpenAI-compatible 模型端点。

### 1. 获取源码

~~~bash
git clone https://github.com/Ling-ye/Lingye_Agent.git
cd Lingye_Agent
~~~

### 2. 创建虚拟环境并安装

Windows PowerShell：

~~~powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e .
Copy-Item .env.example .env
~~~

Linux / macOS：

~~~bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
cp .env.example .env
~~~

打开 `.env`，填写模型服务对应的 `LLM_API_KEY`、`LLM_BASE_URL` 和 `LLM_MODEL_ID`。也可以使用模板中的 Provider 专用配置。

### 3. 运行第一个 Agent

将以下代码保存为 `quickstart.py`：

~~~python
from dotenv import load_dotenv
from lingye_agent import LingyeLLM, SimpleAgent

load_dotenv()

agent = SimpleAgent(
    name="assistant",
    llm=LingyeLLM(),
    system_prompt="你是一个简洁、可靠的助手。",
)

print(agent.run("用一句话解释 RAG。"))
~~~

运行：

~~~bash
python quickstart.py
~~~

运行这段代码会调用你配置的模型服务。使用托管模型时，请留意 Provider 的费用。

### 在已有项目中安装 SDK

~~~bash
python -m pip install "https://github.com/Ling-ye/Lingye_Agent/releases/download/v0.1.0/lingye_agent-0.1.0-py3-none-any.whl"
~~~

完整说明见架构与接口指南中的[运行环境与依赖边界](docs/guide.zh-CN.md#2-运行环境与依赖边界)和[核心接口与 LLM 配置](docs/guide.zh-CN.md#3-核心接口与-llm-配置)。

## 按场景选择入口

| 目标 | 建议入口 | 需要准备 |
|---|---|---|
| 先验证模型和提示词 | `SimpleAgent` | 基础安装、模型端点 |
| 调用参数明确的函数或工具 | `FunctionCallAgent` | 支持 tool calling 的模型端点 |
| 展示“思考—行动—观察”过程 | `ReActAgent` | 工具注册表、迭代上限 |
| 分解并执行多步骤任务 | `PlanAndSolveAgent` | 额外模型调用预算 |
| 对结果多轮评价和改写 | `ReflectionAgent` | 反思轮数和调用预算 |
| 使用记忆与知识库构建上下文 | `ContextAwareAgent` | `nlp`、`rag`、embedding、Qdrant |

按场景增加依赖，例如：

~~~bash
# GSSC 上下文构建
python -m pip install -e ".[nlp]"

# RAG、PDF 解析和上下文构建
python -m pip install -e ".[rag,doc,nlp]"

# MCP 客户端与服务端
python -m pip install -e ".[mcp]"
~~~

## 示例项目

[`examples/`](examples) 中有以下组合示例：

- [`PDF_learning_assistant.py`](examples/PDF_learning_assistant.py)：PDF、RAG、Memory 与 Gradio。
- [`codebase_maintainer.py`](examples/codebase_maintainer.py)：代码分析工具、Working Memory 与 GSSC。
- [`project_assistant.py`](examples/project_assistant.py)：笔记、记忆、RAG 与项目上下文。
- [`doc_assistant.py`](examples/doc_assistant.py)：多个 Agent 与 MCP 工具的顺序协作。
- [`tavily_search.py`](examples/tavily_search.py)：通过 MCP 接入网络搜索。

示例涉及的 extras、模型、数据库、目录权限和第三方服务见[示例与仓库集成](docs/guide.zh-CN.md#14-示例与仓库集成)。

## 架构与接口文档

分层设计和接口细节统一放在[中文架构与接口指南](docs/guide.zh-CN.md)：

- 分层职责、依赖方向和一次请求的执行链路。
- `Agent`、`LingyeLLM`、`Message`、`ToolRegistry` 和 `ContextBuilder` 等核心接口。
- 六种 Agent 的执行策略、工具能力、历史管理和流式行为。
- GSSC、Prompt Cache、Memory、RAG、MCP 的设计与运行边界。
- 新增 Agent、工具和存储后端时需要实现的契约。
- 安全边界、验证命令和常见故障排查。

其他资料：

- [English architecture and API guide](docs/guide.en.md)
- [环境变量模板](.env.example)
- [更新日志](CHANGELOG.md)
- [贡献指南](CONTRIBUTING.md)
- [安全策略](SECURITY.md)

## 项目状态

当前版本为 `v0.1.0`，项目成熟度为 **Beta**。模型、embedding、Qdrant、Neo4j、MCP 和搜索能力需要按场景配置。会执行命令或读写文件、网络和数据库的工具沿用宿主进程权限，请在可信工作区中运行，并使用最小权限凭据。

## 参与贡献

提交代码前请阅读[贡献指南](CONTRIBUTING.md)。安全问题请按[安全策略](SECURITY.md)私下报告。

## License

[MIT License](LICENSE) © Lingye Agent Contributors
