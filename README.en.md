# Lingye Agent

English | [简体中文](README.md)

> A modular Python framework for learning, experimenting with, and building LLM agents with multiple agent strategies, tool calling, memory, RAG, MCP, and context engineering.

[![CI](https://github.com/Ling-ye/Lingye_Agent/actions/workflows/ci.yml/badge.svg)](https://github.com/Ling-ye/Lingye_Agent/actions/workflows/ci.yml)
[![Release](https://img.shields.io/github/v/release/Ling-ye/Lingye_Agent?display_name=tag)](https://github.com/Ling-ye/Lingye_Agent/releases)
[![Python](https://img.shields.io/badge/Python-3.10--3.13-blue.svg)](https://www.python.org/)
[![Status](https://img.shields.io/badge/Status-Beta-yellow.svg)](#project-status)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

## Overview

Lingye Agent separates decision loops, model calls, tool execution, context construction, and knowledge storage into composable modules. Start with a simple conversational agent, then add function tools, long-term memory, a knowledge base, or MCP services as the task grows.

The project includes six execution strategies: Simple, Function Call, ReAct, Plan-and-Solve, Reflection, and Context-Aware. They share model, message, and tool abstractions while keeping each execution flow explicit, making the codebase useful for learning, comparing designs, and building prototypes.

## What you can build

- **Conversational assistants:** build assistants with system prompts and history on OpenAI-compatible model endpoints.
- **Tool-using agents:** let a model call calculators, local functions, and custom tools through native function calling or an explicit ReAct loop.
- **Complex-task workflows:** decompose work with Plan-and-Solve or improve results through repeated Reflection passes.
- **Knowledge-base assistants:** combine document parsing, embeddings, Qdrant, and RAG for project-document retrieval.
- **Long-running project assistants:** use working, episodic, semantic, and perceptual memory for current state, experience, and searchable information.
- **MCP integrations:** connect stdio, HTTP, or SSE MCP services through the same tool execution path.
- **Context-engineering experiments:** use GSSC and request preprocessing to control token budgets, context structure, and stable prefixes.

## Beginner quick start

Prepare Python 3.10 or later and an OpenAI-compatible model endpoint.

### 1. Get the source

~~~bash
git clone https://github.com/Ling-ye/Lingye_Agent.git
cd Lingye_Agent
~~~

### 2. Create an environment and install

Windows PowerShell:

~~~powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e .
Copy-Item .env.example .env
~~~

Linux / macOS:

~~~bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
cp .env.example .env
~~~

Open `.env` and set `LLM_API_KEY`, `LLM_BASE_URL`, and `LLM_MODEL_ID` for the selected model service. You can instead use a provider-specific configuration from the template.

### 3. Run your first agent

Save the following as `quickstart.py`:

~~~python
from dotenv import load_dotenv
from lingye_agent import LingyeLLM, SimpleAgent

load_dotenv()

agent = SimpleAgent(
    name="assistant",
    llm=LingyeLLM(),
    system_prompt="You are a concise, reliable assistant.",
)

print(agent.run("Explain RAG in one sentence."))
~~~

Run it:

~~~bash
python quickstart.py
~~~

This example calls the configured model service. Check the provider's usage charges when using a hosted model.

### Install the SDK in an existing project

~~~bash
python -m pip install "https://github.com/Ling-ye/Lingye_Agent/releases/download/v0.1.0/lingye_agent-0.1.0-py3-none-any.whl"
~~~

See [Runtime and dependency boundaries](docs/guide.en.md#2-runtime-and-dependency-boundaries) and [Core interfaces and LLM configuration](docs/guide.en.md#3-core-interfaces-and-llm-configuration) for the complete setup reference.

## Choose an entry point

| Goal | Suggested entry point | Prepare |
|---|---|---|
| Verify the model and prompt first | `SimpleAgent` | Base installation and a model endpoint |
| Call functions or tools with explicit parameters | `FunctionCallAgent` | A model endpoint with compatible tool calling |
| Expose a reason–act–observe loop | `ReActAgent` | A tool registry and iteration limit |
| Decompose and execute multi-step work | `PlanAndSolveAgent` | Additional model-call budget |
| Critique and rewrite results repeatedly | `ReflectionAgent` | Reflection count and call budget |
| Build context from memory and a knowledge base | `ContextAwareAgent` | `nlp`, `rag`, embeddings, and Qdrant |

Add dependencies for the selected scenario, for example:

~~~bash
# GSSC context construction
python -m pip install -e ".[nlp]"

# RAG, PDF parsing, and context construction
python -m pip install -e ".[rag,doc,nlp]"

# MCP client and server
python -m pip install -e ".[mcp]"
~~~

## Example projects

[`examples/`](examples) demonstrates these compositions:

- [`PDF_learning_assistant.py`](examples/PDF_learning_assistant.py): PDF, RAG, Memory, and Gradio.
- [`codebase_maintainer.py`](examples/codebase_maintainer.py): code-analysis tools, Working Memory, and GSSC.
- [`project_assistant.py`](examples/project_assistant.py): notes, memory, RAG, and project context.
- [`doc_assistant.py`](examples/doc_assistant.py): sequential collaboration between multiple agents and MCP tools.
- [`tavily_search.py`](examples/tavily_search.py): web search through MCP.

See [Examples and repository integration](docs/guide.en.md#14-examples-and-repository-integration) for each example's extras, model, database, directory-permission, and third-party-service requirements.

## Architecture and API documentation

The [English architecture and API guide](docs/guide.en.md) covers:

- Layer responsibilities, dependency direction, and the request execution path.
- Core interfaces including `Agent`, `LingyeLLM`, `Message`, `ToolRegistry`, and `ContextBuilder`.
- Execution strategy, tool behavior, history handling, and streaming behavior for all six agents.
- Design and runtime boundaries for GSSC, prompt caching, memory, RAG, and MCP.
- Contracts for adding an agent, tool, or storage backend.
- Security boundaries, validation commands, and troubleshooting.

Other resources:

- [中文架构与接口指南](docs/guide.zh-CN.md)
- [Environment template](.env.example)
- [Changelog](CHANGELOG.md)
- [Contributing guide](CONTRIBUTING.md)
- [Security policy](SECURITY.md)

## Project status

The current release is `v0.1.0`, and project maturity is **Beta**. Configure model, embedding, Qdrant, Neo4j, MCP, and search services for the selected scenario. Tools that perform command, filesystem, network, or database writes inherit host-process permissions, so run them in a trusted workspace with least-privilege credentials.

## Contributing

Read the [contributing guide](CONTRIBUTING.md) before submitting code. Report security issues privately according to the [security policy](SECURITY.md).

## License

[MIT License](LICENSE) © Lingye Agent Contributors
