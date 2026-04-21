"""Lingye Agent - 模块化 LLM Agent 框架"""

from typing import Any

__version__ = "0.1.0"

from .core import (
    Agent,
    LingyeLLM,
    Message,
    Config,
    LingyeAgentsException,
    LLMException,
    AgentException,
    StreamEvent,
    StreamEventType,
)
from .agents import (
    SimpleAgent,
    FunctionCallAgent,
    ReActAgent,
    PlanAndSolveAgent,
    ReflectionAgent,
)
from .tools import Tool, ToolParameter, ToolRegistry, tool_action
from .cache import optimize_for_cache, sort_tools, normalize_text

__all__ = [
    "__version__",
    # core
    "Agent",
    "LingyeLLM",
    "Message",
    "Config",
    "LingyeAgentsException",
    "LLMException",
    "AgentException",
    "StreamEvent",
    "StreamEventType",
    # agents
    "SimpleAgent",
    "FunctionCallAgent",
    "ReActAgent",
    "PlanAndSolveAgent",
    "ReflectionAgent",
    "ContextAwareAgent",
    # tools
    "Tool",
    "ToolParameter",
    "ToolRegistry",
    "tool_action",
    # cache
    "optimize_for_cache",
    "sort_tools",
    "normalize_text",
]


def __getattr__(name: str) -> Any:
    if name == "ContextAwareAgent":
        from .agents import ContextAwareAgent
        return ContextAwareAgent
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
