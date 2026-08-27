# Lingye Agent Architecture and API Guide

[Back to the English README](../README.en.md) | [中文指南](guide.zh-CN.md)

## 1. Layered architecture and design principles

Lingye Agent uses explicit orchestration: each agent strategy implements its own model calls, tool loop, and stopping conditions, while core types and composed objects provide shared capabilities. Reading a concrete agent class reveals the control flow of one request, and tools, context, or storage implementations can be replaced independently.

| Layer | Primary entry point | Responsibility | Design approach |
|---|---|---|---|
| Application | `examples/`, user code | Compose agents, tools, and data sources into an interaction | Keep business workflows in the application and expose composable framework parts |
| Agent strategy | `lingye_agent.agents` | Decide when to call the model or a tool and when to stop | Give each strategy one explicit execution loop |
| Core runtime | `Agent`, `LingyeLLM`, `Message`, `Config` | Unify model access, message format, shared state, and configuration | Keep the common abstraction small and express strategy differences in subclasses |
| Tools | `ToolRegistry`, `Tool` | Describe, register, and execute functions, structured tools, and MCP tools | The model selects and supplies arguments; the registry performs execution |
| Context | `ContextBuilder`, `optimize_for_cache` | Organize information within a token budget and stabilize request prefixes | Keep context selection separate from agent decisions so it can be verified independently |
| Knowledge and state | `MemoryManager`, `RAGTool` | Manage transient state, experience, semantic indexes, and external knowledge | Separate memory state from document retrieval |
| Protocol and storage | MCP, SQLite, Qdrant, Neo4j | Connect out-of-process tools and persistence infrastructure | Let the host environment control external side effects and credentials |

Dependencies point from the application toward strategy and core layers. An agent composes tools and context as needed; context can then read Memory or RAG. MCP, databases, and model endpoints sit outside the process boundary and connect through adapters.

~~~text
Application
   └─ Agent strategy
      ├─ Agent + LingyeLLM + per-strategy prompt/state
      ├─ ToolRegistry ──> local Tool / function / MCP
      └─ ContextBuilder
         ├─ MemoryTool ──> in-memory / SQLite / Qdrant / Neo4j
         └─ RAGTool ──> Qdrant
~~~

## 2. Runtime and dependency boundaries

