# test_async_executor.py
import asyncio

from dotenv import load_dotenv

from ..tools.advanced_search import create_advanced_search_registry
from ..tools.async_executor import AsyncToolExecutor
from ..tools.registry import ToolRegistry
from ..tools.simple_calculate import simple_calculate

load_dotenv()


def _build_registry_minimal() -> ToolRegistry:
    """轻量工具：单测异步封装与并行调度，不访问网络。"""
    registry = ToolRegistry()
    registry.register_function(
        "echo",
        "原样返回",
        lambda s: s,
    )
    registry.register_function(
        "double",
        "字符串重复一次",
        lambda s: s + s,
    )
    return registry


def _build_registry_search_and_calc() -> ToolRegistry:
    """与 test_chain 一致：高级搜索 + simple_calculate，供并行集成测试。"""
    registry = create_advanced_search_registry()
    registry.register_function(
        "simple_calculate",
        "简单的数学计算工具，支持基本运算与 sqrt",
        simple_calculate,
    )
    return registry


def _build_registry_parallel_execution_sample() -> ToolRegistry:
    """
    对应 tools/async_executor.py 里 test_parallel_execution 所假设的注册表
    （advanced_search + simple_calculator）；示例源码里未注册，在测试中补齐。
    """
    registry = create_advanced_search_registry()
    registry.register_function(
        "simple_calculator",
        "简单的数学计算工具，支持基本运算与 sqrt",
        simple_calculate,
    )
    return registry


async def _run_single_async():
    registry = _build_registry_minimal()
    executor = AsyncToolExecutor(registry, max_workers=2)
    result = await executor.execute_tool_async("echo", "ping")
    assert result == "ping"

    print("\n========== AsyncToolExecutor 单工具执行结果 ==========\n")
    print(result)


def test_execute_tool_async():
    """异步执行单个工具，结果与同步 registry 一致。"""
    asyncio.run(_run_single_async())


async def _run_parallel():
    registry = _build_registry_minimal()
    executor = AsyncToolExecutor(registry, max_workers=4)
    tasks = [
        {"tool_name": "echo", "input_data": "a"},
        {"tool_name": "double", "input_data": "b"},
        {"tool_name": "echo", "input_data": "xyz"},
    ]
    results = await executor.execute_tools_parallel(tasks)
    assert results == ["a", "bb", "xyz"]

    print("\n========== AsyncToolExecutor 并行执行结果（顺序与 tasks 一致）==========\n")
    for i, r in enumerate(results, 1):
        print(f"任务 {i}: {r!r}")


def test_execute_tools_parallel():
    """并行多任务，顺序与 tasks 列表一致。"""
    asyncio.run(_run_parallel())


async def _run_parallel_search_and_calc():
    registry = _build_registry_search_and_calc()
    executor = AsyncToolExecutor(registry, max_workers=4)
    tasks = [
        {"tool_name": "advanced_search", "input_data": "Python 3.12 发布年份"},
        {"tool_name": "simple_calculate", "input_data": "2024 - 2010"},
    ]
    results = await executor.execute_tools_parallel(tasks)
    assert len(results) == 2
    assert len(results[0].strip()) > 0, "搜索结果不应为空"
    assert results[1].strip() == "14"

    print("\n========== 并行：搜索结果 ==========\n")
    print(results[0])
    print("\n========== 并行：计算结果 ==========\n")
    print(results[1])


def test_parallel_search_and_calculate():
    """
    并行：真实搜索 + 算术（需配置搜索 API；计算器与搜索独立，便于断言数值）。
    """
    asyncio.run(_run_parallel_search_and_calc())


async def _run_parallel_execution_sample():
    """
    复现 tools/async_executor.test_parallel_execution 的任务列表与执行方式；
    不调用该模块内函数（示例中 registry 为空），此处使用完整注册表以便断言。
    """
    registry = _build_registry_parallel_execution_sample()
    executor = AsyncToolExecutor(registry)
    tasks = [
        {"tool_name": "advanced_search", "input_data": "Python编程"},
        {"tool_name": "advanced_search", "input_data": "机器学习"},
        {"tool_name": "simple_calculator", "input_data": "2 + 2"},
        {"tool_name": "simple_calculator", "input_data": "sqrt(16)"},
    ]
    results = await executor.execute_tools_parallel(tasks)
    assert len(results) == 4
    assert len(results[0].strip()) > 0
    assert len(results[1].strip()) > 0
    assert results[2].strip() == "4"
    assert results[3].strip() == "4.0"

    print("\n========== 与 async_executor.test_parallel_execution 同构的并行结果 ==========\n")
    for i, r in enumerate(results, 1):
        preview = r[:120] + ("..." if len(r) > 120 else "")
        print(f"任务 {i}: {preview}")


def test_parallel_execution_sample():
    """覆盖 tools/async_executor.py 中 test_parallel_execution 示例的行为（任务与工具名一致）。"""
    asyncio.run(_run_parallel_execution_sample())


if __name__ == "__main__":
    # test_execute_tool_async()
    # test_execute_tools_parallel()
    # test_parallel_search_and_calculate()
    test_parallel_execution_sample()
    print("test_async_executor: 全部通过")
