from lingye_agent.agents import FunctionCallAgent
from lingye_agent.tools import create_calculator_registry


class DummyLLM:
    temperature = 0.0
    max_tokens = None
    model = "dummy"


def test_function_call_agent_keeps_tool_descriptions_out_of_system_prompt():
    agent = FunctionCallAgent(
        name="test-agent",
        llm=DummyLLM(),
        tool_registry=create_calculator_registry(),
    )

    system_prompt = agent._get_system_prompt()
    tool_schemas = agent._build_tool_schemas()

    assert "## 可用工具" not in system_prompt
    assert "simple_calculate" not in system_prompt
    assert "羊宫妃那" not in system_prompt
    assert any(schema["function"]["name"] == "simple_calculate" for schema in tool_schemas)