Package metadata requires Python 3.10 or later. GitHub Actions validates the base/development release contract on `ubuntu-latest` with Python 3.10–3.13. See the README [beginner quick start](../README.en.md#beginner-quick-start) for the complete virtual-environment, configuration, and first-agent workflow.

| Installation mode | Command | Use case |
|---|---|---|
| Editable source install | `python -m pip install -e .` | Run `examples/`, use root `config/`, debug, or extend the source |
| Release wheel | `python -m pip install "https://github.com/Ling-ye/Lingye_Agent/releases/download/v0.1.0/lingye_agent-0.1.0-py3-none-any.whl"` | Use the `lingye_agent` package in an existing Python application |

Optional dependencies are grouped by capability:

| Extra | Added capability | Out-of-process prerequisite |
|---|---|---|
| `rag` | Qdrant client, local embeddings, and TF-IDF | Qdrant or another configured vector service; embedding model or service |
| `graph` | Neo4j graph storage | Neo4j service and credentials |
| `mcp` | FastMCP client and server | The selected MCP service; stdio scenarios may need Node.js/npm |
| `nlp` | jieba and the DashScope SDK | `ContextBuilder` imports jieba directly |
| `doc` | MarkItDown PDF parsing | Input-file permissions; other formats need parser-specific dependencies |
| `ui` | Gradio example dependencies | The model, database, and network services required by the example |
| `all` | Every runtime extra declared by the project | Out-of-process services required by each capability |
| `dev` | Tests, builds, and package checks | A source checkout |

Third-party MCP npm packages, external databases, model files, and some search-provider SDKs remain scenario-specific. `all` aggregates only the Python runtime extras declared in `pyproject.toml`.

## 3. Core interfaces and LLM configuration

`LingyeLLM` uses the OpenAI Python SDK to access OpenAI-compatible interfaces. The minimal generic settings are:

| Variable | Purpose |
|---|---|
| `LLM_API_KEY` | API key for the model endpoint |
| `LLM_BASE_URL` | OpenAI-compatible API root |
| `LLM_MODEL_ID` | Model identifier |
| `LLM_TIMEOUT` | Optional request timeout in seconds; defaults to 180 |

You can also use provider-specific keys from `.env.example`. The implementation chooses OpenAI, AIHubMix, DeepSeek, Qwen, ModelScope, Kimi, Zhipu, Ollama, vLLM, or a generic local endpoint based on explicit arguments, provider-specific environment variables, and key or URL characteristics.

~~~python
from dotenv import load_dotenv
from lingye_agent import LingyeLLM

load_dotenv()

llm = LingyeLLM(
    temperature=0.2,
    max_tokens=1200,
)
~~~

The `LingyeLLM` constructor determines `temperature` and `max_tokens`. `Config.from_env()` can read `TEMPERATURE` and `MAX_TOKENS` for callers to pass in when creating the model client.

Hosted models generate network traffic and can incur provider charges. Local Ollama or vLLM usage still requires you to start the service and prepare a model.

### Core runtime interfaces

| Interface | Input | Return or state change | Calling contract |
|---|---|---|---|
| `Agent.run(input_text, **kwargs)` | Current user input and strategy parameters | Final text; the concrete class updates history or memory according to its implementation | Subclasses implement it and own the tool loop and stopping conditions |
| `Agent.add_message()` / `get_history()` / `clear_history()` | A `Message`, or no arguments | Write, copy-read, or clear base `_history` | Whether the next `run()` consumes this history depends on the concrete agent |
| `LingyeLLM.invoke(messages, **kwargs)` | OpenAI-format messages and request arguments | Complete text response | Calls the configured model endpoint and wraps failures in framework exceptions |
| `LingyeLLM.think()` / `stream_invoke()` | Messages, temperature, and optional output control | Iterator of text chunks | The caller consumes the iterator; `stream_invoke()` does not echo to the terminal by default |
| `Message(content, role)` / `to_dict()` | Text and a `user`, `assistant`, `system`, or `tool` role | A message with timestamp and metadata, or a model-request dictionary | `to_dict()` emits only `role` and `content` |
| `Config.from_env()` | Process environment variables | A `Config` object | Reads framework runtime values; the caller still passes model constructor values to `LingyeLLM` explicitly |

## 4. Tool-call execution sequence

`FunctionCallAgent` most clearly demonstrates the separation between model decisions and tool execution:

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

Key constraints:

1. The model chooses the tool and generates arguments; the registry performs the actual execution.
2. The agent preserves the assistant `tool_calls` message and appends the result as its paired `role=tool` message.
3. `max_tool_iterations` bounds the loop. At the limit, the agent requests a final answer with `tool_choice="none"`.
4. `optimize_for_cache` processes messages and schemas before model calls. It neither executes tools nor stores application state.

## 5. Agent strategy layer: capabilities and selection

The six agents inherit one `Agent` base and use models, prompts, configuration, and history according to their execution strategies. `SimpleAgent` and `FunctionCallAgent` feed base history into the next `run()`; `ReActAgent`, `PlanAndSolveAgent`, and `ReflectionAgent` start each execution loop from the current input and record the result; `ContextAwareAgent` organizes its own `conversation_history` through GSSC. `ReActAgent` and `PlanAndSolveAgent` use their own prompt templates.

| Agent | Main execution loop | Tool support | Current streaming / async behavior |
|---|---|---|---|
| `SimpleAgent` | Normal conversation; iterates after parsing `[TOOL_CALL:...]` text markers | Its text loop invokes registered `Tool` objects | `stream_run()` incrementally returns model text |
| `FunctionCallAgent` | Native `tools` / `tool_calls` message loop | `Tool` objects and `register_function()` functions | `stream_run()` currently yields the completed synchronous result once |
| `ReActAgent` | Thought → Action → Observation until `Finish` or the step limit | `Tool` objects and functions | Synchronous `run()` |
| `PlanAndSolveAgent` | Planner emits a Python list; Executor calls the model for each step | Model-only planning and execution loop | Synchronous `run()` |
| `ReflectionAgent` | Initial answer → reflection → refinement for up to N iterations | Registry remains a constructor parameter; the loop focuses on model reflection | `arun_stream()` wraps synchronous execution with start / finish / error events |
| `ContextAwareAgent` | GSSC context → model call → episodic-memory write-back | MemoryTool / RAGTool provide context | Synchronous `run()` |

Selection guidance:

- Start with `SimpleAgent` to verify model configuration.
- Prefer `FunctionCallAgent` when structured arguments must be reliable.
- Choose `ReActAgent` when you want an explicit “reason—act—observe” loop.
- Use `PlanAndSolveAgent` for naturally decomposable tasks, after accounting for extra call latency.
- Use `ReflectionAgent` when outputs benefit from repeated self-review, with a bounded iteration count.
- Use `ContextAwareAgent` only after Qdrant, embeddings, the model endpoint, and runtime-data boundaries are ready.

## 6. Tool layer: interfaces and extension

The tool layer supports three registration styles:

1. Subclass `Tool` and provide structured parameters plus `run()`.
2. Use `register_function()` for a lightweight string-input/string-output function.
3. Declare actions with `@tool_action` and set `expandable=True` when constructing the `Tool`; both are required to expose the composite tool as independent tools.

### Tool interface contracts

| Interface | Responsibility | Return or side effect |
|---|---|---|
| `Tool.get_parameters()` | Define names, types, descriptions, required flags, and defaults | A `list[ToolParameter]` used for validation and tool schemas |
| `Tool.run(parameters)` | Execute one structured tool | Text result; the tool owns its business side effects |
| `Tool.to_openai_schema()` | Convert parameter definitions into a native function-calling schema | OpenAI tool-definition dictionary |
| `ToolRegistry.register_tool()` | Register a `Tool` and expand sub-tools according to `expandable` | Updates the registry's structured-tool collection |
| `ToolRegistry.register_function()` | Register a lightweight string-input/string-output function | Updates the registry's function collection |
| `ToolRegistry.execute_tool()` | Execute a structured tool or function by name | Returns tool text; the current registry converts execution exceptions into error strings |

### Register a simple function

~~~python
from lingye_agent import ToolRegistry
from lingye_agent.tools import simple_calculate

registry = ToolRegistry()
registry.register_function(
    name="calculator",
    description="Evaluate a basic arithmetic expression",
    func=simple_calculate,
)

print(registry.execute_tool("calculator", "sqrt(16) + 2 * 3"))
~~~

### Implement a structured Tool

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

Built-in modules include `TerminalTool`, `NoteTool`, `MemoryTool`, `RAGTool`, `MCPTool`, `AdvancedSearchTool`, `ToolChain`, and `AsyncToolExecutor`. Tools can return normal text, return error strings, or raise exceptions; host applications handle each path explicitly.

`TerminalTool` controls execution through command lists, workspace restrictions, and timeouts, and runs Python, Node, or shell commands with the current Python process permissions. Callers validate model output and provide process and operating-system isolation through the host environment.

## 7. Context layer: GSSC construction

Using `ContextBuilder` requires the `nlp` extra because the current implementation imports jieba directly. This example builds context from conversation history and system instructions:

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
    user_query="How can I reduce memory use in a Python service?",
    conversation_history=[
        Message("The service processes CSV files with Pandas.", "user"),
        Message("Measure peak memory and input sizes first.", "assistant"),
    ],
    system_instructions="Only provide optimizations that can be verified.",
)

