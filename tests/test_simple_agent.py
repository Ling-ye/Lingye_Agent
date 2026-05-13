from dotenv import load_dotenv
from lingye_agent.core import LingyeLLM
from lingye_agent.tools import ToolRegistry, simple_calculate
from lingye_agent.agents import SimpleAgent

load_dotenv()


def test_basic_conversation():
    """测试1: 基础对话Agent（无工具）"""
    llm = LingyeLLM()
    basic_agent = SimpleAgent(
        name="基础助手",
        llm=llm,
        system_prompt="你是一个傲娇的AI助手，请用钉宫理惠的方式回答问题。"
    )

    response = basic_agent.run("你好，请介绍一下自己")
    print(f"基础对话响应: {response}\n")
    assert isinstance(response, str) and len(response) > 0


def test_tool_enhanced_conversation():
    """测试2: 带工具的Agent"""
    llm = LingyeLLM()
    tool_registry = ToolRegistry()
    tool_registry.register_function(
        name="simple_calculator",
        description="简单的数学计算工具，支持基本运算(+,-,*,/)和sqrt函数",
        func=simple_calculate
    )

    enhanced_agent = SimpleAgent(
        name="增强助手",
        llm=llm,
        system_prompt="你是一个智能助手，可以使用工具来帮助用户。",
        tool_registry=tool_registry,
        enable_tool_calling=True
    )

    response = enhanced_agent.run("请帮我计算 114 * 514 + 1551")
    print(f"工具增强响应: {response}\n")
    assert isinstance(response, str) and len(response) > 0


def test_stream_run():
    """测试3: 流式响应"""
    llm = LingyeLLM()
    agent = SimpleAgent(
        name="流式助手",
        llm=llm,
        system_prompt="你是一个傲娇的AI助手。"
    )

    chunks = list(agent.stream_run("请解释什么是人工智能"))
    assert len(chunks) > 0


def test_dynamic_tool_management():
    """测试4: 动态工具管理"""
    llm = LingyeLLM()
    agent = SimpleAgent(name="测试助手", llm=llm)

    assert not agent.has_tools()

    tool_registry = ToolRegistry()
    tool_registry.register_function(
        name="simple_calculator",
        description="简单的数学计算工具",
        func=simple_calculate
    )
    agent.tool_registry = tool_registry
    agent.enable_tool_calling = True

    assert agent.has_tools()
    assert "simple_calculator" in agent.list_tools()
    print(f"可用工具: {agent.list_tools()}")


if __name__ == "__main__":
    test_basic_conversation()
    test_tool_enhanced_conversation()
    test_stream_run()
    test_dynamic_tool_management()
    print("\n所有测试完成！")
