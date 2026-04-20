"""Agent 模块"""

from typing import TYPE_CHECKING, Any

from .simple_agent import SimpleAgent
from .function_call_agent import FunctionCallAgent
from .plan_solve_agent import Planner, Executor, PlanAndSolveAgent
from .react_agent import ReActAgent
from .reflection_agent import ReflectionAgent

if TYPE_CHECKING:
    from .context_aware_agent import ContextAwareAgent

__all__ = [
    "SimpleAgent",
    "FunctionCallAgent",
    "Planner",
    "Executor",
    "PlanAndSolveAgent",
    "ReActAgent",
    "ReflectionAgent",
    "ContextAwareAgent",
]


def __getattr__(name: str) -> Any:
    if name == "ContextAwareAgent":
        from .context_aware_agent import ContextAwareAgent
        return ContextAwareAgent
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