print(context)
~~~

The current GSSC implementation works as follows:

| Stage | Current behavior | Design purpose |
|---|---|---|
| Gather | Collect system instructions, memory results, RAG results, the latest 10 history messages, and extra `ContextPacket` objects | Normalize multi-source input |
| Select | Filter using jieba term overlap, recency, a relevance threshold, and the token budget | Retain relevant content that fits |
| Structure | Build sections such as Role & Policies, State, Evidence, Context, Output, and Task | Give the model a stable, readable context layout |
| Compress | Truncate by line to the available token count when over budget | Stop request growth |

Select currently uses jieba term overlap, recency, a relevance threshold, and the token budget; `enable_mmr` and `mmr_lambda` remain reserved configuration fields. Compress truncates by line when over budget, while callers can add semantic summarization when needed.

## 8. Context layer: prompt-cache preprocessing

`optimize_for_cache(messages, tools)` is deterministic preprocessing before a model call:

- Merge system messages and move them to the front.
- Normalize timestamps, UUIDs, and volatile IDs only in system text.
- Sort schemas by tool name and stabilize `properties` and `required` ordering.
- Deep-copy input instead of mutating caller-owned objects.
- Preserve user text and the ordering of assistant `tool_calls` with adjacent tool messages.

This function performs request normalization only. Prompt-cache hits, latency, and billing follow the selected provider's policy.

