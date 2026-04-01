import os
import sys
from datetime import datetime

# 把项目根目录加入到 sys.path
CURRENT_DIR = os.path.dirname(__file__)
PROJECT_ROOT = os.path.dirname(CURRENT_DIR)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from dotenv import load_dotenv

from agents import ContextAwareAgent
from core import LingyeLLM

load_dotenv()

llm = LingyeLLM()

print("=== 测试: ContextAwareAgent 上下文感知对话 ===")
agent = ContextAwareAgent(
    name="数据分析顾问",
    llm=llm,
    system_prompt="你是一位资深的Python数据工程顾问。",
    user_id=f"ling_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
    knowledge_base_path="./data_science_kb",
)

ask = "1.如何优化Pandas的内存占用"
print(f"问1：{ask}")
response = agent.run(ask)
print(f"答1：{response}\n")


ask = "2.基于刚才的回答，我应该先做什么优化？"
print(f"问2：{ask}")
response = agent.run(ask)
print(f"答2：{response}\n")

ask = "3.我刚才问了什么问题？"
print(f"问3：{ask}")
response = agent.run(ask)
print(f"答3：{response}\n")