from ..context.builder import ContextBuilder, ContextConfig
from ..tools.memory_tool import MemoryTool
from ..tools.rag_tool import RAGTool
from ..core.message import Message
from datetime import datetime



# 1. 初始化工具
memory_tool = MemoryTool(user_id="ling")
rag_tool = RAGTool(knowledge_base_path="./knowledge_base")

# 2. 创建 ContextBuilder
config = ContextConfig(
    max_tokens=3000,
    reserve_ratio=0.2,
    min_relevance=0.2,
    enable_compression=True
)

builder = ContextBuilder(
    memory_tool=memory_tool,
    rag_tool=rag_tool,
    config=config
)

# 3. 准备对话历史
conversation_history = [
    Message(content="我正在开发一个数据分析工具", role="user", timestamp=datetime.now()),
    Message(content="很好!数据分析工具通常需要处理大量数据。您计划使用什么技术栈?", role="assistant", timestamp=datetime.now()),
    Message(content="我打算使用Python和Pandas,已经完成了CSV读取模块", role="user", timestamp=datetime.now()),
    Message(content="不错的选择!Pandas在数据处理方面非常强大。接下来您可能需要考虑数据清洗和转换。", role="assistant", timestamp=datetime.now()),
]

# 4. 添加一些记忆
memory_tool.run({
    "action": "add",
    "content": "用户正在开发数据分析工具,使用Python和Pandas",
    "memory_type": "semantic",
    "importance": 0.8
})

memory_tool.run({
    "action": "add",
    "content": "已完成CSV读取模块的开发",
    "memory_type": "episodic",
    "importance": 0.7
})

# 5. 构建上下文
context = builder.build(
    user_query="如何优化Pandas的内存占用?",
    conversation_history=conversation_history,
    system_instructions="你是一位资深的Python数据工程顾问。你的回答需要:1) 提供具体可行的建议 2) 解释技术原理 3) 给出代码示例"
)

print("=" * 80)
print("构建的上下文:")
print("=" * 80)
print(context)
print("=" * 80)
