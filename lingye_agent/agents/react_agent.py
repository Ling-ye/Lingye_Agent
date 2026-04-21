"""ReAct Agent实现 - 推理与行动结合的智能体"""

import json
import re
from typing import Optional, List, Dict, Any, Tuple
from ..cache import optimize_for_cache
from ..core import Agent, LingyeLLM, Config, Message
from ..tools import ToolRegistry

# 系统提示词模板（不含 question / history，构成稳定前缀以最大化 prompt cache 命中）
REACT_SYSTEM_TEMPLATE = """你是模仿钉宫理惠的傲娇的AI助手。你可以通过思考分析问题，然后调用合适的工具来获取信息，最终给出准确的答案。

## 可用工具
{tools}

## 工作流程
请严格按照以下格式进行回应，每次只能执行一个步骤：

**Thought:** 分析当前问题，思考需要什么信息或采取什么行动。
**Action:** 选择一个行动，格式必须是以下之一：
- `{{tool_name}}[{{tool_input}}]` - 调用指定工具
- `Finish[最终答案]` - 当你有足够信息给出最终答案时

## 重要提醒
1. 每次回应必须包含Thought和Action两部分
2. 工具调用的格式必须严格遵循：工具名[参数]
3. 只有当你确信有足够信息回答问题时，才使用Finish
4. 如果工具返回的信息不够，继续使用其他工具或相同工具的不同参数"""

# 用户提示词模板（仅含当前问题，每次 run 仅出现一次）
REACT_USER_TEMPLATE = "**Question:** {question}\n\n现在开始你的推理和行动。"

# 兼容旧 import：保留原变量名
DEFAULT_REACT_PROMPT = REACT_SYSTEM_TEMPLATE + "\n\n## 当前任务\n" + REACT_USER_TEMPLATE

