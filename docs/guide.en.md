# Lingye Agent Guide

[Back to the English README](../README.en.md) | [中文指南](guide.zh-CN.md)

## 1. Environment and installation

Lingye Agent supports Python 3.10–3.13. The core installation contains agents, the LLM abstraction, context construction, basic memory, and basic tools. Databases, document parsing, MCP, and UI support are installed through extras.

~~~bash
python -m venv .venv
# Windows PowerShell
.venv\Scripts\Activate.ps1
# Linux / macOS
source .venv/bin/activate

python -m pip install -e ".[dev]"
~~~

For a full local development environment:

~~~bash
python -m pip install -e ".[rag,graph,mcp,nlp,doc,ui,dev]"
~~~

Copy .env.example to .env. Never commit .env files, databases, indexes, model weights, or real credentials.

## 2. LLM configuration

LingyeLLM uses an OpenAI-compatible request format.

| Variable | Purpose |
|---|---|
| LLM_API_KEY | API key for the selected endpoint |
| LLM_BASE_URL | OpenAI-compatible API root |
| LLM_MODEL_ID | Model identifier |
| LLM_TIMEOUT | Request timeout in seconds |
| TEMPERATURE | Default sampling temperature |
| MAX_TOKENS | Default output-token limit |

Provider-specific variables can override the generic settings. For Ollama or vLLM, configure the related host and model identifier.

## 3. Agent patterns

| Agent | Purpose |
|---|---|
| SimpleAgent | Basic conversation and text-oriented tool use |
| FunctionCallAgent | Native model tool/function calling |
| ReActAgent | Alternating reasoning and tool actions |
| PlanAndSolveAgent | Plan first, then solve step by step |
| ReflectionAgent | Generate, evaluate, and revise |
| ContextAwareAgent | Build context from memory and RAG |

All agents extend the core Agent abstraction and combine LingyeLLM, a system prompt, Config, and ToolRegistry. Synchronous, asynchronous, and streaming support varies by agent; inspect the methods on the selected class.

## 4. Tools

ToolRegistry accepts Tool subclasses, registered functions, and methods decorated with tool_action.

~~~python
from lingye_agent import ToolRegistry
from lingye_agent.tools import simple_calculate

registry = ToolRegistry()
registry.register_function(
    name="calculator",
    description="Evaluate a basic arithmetic expression",
    func=simple_calculate,
)

result = registry.execute_tool("calculator", "sqrt(16) + 2 * 3")
print(result)
~~~

Built-in modules include TerminalTool, NoteTool, MemoryTool, RAGTool, MCPTool, AdvancedSearchTool, ToolChain, and AsyncToolExecutor. Tools that execute commands, access the network, or call external services require separate permissions, credentials, and timeout policies.

## 5. Memory and storage

MemoryManager coordinates four memory categories:

- WorkingMemory: short-lived state with capacity and TTL controls.
- EpisodicMemory: time- and session-oriented events.
- SemanticMemory: semantic retrieval through vector or graph data.
- PerceptualMemory: text, image, or audio-related observations.

The SQLite document store creates its database directory at runtime. memory_data, knowledge_base, and data_science_kb are local runtime data and must not be committed.

Qdrant and Neo4j are optional backends. Before enabling them, install the relevant extra and align vector dimensions, collection names, database names, and network settings.

## 6. RAG

RAG components live under lingye_agent.memory.rag and RAGTool. A typical flow parses a document, splits it, creates embeddings, indexes it, retrieves candidates, and optionally reranks them.

~~~python
from lingye_agent.tools import RAGTool

rag = RAGTool(
    name="knowledge",
    description="Project knowledge base",
    knowledge_base_path="./knowledge_base",
)
~~~

Document parsing requires the doc extra. Local embeddings and reranking require the rag extra. Hosted embeddings require provider credentials. In offline mode, set EMBED_MODEL_NAME to an existing local model directory and enable EMBED_OFFLINE.

## 7. MCP

After installing the mcp extra, use MCPTool or the lower-level MCPClient.

~~~python
from lingye_agent.tools import MCPTool

tool = MCPTool.from_config("tavily")
~~~

Server definitions live in config/mcp_servers.json. The client covers in-memory, stdio, HTTP, and SSE scenarios; availability depends on the FastMCP version and server implementation. Reference access tokens through environment variables instead of storing them in JSON.

## 8. Context and cache optimization

ContextBuilder applies the GSSC process to gather, select, structure, and compress conversation history, memory, RAG evidence, and tool results.

~~~python
from lingye_agent.context import ContextBuilder, ContextConfig

builder = ContextBuilder(
    memory_tool=memory_tool,
    rag_tool=rag_tool,
    config=ContextConfig(max_tokens=8000, reserve_ratio=0.15),
)

context = builder.build(
    user_query="Summarize the current task",
    conversation_history=[],
    system_instructions="Use only the supplied evidence",
)
~~~

optimize_for_cache stabilizes system prefixes, tool-schema order, and volatile identifiers while retaining user text and tool-call pairing.

## 9. Streaming and lifecycle hooks

core.streaming provides StreamEvent, StreamEventType, and serialization helpers. core.lifecycle provides AgentEvent, ExecutionContext, and LifecycleHook. Agents expose only the stream_run or arun_stream methods they implement; do not assume a uniform streaming interface across every agent.

## 10. Examples

| File | Scenario |
|---|---|
| examples/PDF_learning_assistant.py | PDF, RAG, and Gradio |
| examples/codebase_maintainer.py | Tools and long-running repository work |
| examples/project_assistant.py | NoteTool and context construction |
| examples/doc_assistant.py | Multi-agent document generation |
| examples/tavily_search.py | MCP search |

Examples can require the all extra, external databases, MCP servers, or API keys. Inspect the imports and .env.example before running an entry point.

## 11. Repository layout

~~~text
lingye_agent/
├── agents/       # Agent patterns
├── cache/        # Stable-prefix and tool-schema optimization
├── context/      # GSSC context construction
├── core/         # Agent, LLM, messages, events, and configuration
├── memory/       # Memory types, RAG, and storage
├── protocols/    # MCP client and server
└── tools/        # Tools, registry, and executors

examples/         # Runnable examples
tests/            # Unit and integration tests
config/           # Non-sensitive configuration templates
~~~

## 12. Validation and limitations

Fast release checks:

~~~bash
python -m pytest -q tests/test_release_contract.py tests/test_function_call_agent_unit.py tests/test_simple_calculator.py::test_calculator_tool
python -m build
python -m twine check dist/*
python scripts/verify_release_artifact.py dist/lingye_agent-0.1.0-py3-none-any.whl
~~~

The full suite includes external services and slower initialization and is not a blocking v0.1.0 gate. When reporting a problem, include the Python version, operating system, installed extras, a minimal reproduction, and the full traceback after removing secrets.