## 9. Knowledge and state layer: memory model

| Type | Purpose | Current storage and dependencies | Lifetime |
|---|---|---|---|
| Working | Current-session state and transient facts | In-process container; optional TF-IDF enhancement | Disappears with the process |
| Episodic | Time- and session-oriented interaction events | Text embeddings; SQLite stores records and Qdrant provides a vector index | Persistent across processes |
| Semantic | Concept, fact, and relationship retrieval | Text embeddings and Qdrant are the primary path; Neo4j / spaCy are degradable enhancements | Persistent |
| Perceptual | Text-, image-, and audio-related records | Text embeddings; SQLite stores records and Qdrant indexes modalities; CLIP / CLAP are optional | Persistent |

`MemoryManager` is the orchestration entry point for all four memory types. `add_memory()` returns a memory ID; `retrieve_memories()` returns `MemoryItem` objects ordered by importance and time; `update_memory()` and `remove_memory()` report success. `forget_memories()`, `consolidate_memories()`, and `clear_all_memories()` manage lifecycle, so callers define business confirmation and recovery policy before cleanup.

To enable the spaCy enhancement, install and verify spaCy and its language model separately.

Use Working Memory independently:

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

`MemoryTool` enables working, episodic, and semantic memory by default, so complete initialization needs the `rag` dependencies, embeddings, and Qdrant. Qdrant runs as an external service and defaults to `localhost:6333` when `QDRANT_URL` is unset.

SQLite files are written to `memory_data/` by default. That directory, `knowledge_base/`, and `data_science_kb/` are Git-ignored local plaintext runtime data; store sensitive information in separate protected storage.

## 10. Knowledge and state layer: RAG flow

The main RAG path is:

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

Prerequisites:

- Install `rag`; add `doc` for PDF parsing. For other formats, install the dependencies required by the relevant MarkItDown integration and verify the result.
- Start or configure Qdrant and align collection vector dimensions with the embedding model.
- Configure a local embedding directory or a hosted embedding service.
- Configure a valid `LingyeLLM` endpoint. `RAGTool` currently creates its LLM client unconditionally during construction, so this configuration is required even for add/search-only usage.

A valid minimal construction and lower-call-cost retrieval example:

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

Constructing `RAGTool` initializes its directory, embeddings, Qdrant, and an LLM. Advanced retrieval uses Multi-Query or HyDE expansion; the `ask` action calls the LLM after retrieval to generate an answer.

`RAGTool.run(parameters)` dispatches on `action`: `add_document` and `add_text` write to the knowledge base, `search` returns retrieval results, `ask` generates an answer after retrieval, `stats` returns namespace statistics, and `clear` clears a namespace. Callers provide filesystem permissions, namespace isolation, and confirmation around write and clear actions.

## 11. Protocol layer: MCP integration

