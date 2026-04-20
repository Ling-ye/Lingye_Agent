
from dotenv import load_dotenv
from lingye_agent.core import LingyeLLM

# 加载环境变量
load_dotenv()

llm = LingyeLLM(provider="modelscope", base_url="https://aihubmix.com/v1")

# 准备消息
messages = [{"role": "user", "content": "你好，请介绍一下你自己。"}]

response_stream = llm.think(messages)

# 打印响应
print("ModelScope Response:")
for chunk in response_stream:
    pass