from datetime import datetime

import pytest
from dotenv import load_dotenv

load_dotenv()


def test_context_aware_agent():
    """测试 ContextAwareAgent 上下文感知对话"""
    pytest.importorskip("qdrant_client", reason="qdrant-client 未安装，跳过")

    from lingye_agent.agents import ContextAwareAgent
    from lingye_agent.core import LingyeLLM

    llm = LingyeLLM()

    agent = ContextAwareAgent(
        name="数据分析顾问",
        llm=llm,
        system_prompt="你是一位资深的Python数据工程顾问。",
        user_id=f"ling_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        knowledge_base_path="./data_science_kb",
    )

    response = agent.run("如何优化Pandas的内存占用")
    print(f"答1：{response}\n")
    assert isinstance(response, str) and len(response) > 0

    response = agent.run("基于刚才的回答，我应该先做什么优化？")
    print(f"答2：{response}\n")
    assert isinstance(response, str) and len(response) > 0

    response = agent.run("我刚才问了什么问题？")
    print(f"答3：{response}\n")
    assert isinstance(response, str) and len(response) > 0


if __name__ == "__main__":
    test_context_aware_agent()