After installing the `mcp` extra, the framework can connect to in-memory, stdio, HTTP, or SSE MCP servers and can expose tools through its FastMCP server wrapper.

A source checkout can explicitly reference the root configuration:

~~~python
from lingye_agent.tools import MCPTool

tool = MCPTool.from_config(
    "tavily",
    config_path="config/mcp_servers.json",
)
~~~

Run this example from the repository root and prepare Node.js/npm, the selected npm package, `TAVILY_API_KEY`, and network access. Wheel users provide their own config path or pass `server_command` / `server_url` directly.

Security boundaries:

- When `env` is omitted, the current stdio MCP client passes the complete process environment to the child. For third-party servers, construct an environment containing only the system variables and credentials needed by that runtime.
- The filesystem server in the root config exposes its starting directory `.` by default. Start it from a least-privilege directory rather than exposing an entire repository or user directory.
- HTTP / SSE MCP sends call arguments to a remote service. Review the server, authentication method, and data policy first.

## 12. Runtime events and lifecycle

`lingye_agent.core.streaming` provides `StreamEvent`, SSE/JSON Lines conversion, and buffering types. `core.lifecycle` provides events, execution contexts, and hook types. Each agent uses these primitives according to its execution model.

Streaming behavior by agent:

- `SimpleAgent.stream_run()` incrementally consumes normal model text.
- `FunctionCallAgent.stream_run()` currently completes synchronous execution and then yields the final result once.
- `ReflectionAgent.arun_stream()` wraps synchronous `run()` with start / finish / error events.
- Other agents use synchronous `run()` as their primary entry point.

Before integrating WebSocket or SSE, validate the selected agent specifically rather than inferring behavior from the event primitives alone.

## 13. Extension interface contracts

### Add an agent

Subclass `Agent` and implement `run()`. A new strategy should explicitly define:

1. How it organizes the system prompt, history, and current input.
2. Whether it calls `optimize_for_cache`.
3. Its tool protocol, argument validation, and maximum iteration count.
4. When it writes `_history` and whether failures preserve intermediate state.
5. What its synchronous, asynchronous, and streaming methods each guarantee.

### Add a tool

Prefer `Tool` plus `ToolParameter` for structured arguments. Use `register_function()` only for simple string transformations. For command, file, network, or database writes, enforce permissions, timeouts, retries, and side-effect policy in the host application instead of relying on model instructions.

### Add a memory type or storage backend

A new memory type subclasses `BaseMemory` and joins the construction flow in `MemoryManager`. Document storage uses the existing abstraction; replacing vector or graph storage also updates the built-in memory composition around SQLite, Qdrant, or Neo4j. Define the authoritative data source, index-failure behavior, cleanup semantics, and multi-user isolation, and verify persistence through the business store's receipt.

The project extends agents, tools, and memory through explicit inheritance and composition.

## 14. Examples and repository integration

| File | Composition demonstrated | Main prerequisites |
|---|---|---|
| [`PDF_learning_assistant.py`](../examples/PDF_learning_assistant.py) | PDF, RAG, Memory, Gradio | Source checkout; `rag,doc,ui`; `gradio>=6`; model, embeddings, Qdrant |
| [`codebase_maintainer.py`](../examples/codebase_maintainer.py) | Tools, Working Memory, GSSC, and codebase analysis | `nlp`; model; trusted workspace and command permissions |
| [`project_assistant.py`](../examples/project_assistant.py) | NoteTool, Memory, RAG, and GSSC composition design | `rag,nlp`; model, embeddings, Qdrant; local notes directory; adapt NoteTool string outputs into GSSC packets before running |
| [`doc_assistant.py`](../examples/doc_assistant.py) | Sequential composition of two agents and two MCP tools | `mcp`, Node.js/npm, GitHub token, model, and network; its filesystem MCP currently uses `.`, so start from a constrained cwd or change the path first |
| [`tavily_search.py`](../examples/tavily_search.py) | MCP search | `mcp`, Node.js/npm, Tavily key, network; the current script must also point `from_config` at the root config explicitly |

