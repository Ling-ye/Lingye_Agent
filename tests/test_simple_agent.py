from dotenv import load_dotenv
from lingye_agent.core import LingyeLLM
from lingye_agent.tools import ToolRegistry, simple_calculate
from lingye_agent.agents import SimpleAgent

# 加载环境变量
load_dotenv()

# 创建LLM实例
llm = LingyeLLM()

# 测试1:基础对话Agent（无工具）
print("=== 测试1:基础对话 ===")
basic_agent = SimpleAgent(
    name="基础助手",
    llm=llm,
    system_prompt="你是一个傲娇的AI助手，请用钉宫理惠的方式回答问题。"
)

response1 = basic_agent.run("你好，请介绍一下自己")
print(f"基础对话响应: {response1}\n")

# 测试2:带工具的Agent
print("=== 测试2:工具增强对话 ===")

tool_registry = ToolRegistry()
# 注册计算器函数
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

response2 = enhanced_agent.run("请帮我计算 114 * 514 + 1551")
print(f"工具增强响应: {response2}\n")

# 测试3:流式响应
print("=== 测试3:流式响应 ===")
print("流式响应: ", end="")
for chunk in basic_agent.stream_run("请解释什么是人工智能"):
    pass  # 内容已在stream_run中实时打印

# 测试4:动态添加工具
print("\n=== 测试4:动态工具管理 ===")
print(f"添加工具前: {basic_agent.has_tools()}")
basic_agent.add_tool(simple_calculate)
print(f"添加工具后: {basic_agent.has_tools()}")
print(f"可用工具: {basic_agent.list_tools()}")

# 查看对话历史
print(f"\n对话历史: {len(basic_agent.get_history())} 条消息")
