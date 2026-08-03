# Lingye Agent

English | [简体中文](README.md)

> A modular Python framework for LLM agents, combining multiple agent patterns, memory, RAG, MCP, and context engineering.

[![CI](https://github.com/Ling-ye/Lingye_Agent/actions/workflows/ci.yml/badge.svg)](https://github.com/Ling-ye/Lingye_Agent/actions/workflows/ci.yml)
[![Release](https://img.shields.io/github/v/release/Ling-ye/Lingye_Agent?display_name=tag)](https://github.com/Ling-ye/Lingye_Agent/releases)
[![Python](https://img.shields.io/badge/Python-3.10--3.13-blue.svg)](https://www.python.org/)
[![Status](https://img.shields.io/badge/Status-Beta-yellow.svg)](#beta-status)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

## Why Lingye Agent

Lingye Agent separates agent execution, tools, memory, retrieval, and context construction into modules that can be used independently. It is intended for developers who want to compare agent patterns in one codebase or combine MCP, RAG, memory, and prompt-cache optimization in a prototype.

- Six agent patterns: Simple, Function Call, ReAct, Plan-and-Solve, Reflection, and Context-Aware.
- A unified interface for OpenAI-compatible model endpoints, selected through environment variables.
- Working, episodic, semantic, and perceptual memory with SQLite, Qdrant, and Neo4j integrations.
- Document retrieval, MCP client/server support, a tool registry, streaming events, and lifecycle hooks.
- GSSC (Gather, Select, Structure, Compress) context construction and stable-prefix cache optimization.

## Beta status

v0.1.0 is the first stable-channel GitHub release, while the project maturity remains Beta. Core packaging, release metadata, wheel construction, and fast offline checks are release gates. The full test suite includes slower scenarios and integrations that require external services, so it is currently reported but not blocking. Qdrant, Neo4j, MCP servers, hosted models, and search providers must be deployed or configured separately.

## Installation

The project is currently distributed through [GitHub Releases](https://github.com/Ling-ye/Lingye_Agent/releases) and source. It is not published on PyPI.

### Install the release wheel

~~~bash
python -m pip install "https://github.com/Ling-ye/Lingye_Agent/releases/download/v0.1.0/lingye_agent-0.1.0-py3-none-any.whl"
~~~

Install optional features by combining extras with the wheel URL:

~~~bash
python -m pip install "lingye-agent[rag,mcp] @ https://github.com/Ling-ye/Lingye_Agent/releases/download/v0.1.0/lingye_agent-0.1.0-py3-none-any.whl"
~~~

### Install from source

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

Available extras:

| Extra | Capability |
|---|---|
| rag | Qdrant, local embeddings, reranking, and TF-IDF |
| graph | Neo4j graph storage |
| mcp | FastMCP client and server |
| nlp | jieba and DashScope |
| doc | MarkItDown document parsing |
| ui | Gradio examples |
| all | All optional runtime features |
| dev | Tests, package builds, and package checks |

## Quick start

Copy the environment template and configure at least one OpenAI-compatible model endpoint:

~~~bash
copy .env.example .env
# Linux / macOS: cp .env.example .env
~~~

~~~python
from dotenv import load_dotenv
from lingye_agent import LingyeLLM, SimpleAgent

load_dotenv()

agent = SimpleAgent(
    name="assistant",
    llm=LingyeLLM(),
    system_prompt="Be concise and reliable.",
)

print(agent.run("Explain RAG in one sentence."))
~~~

Add a function tool:

~~~python
from lingye_agent import FunctionCallAgent, LingyeLLM, ToolRegistry
from lingye_agent.tools import simple_calculate

registry = ToolRegistry()
registry.register_function(
    name="calculator",
    description="Evaluate a basic arithmetic expression",
    func=simple_calculate,
)

agent = FunctionCallAgent(
    name="calculator-assistant",
    llm=LingyeLLM(),
    tool_registry=registry,
)

print(agent.run("Calculate sqrt(144) + 12 * 8"))
~~~

## Capability matrix

| Subsystem | Entry point | Core package | Optional dependency or service |
|---|---|---:|---|
| Agents | lingye_agent.agents | Yes | Model API |
| Tools and registry | lingye_agent.tools | Yes | Tool-specific |
| Context construction | lingye_agent.context | Yes | jieba optional |
| Working memory | lingye_agent.memory | Yes | None |
| Semantic retrieval / RAG | lingye_agent.memory.rag | No | rag, Qdrant |
| Graph storage | lingye_agent.memory.storage | No | graph, Neo4j |
| MCP | lingye_agent.protocols.mcp | No | mcp |
| Example UI | examples | No | ui and related services |

## Architecture

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

## Documentation and examples

- [English guide](docs/guide.en.md)
- [中文使用指南](docs/guide.zh-CN.md)
- [Environment template](.env.example)
- [Example applications](examples)
- [Changelog](CHANGELOG.md)
- [Contributing guide](CONTRIBUTING.md)
- [Security policy](SECURITY.md)

## Release checks

Blocking release checks:

~~~bash
python -m pytest -q tests/test_release_contract.py tests/test_function_call_agent_unit.py tests/test_simple_calculator.py::test_calculator_tool
python -m build
python -m twine check dist/*
python scripts/verify_release_artifact.py dist/lingye_agent-0.1.0-py3-none-any.whl
~~~

Run the full suite separately. It can access optional services or take substantially longer:

~~~bash
python -m pytest
~~~

## Contributing

Read [CONTRIBUTING.md](CONTRIBUTING.md) before opening a pull request. Report security issues privately according to [SECURITY.md](SECURITY.md); do not disclose secrets or exploitable details in a public issue.

## License

[MIT License](LICENSE) © Lingye Agent Contributors
