from dotenv import load_dotenv
from lingye_agent.core import LingyeLLM
from lingye_agent.agents import ReflectionAgent

load_dotenv()
llm = LingyeLLM()

# 使用默认通用提示词
general_agent = ReflectionAgent(name="我的反思助手", llm=llm)

# 使用自定义代码生成提示词
code_prompts = {
    "initial": "你是Python专家，请编写函数：{task}",
    "reflect": "请审查代码的算法效率：\n任务：{task}\n代码：{content}",
    "refine": "请根据反馈优化代码：\n任务：{task}\n反馈：{feedback}"
}
# code_agent = ReflectionAgent(
#     name="我的代码生成助手",
#     llm=llm,
#     custom_prompts=code_prompts
# )

# 测试使用
result = general_agent.run("写一篇钉宫理惠的介绍，限制为100字")
print(f"最终结果: {result}")