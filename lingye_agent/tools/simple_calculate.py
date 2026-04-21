import ast
import operator
import math
from .registry import ToolRegistry

def simple_calculate(expression: str) -> str:
    """简单的数学计算函数"""
    if not expression.strip():
        return "计算表达式不能为空"

    # 支持的基本运算
    operators = {
        ast.Add: operator.add,      # +
        ast.Sub: operator.sub,      # -
        ast.Mult: operator.mul,     # *
        ast.Div: operator.truediv,  # /
        ast.Pow: operator.pow,      # **
        ast.Mod: operator.mod,      # %
        ast.USub: operator.neg,     # unary -
        ast.UAdd: operator.pos,     # unary +
    }

    # 支持的基本函数
    functions = {
        'sqrt': math.sqrt,
        'pi': math.pi,
    }

    try:
        node = ast.parse(expression, mode='eval')
        result = _eval_node(node.body, operators, functions)
        return str(result)
    except Exception as e:
        return f"计算失败: {e}"

def _eval_node(node, operators, functions):
    """简化的表达式求值"""
    if isinstance(node, ast.Constant):
        return node.value
    elif isinstance(node, ast.UnaryOp):
        op = operators.get(type(node.op))
        if op is None:
            raise ValueError(f"不支持的一元运算: {type(node.op).__name__}")
        return op(_eval_node(node.operand, operators, functions))
    elif isinstance(node, ast.BinOp):
        op = operators.get(type(node.op))
        if op is None:
            raise ValueError(f"不支持的运算符: {type(node.op).__name__}")
        left = _eval_node(node.left, operators, functions)
        right = _eval_node(node.right, operators, functions)
        return op(left, right)
    elif isinstance(node, ast.Call):
        if not isinstance(node.func, ast.Name):
            raise ValueError(f"不支持的函数调用形式: {type(node.func).__name__}")
        func_name = node.func.id
        if func_name in functions:
            func = functions[func_name]
            if callable(func):
                args = [_eval_node(arg, operators, functions) for arg in node.args]
                return func(*args)
            raise ValueError(f"'{func_name}' 是常量，不能作为函数调用")
    elif isinstance(node, ast.Name):
        if node.id in functions:
            return functions[node.id]

    raise ValueError(f"不支持的表达式: {type(node).__name__}")

def create_calculator_registry():
    """创建包含计算器的工具注册表"""
    registry = ToolRegistry()

    # 注册计算器函数
    registry.register_function(
        name="simple_calculate",
        description="简单的数学计算工具，支持基本运算(+,-,*,/)和sqrt函数",
        func=simple_calculate
    )

    return registry
