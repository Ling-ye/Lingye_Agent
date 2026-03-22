from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Callable, get_type_hints
from pydantic import BaseModel
import inspect
import re


def tool_action(name: str = None, description: str = None):
    """装饰器：标记一个方法为可展开的工具 action

    用法:
        @tool_action("memory_add", "添加新记忆")
        def _add_memory(self, content: str, importance: float = 0.5) -> str:
            '''添加记忆

            Args:
                content: 记忆内容
                importance: 重要性分数
            '''
            ...

    Args:
        name: 工具名称（如果不提供，从方法名自动生成）
        description: 工具描述（如果不提供，从 docstring 提取）
    """
    def decorator(func: Callable):
        func._is_tool_action = True
        func._tool_name = name
        func._tool_description = description
        return func
    return decorator

class ToolParameter(BaseModel):
    """工具参数定义"""
    name: str
    type: str
    description: str
    required: bool = True
    default: Any = None


class Tool(ABC):
    """工具基类"""

    def __init__(self, name: str, description: str, expandable: bool = False):
        """初始化工具

        Args:
            name: 工具名称
            description: 工具描述
            expandable: 是否可展开为多个子工具
        """
        self.name = name
        self.description = description
        self.expandable = expandable

    @abstractmethod
    def run(self, parameters: Dict[str, Any]) -> str:
        """执行工具"""
        pass

    def validate_parameters(self, parameters: Dict[str, Any]) -> bool:
        """验证参数"""
        required_params = [p.name for p in self.get_parameters() if p.required]
        return all(param in parameters for param in required_params)

    @abstractmethod
    def get_parameters(self) -> List[ToolParameter]:
        """获取工具参数定义"""
        pass

    def to_openai_schema(self) -> Dict[str, Any]:
        """转换为 OpenAI function calling schema 格式

        用于 FunctionCallAgent，使工具能够被 OpenAI 原生 function calling 使用

        Returns:
            符合 OpenAI function calling 标准的 schema
        """
        parameters = self.get_parameters()

        # 构建 properties
        properties = {}
        required = []

        for param in parameters:
            # 基础属性定义
            prop = {
                "type": param.type,
                "description": param.description
            }

            # 如果有默认值，添加到描述中（OpenAI schema 不支持 default 字段）
            if param.default is not None:
                prop["description"] = f"{param.description} (默认: {param.default})"

            # 如果是数组类型，添加 items 定义
            if param.type == "array":
                prop["items"] = {"type": "string"}  # 默认字符串数组

            properties[param.name] = prop

            # 收集必需参数
            if param.required:
                required.append(param.name)

        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": properties,
                    "required": required
                }
            }
        }