Launch the PDF interface from the source root:

~~~bash
python -m pip install -e ".[rag,doc,ui]" "gradio>=6"
python examples/PDF_learning_assistant.py
~~~

The interface uses `http://127.0.0.1:7860` by default. Install `gradio>=6` to match the example's Gradio 6 message structure. Initializing the assistant connects to the model, embeddings, and Qdrant.

~~~text
lingye_agent/
├── agents/       # Six agent execution strategies
├── cache/        # Request-prefix and tool-schema stabilization
├── context/      # GSSC context construction
├── core/         # Agent, LLM, messages, configuration, and event primitives
├── memory/       # Memory types, RAG, and storage adapters
├── protocols/    # MCP client and server wrappers
└── tools/        # Tools, registry, chains, and executors

examples/         # Source-level integration examples
tests/            # Unit tests and external-service scenarios
config/           # Non-secret templates used from a source workspace
~~~

## 15. Security and data boundaries

- Never commit `.env`, API keys, databases, indexes, knowledge-base contents, model weights, or user data.
- Model, embedding, search, and remote MCP services can receive prompts, retrieved passages, or tool arguments. The host application owns data redaction and multi-tenant authorization.
- `TerminalTool` executes with the current process permissions; the host environment provides operating-system isolation.
- MCP stdio children and third-party npm/Python packages create new trust boundaries. Review package provenance and minimize their environment.
- SQLite runtime data is stored as plaintext. Sensitive deployments need host-provided disk encryption, access control, backups, and deletion policies.
- The default `memory_data/`, `knowledge_base/`, and `data_science_kb/` paths are Git-ignored, but examples can also generate `<project>_notes/`, `<project>_kb/`, `report.md`, `learning_report_*.json`, or `maintainer_report_*.json` in the current directory. Those paths are not guaranteed to match existing ignore rules. Run outside the repository or add exact local ignore rules first.
- Tool iteration limits control loops; host applications also configure call budgets, rate limits, and cost caps.

## 16. Validation and troubleshooting

Run the following commands from the source-checkout root after installing `python -m pip install -e ".[dev]"`. Offline fast release checks:

~~~bash
python -m pytest -q tests/test_release_contract.py tests/test_function_call_agent_unit.py tests/test_simple_calculator.py::test_calculator_tool
~~~

Build and inspect artifacts:

~~~bash
python -m build
python -m twine check dist/*.whl dist/*.tar.gz
python scripts/verify_release_artifact.py dist/lingye_agent-0.1.0-py3-none-any.whl
~~~

Twine checks only the wheel and sdist shown above; handle `SHA256SUMS` separately as a checksum file.

Full suite:

~~~bash
python -m pytest
~~~

The full suite includes slow initialization and scenarios involving models, Qdrant, Neo4j, MCP, search providers, or local test servers. Some can make real network requests, incur provider charges, or write to external systems; review the selected tests first and use isolated least-privilege credentials. Fast checks cover the release contract and a small set of offline unit paths; verify each real external integration separately.

| Symptom | Check first |
|---|---|
| Importing `lingye_agent.context` fails with a jieba error | Install the `nlp` extra |
| `MemoryTool` initialization fails | `rag` extra, embedding config, Qdrant at `localhost:6333`, or `QDRANT_URL` |
| `RAGTool` initialization fails | Model endpoint / LLM configuration, plus the `rag`, embedding, and Qdrant prerequisites |
| The model never calls a tool | Whether the endpoint supports native tool calling; tool schemas and `tool_choice` |
| The MCP config file is missing | In source, pass `config_path="config/mcp_servers.json"`; wheel users provide their own path |
| MCP stdio does not start | Whether Python/Node/npx is on PATH; third-party package, arguments, and minimal environment |
| The Gradio example does not start | Whether you use a source checkout and installed every extra and service required by that example |

When filing an issue, include the Python version, operating system, installed extras, a minimal reproduction, complete traceback, and exact external-service state after removing every secret and private datum.
