from dotenv import load_dotenv

from lingye_agent.tools import (
    create_advanced_search_registry,
    ToolChain, ToolChainManager, create_research_calculator_chain,
    ToolRegistry,
    simple_calculate,
)

load_dotenv()


def _build_registry_for_research_chain(*, fixed_calc_expr: str) -> ToolRegistry:
    """
    供 create_research_calculator_chain 使用：advanced_search + simple_calculator。

    链内第二步会把「根据以下信息…」+ 整段搜索结果交给计算器，simple_calculate 无法解析自然语言。
    在不改 chain 的前提下，测试中 simple_calculator 忽略入参，只对 fixed_calc_expr 求值以验证链路。
    """
    registry = create_advanced_search_registry()

    def simple_calculator_stub(_tool_input: str) -> str:
        return simple_calculate(fixed_calc_expr)

    registry.register_function(
        "simple_calculator",
        "测试桩：忽略链传入的长文本，仅计算固定表达式",
        simple_calculator_stub,
    )
    return registry


def _build_registry_for_search_calc_summarize(llm) -> ToolRegistry:
    """在高级搜索注册表上追加 simple_calculate 与调用 LingyeLLM.invoke 的总结工具。"""

    def llm_summarize(prompt: str) -> str:
        messages = [{"role": "user", "content": prompt}]
        return llm.invoke(messages)

    registry = create_advanced_search_registry()
    registry.register_function(
        "simple_calculate",
        "简单的数学计算工具，支持基本运算与 sqrt",
        simple_calculate,
    )
    registry.register_function(
        "llm_summarize",
        "根据搜索结果与计算结果生成中文总结",
        llm_summarize,
    )
    return registry


def test_chain_search_calculate_summarize_llm():
    """
    端到端：搜索 -> 计算 -> 大模型总结（真实调用搜索 API 与 LLM）。

    计算步骤通过 context 传入表达式（例如年份差），与搜索主题解耦，便于稳定跑通计算器。
    """
    from core import LingyeLLM

    try:
        llm = LingyeLLM()
    except Exception as e:
        print(f"跳过：无法初始化 LLM（请配置 .env 中的 LLM 相关变量）: {e}")
        return

    registry = _build_registry_for_search_calc_summarize(llm)

    chain = ToolChain(
        "search_calc_summarize",
        "搜索 -> 计算 -> LLM 总结",
    )
    chain.add_step("advanced_search", "{input}", "search_result")
    chain.add_step("simple_calculate", "{calc_expr}", "calculation_result")
    chain.add_step(
        "llm_summarize",
        (
            "请根据下列「搜索结果」与「计算结果」，用一段话（200 字以内）做中文总结，语言简洁，要求必须按照如下格式输出。\n\n"
            "【搜索结果】\n{search_result}\n\n"
            "【计算结果】\n{calculation_result}"
        ),
        "final_summary",
    )

    user_query = "Python 3.12 发布年份与主要新特性"
    calc_expr = "2026 - 1999"

    result = chain.execute(
        registry,
        user_query,
        context={"calc_expr": calc_expr},
    )

    assert isinstance(result, str)
    assert len(result.strip()) > 0, "总结结果不应为空"

    print("\n========== 工具链最终输出（LLM 总结）==========\n")
    print(result)


if __name__ == "__main__":
    test_chain_search_calculate_summarize_llm()