class ReActAgent(Agent):
    """
    ReAct (Reasoning and Acting) Agent
    
    结合推理和行动的智能体，能够：
    1. 分析问题并制定行动计划
    2. 调用外部工具获取信息
    3. 基于观察结果进行推理
    4. 迭代执行直到得出最终答案
    
    这是一个经典的Agent范式，特别适合需要外部信息的任务。
    """
    
    def __init__(
        self,
        name: str,
        llm: LingyeLLM,
        tool_registry: ToolRegistry,
        system_prompt: Optional[str] = None,
        config: Optional[Config] = None,
        max_steps: int = 5,
        custom_prompt: Optional[str] = None
    ):
        """
        初始化ReActAgent

        Args:
            name: Agent名称
            llm: LLM实例
            tool_registry: 工具注册表
            system_prompt: 系统提示词
            config: 配置对象
            max_steps: 最大执行步数
            custom_prompt: 自定义提示词模板
        """
        super().__init__(name, llm, system_prompt, config)
        self.tool_registry = tool_registry
        self.max_steps = max_steps
        self.current_history: List[str] = []

        # 设置提示词模板：用户自定义优先，否则使用默认模板
        self.prompt_template = custom_prompt if custom_prompt else DEFAULT_REACT_PROMPT
        # cache 友好的拆分模板（system 段常驻、user 段每轮变化）
        self.system_template = REACT_SYSTEM_TEMPLATE
        self.user_template = REACT_USER_TEMPLATE
    
    def run(self, input_text: str, **kwargs) -> str:
        """
        运行ReAct Agent
        
        Args:
            input_text: 用户问题
            **kwargs: 其他参数
            
        Returns:
            最终答案
        """
        self.current_history = []
        current_step = 0
        
        print(f"\n🤖 {self.name} 开始处理问题: {input_text}")

        # 构建稳定前缀：system 段在 run 期间不变，question 仅出现一次在第一条 user 中
        tools_desc = self.tool_registry.get_tools_description()
        system_text = self.system_template.format(tools=tools_desc)
        user_text = self.user_template.format(question=input_text)
        messages: List[Dict[str, Any]] = [
            {"role": "system", "content": system_text},
            {"role": "user", "content": user_text},
        ]

        while current_step < self.max_steps:
            current_step += 1
            print(f"\n--- 第 {current_step} 步 ---")

            # 调用LLM（前缀稳定，仅末尾追加；optimize_for_cache 做最终规范化）
            cached_messages, _ = optimize_for_cache(messages)
            response_text = self.llm.invoke(cached_messages, **kwargs)
            
            if not response_text:
                print("❌ 错误：LLM未能返回有效响应。")
                break

            messages.append({"role": "assistant", "content": response_text})

            # 解析输出
            thought, action = self._parse_output(response_text)
            
            if thought:
                print(f"🤔 思考: {thought}")
            
            if not action:
                print("⚠️ 警告：未能解析出有效的Action，流程终止。")
                break
            
            # 检查是否完成
            if action.startswith("Finish"):
                final_answer = self._parse_action_input(action)
                print(f"🎉 最终答案: {final_answer}")
                
                # 保存到历史记录
                self.add_message(Message(input_text, "user"))
                self.add_message(Message(final_answer, "assistant"))
                
                return final_answer
            
            # 执行工具调用
            tool_name, tool_input = self._parse_action(action)
            if not tool_name or tool_input is None:
                messages.append({"role": "user", "content": "Observation: 无效的Action格式，请按 工具名[参数] 重试。"})
                self.current_history.append("Observation: 无效的Action格式，请检查。")
                continue
            
            print(f"🎬 行动: {tool_name}[{tool_input}]")
            
            # 调用工具（优先结构化参数，兼容纯文本）
            tool_input_text, parameters = self._parse_tool_input(tool_input)
            observation = self.tool_registry.execute_tool(
                tool_name,
                input_text=tool_input_text,
                parameters=parameters
            )
            print(f"👀 观察: {observation}")
            
            # 更新历史
            messages.append({"role": "user", "content": f"Observation: {observation}"})
            self.current_history.append(f"Action: {action}")
            self.current_history.append(f"Observation: {observation}")
        
        print("⏰ 已达到最大步数，流程终止。")
        final_answer = "抱歉，我无法在限定步数内完成这个任务。"
        
        # 保存到历史记录
        self.add_message(Message(input_text, "user"))
        self.add_message(Message(final_answer, "assistant"))
        
        return final_answer
    
    def _parse_output(self, text: str) -> Tuple[Optional[str], Optional[str]]:
        """解析LLM输出，提取思考和行动"""
        thought_match = re.search(r"Thought: (.*)", text)
        action_match = re.search(r"Action: (.*)", text)
        
        thought = thought_match.group(1).strip() if thought_match else None
        action = action_match.group(1).strip() if action_match else None
        
        return thought, action
    
    def _parse_action(self, action_text: str) -> Tuple[Optional[str], Optional[str]]:
        """解析行动文本，提取工具名称和输入"""
        match = re.match(r"(\w+)\[(.*)\]", action_text)
        if match:
            return match.group(1), match.group(2)
        return None, None
    
    def _parse_action_input(self, action_text: str) -> str:
        """解析行动输入"""
        match = re.match(r"\w+\[(.*)\]", action_text)
        return match.group(1) if match else ""

    def _parse_tool_input(self, tool_input: str) -> Tuple[str, Optional[Dict[str, Any]]]:
        """解析工具输入，返回 (文本输入, 结构化参数)"""
        raw = tool_input.strip()
        if not raw:
            return "", None

        # JSON 参数
        if raw.startswith("{") and raw.endswith("}"):
            try:
                parsed = json.loads(raw)
                if isinstance(parsed, dict):
                    return raw, parsed
            except json.JSONDecodeError:
                pass

        # key=value,key2=value2 参数
        if "=" in raw:
            params: Dict[str, Any] = {}
            for part in raw.split(","):
                if "=" not in part:
                    continue
                key, value = part.split("=", 1)
                key = key.strip()
                value = value.strip()
                if key:
                    params[key] = value
            if params:
                return raw, params

        return raw, None
