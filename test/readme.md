# 测试目录说明

本目录包含 Lingye Agent 各模块的功能演示与测试脚本。

## 运行方式

所有测试文件均已内置 `sys.path` 修正，可以在**任意目录**下直接运行，无需额外配置环境变量或切换工作目录。

```bash
# 方式一：在项目根目录运行
python test/test_memory_tool.py

# 方式二：指定绝对路径运行
python D:/Code/Lingye_Agent/test/test_memory_tool.py

# 方式三：使用 -m 方式运行（需在项目根目录）
python -m test.test_memory_tool
```

## 前置条件

- 安装项目依赖（`pip install -r requirements.txt`）
- 在项目根目录配置 `.env` 文件（包含 LLM API Key 等环境变量），需要调用 LLM 的测试脚本会用到

## 测试文件一览

### Tools 测试

| 文件 | 说明 |
|------|------|
| `test_memory_tool.py` | MemoryTool 基础操作：四种记忆类型的增删查改、语义搜索、遗忘与整合 |
| `test_note_tool.py` | NoteTool 笔记工具：创建、读取、搜索、更新、删除笔记 |
| `test_terminal_tool.py` | TerminalTool 终端工具：命令执行、文件浏览、日志分析、安全沙箱、与其他工具联动 |
| `test_simple_calculator.py` | 计算器工具：基本四则运算、sqrt 函数，以及与 SimpleAgent 集成 |
| `test_advanced_search.py` | 高级搜索工具：网络搜索、API 配置检查、与 Agent 集成 |
| `test_async_executor.py` | 异步执行器：单工具异步调用、多工具并行调度 |
| `test_chain.py` | 工具链：搜索 → 计算 → LLM 总结的端到端链式调用 |
| `test_context_builder.py` | 上下文构建器：ContextBuilder 整合记忆、RAG、对话历史生成上下文 |

### Agents 测试

| 文件 | 说明 |
|------|------|
| `test_simple_agent.py` | SimpleAgent：基础对话、工具增强对话、流式响应、动态工具管理 |
| `test_function_call_agent.py` | FunctionCallAgent：LLM 原生 function calling 调用计算器并验证结果 |
| `test_react_agent.py` | ReActAgent：Thought-Action-Observation 循环、数学计算、信息搜索、自定义提示词 |
| `test_reflection_agent.py` | ReflectionAgent：生成 → 反思 → 优化的迭代式写作 |
| `test_plan_solve_agent.py` | PlanAndSolveAgent：问题分解 → 分步执行 → 汇总结果 |
| `test_context_aware_agent.py` | ContextAwareAgent：上下文感知的多轮对话 |
