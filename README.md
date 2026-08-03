# Lingye Agent

[English](README.en.md) | 简体中文

> 面向研究与产品原型的模块化 Python LLM Agent 框架：多种 Agent 范式、记忆、RAG、MCP 与上下文工程。

[![CI](https://github.com/Ling-ye/Lingye_Agent/actions/workflows/ci.yml/badge.svg)](https://github.com/Ling-ye/Lingye_Agent/actions/workflows/ci.yml)
[![Release](https://img.shields.io/github/v/release/Ling-ye/Lingye_Agent?display_name=tag)](https://github.com/Ling-ye/Lingye_Agent/releases)
[![Python](https://img.shields.io/badge/Python-3.10--3.13-blue.svg)](https://www.python.org/)
[![Status](https://img.shields.io/badge/Status-Beta-yellow.svg)](#beta-说明)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

## 为什么是 Lingye Agent

Lingye Agent 将 Agent 执行、工具、记忆、检索和上下文构建拆成可独立使用的模块。它适合需要在一个代码库中比较多种 Agent 范式，或把 MCP、RAG、记忆与提示缓存组合进原型的开发者。

- 六种 Agent 范式：Simple、Function Call、ReAct、Plan-and-Solve、Reflection、Context-Aware。
- 统一的 OpenAI-compatible LLM 接口，可通过环境变量切换服务端。
- 工作、情景、语义和感知四类记忆，并提供 SQLite、Qdrant、Neo4j 相关适配。
- 文档检索管线、MCP 客户端/服务端、工具注册表和生命周期事件。
- GSSC（Gather、Select、Structure、Compress）上下文构建和稳定前缀缓存优化。

## Beta 说明

v0.1.0 是首个 GitHub 正式版本，项目成熟度标记为 Beta。核心包、发布元数据、wheel 构建和快速离线测试会作为发布门槛；完整测试套件包含较慢或依赖外部服务的场景，当前不作为阻断门槛。Qdrant、Neo4j、MCP 服务、云端模型和搜索服务需要单独部署或配置凭据。

## 安装

项目当前只通过 [GitHub Releases](https://github.com/Ling-ye/Lingye_Agent/releases) 和源码分发，尚未发布到 PyPI。

### 从 Release wheel 安装

~~~bash
python -m pip install "https://github.com/Ling-ye/Lingye_Agent/releases/download/v0.1.0/lingye_agent-0.1.0-py3-none-any.whl"
~~~

需要可选依赖时，将 extra 与 wheel URL 一起传给 pip：

~~~bash
python -m pip install "lingye-agent[rag,mcp] @ https://github.com/Ling-ye/Lingye_Agent/releases/download/v0.1.0/lingye_agent-0.1.0-py3-none-any.whl"
~~~

### 从源码安装

~~~bash
git clone https://github.com/Ling-ye/Lingye_Agent.git
cd Lingye_Agent
git checkout v0.1.0

python -m venv .venv
# Windows PowerShell
.venv\Scripts\Activate.ps1
# Linux / macOS
source .venv/bin/activate

python -m pip install -e .
~~~

常用 extras：

| Extra | 能力 |
|---|---|
| rag | Qdrant、本地 embedding、重排与 TF-IDF |
| graph | Neo4j 图存储 |
| mcp | FastMCP 客户端与服务端 |
| nlp | jieba 与 DashScope |
| doc | MarkItDown 文档解析 |
| ui | Gradio 示例 |
| all | 安装全部可选能力 |
| dev | 测试、构建与包检查工具 |

## 快速开始

复制环境变量模板，并至少配置一组 OpenAI-compatible 模型信息：

~~~bash
copy .env.example .env
# Linux / macOS: cp .env.example .env
~~~

~~~python
from dotenv import load_dotenv
from lingye_agent import LingyeLLM, SimpleAgent

load_dotenv()

agent = SimpleAgent(
    name="助手",
    llm=LingyeLLM(),
    system_prompt="你是一个简洁、可靠的助手。",
)

print(agent.run("用一句话解释 RAG"))
~~~

加入函数工具：

~~~python
from lingye_agent import FunctionCallAgent, LingyeLLM, ToolRegistry
from lingye_agent.tools import simple_calculate

registry = ToolRegistry()
registry.register_function(
    name="calculator",
    description="执行基础算术表达式",
    func=simple_calculate,
)

agent = FunctionCallAgent(
    name="计算助手",
    llm=LingyeLLM(),
    tool_registry=registry,
)

print(agent.run("计算 sqrt(144) + 12 * 8"))
~~~

## 能力矩阵

| 子系统 | 入口 | 核心包 | 可选依赖或服务 |
|---|---|---:|---|
| Agent | lingye_agent.agents | 是 | 模型 API |
| 工具与注册表 | lingye_agent.tools | 是 | 按工具需要 |
| 上下文构建 | lingye_agent.context | 是 | jieba 可选 |
| 工作记忆 | lingye_agent.memory | 是 | 无 |
| 语义检索 / RAG | lingye_agent.memory.rag | 否 | rag、Qdrant |
| 图存储 | lingye_agent.memory.storage | 否 | graph、Neo4j |
| MCP | lingye_agent.protocols.mcp | 否 | mcp |
| 示例 UI | examples | 否 | ui 及对应服务 |

## 架构

~~~mermaid
flowchart TD
    Examples["Examples / Applications"] --> Agents["Agent patterns"]
    Agents --> Core["Core: Agent, LLM, Message, Events"]
    Agents --> Tools["Tools and MCP"]
    Agents --> Context["GSSC Context Builder"]
    Context --> Memory["Memory and RAG"]
    Tools --> Protocols["MCP transports"]
    Memory --> Stores["SQLite / Qdrant / Neo4j"]
~~~

## 文档与示例

- [中文使用指南](docs/guide.zh-CN.md)
- [English guide](docs/guide.en.md)
- [环境变量模板](.env.example)
- [示例应用](examples)
- [更新日志](CHANGELOG.md)
- [贡献指南](CONTRIBUTING.md)
- [安全策略](SECURITY.md)

## 发布校验

发布分支的阻断检查包括：

~~~bash
python -m pytest -q tests/test_release_contract.py tests/test_function_call_agent_unit.py tests/test_simple_calculator.py::test_calculator_tool
python -m build
python -m twine check dist/*
python scripts/verify_release_artifact.py dist/lingye_agent-0.1.0-py3-none-any.whl
~~~

完整测试可用以下命令单独运行；它可能访问可选服务或耗时较长：

~~~bash
python -m pytest
~~~

## 参与贡献

提交代码前请阅读 [CONTRIBUTING.md](CONTRIBUTING.md)。安全问题请按 [SECURITY.md](SECURITY.md) 私下报告，不要在公开 Issue 中披露密钥或可利用细节。

## License

[MIT License](LICENSE) © Lingye Agent Contributors
