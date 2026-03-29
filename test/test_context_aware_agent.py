import os
import sys

# 把项目根目录加入到 sys.path
CURRENT_DIR = os.path.dirname(__file__)
PROJECT_ROOT = os.path.dirname(CURRENT_DIR)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from dotenv import load_dotenv

from ..agents.context_aware_agent import ContextAwareAgent
from ..core.llm import LingyeLLM

load_dotenv()

llm = LingyeLLM()

print("=== 测试: ContextAwareAgent 上下文感知对话 ===")
agent = ContextAwareAgent(
    name="数据分析顾问",
    llm=llm,
    system_prompt="你是一位资深的Python数据工程顾问。",
    user_id="ling",
    knowledge_base_path="./data_science_kb",
)

ask = "如何优化Pandas的内存占用"
print(f"问：{ask}")
response = agent.run(ask)
print(f"答：{response}\n")
