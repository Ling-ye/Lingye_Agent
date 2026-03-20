import os
import re
import sys
from typing import Optional
from dotenv import load_dotenv

# 把项目父目录加入到 sys.path
CURRENT_DIR = os.path.dirname(__file__)
PROJECT_ROOT = os.path.dirname(CURRENT_DIR)  
PARENT_DIR = os.path.dirname(PROJECT_ROOT)  
if PARENT_DIR not in sys.path:
    sys.path.insert(0, PARENT_DIR)

from ..agents.function_call_agent import FunctionCallAgent
from ..core.exceptions import LingyeAgentsException
from ..core.llm import LingyeLLM
from ..tools.simple_calculate import create_calculator_registry, simple_calculate

load_dotenv()


def _extract_number(text: str) -> Optional[str]:
    """
    从输出文本里提取数字（支持整数/小数/科学计数法的粗略场景）。
    如果模型严格输出“纯数字”，则会直接命中整段。
    """
    if not text:
        return None
    # 提取最后一个看起来像数字的片段，降低“表达式中的数字”误伤概率
    matches = re.findall(r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?", text)
    if not matches:
        return None
    return matches[-1]


def test_real_function_call_agent(expression: str) -> None:
    """
    要求模型调用工具 `my_calculator` 来计算 expression，并最终输出结果数字。
    """

    expected = simple_calculate(expression)
    expected_str = str(expected).strip()
    print(f"本地计算器输出的计算结果为{expected_str}")

    llm = LingyeLLM(temperature=0.0, max_tokens=64)

    client = getattr(llm, "_client", None)
    if client is not None:
        create_fn = getattr(getattr(getattr(client, "chat", None), "completions", None), "create", None)
        if callable(create_fn):
            _orig_create = create_fn

            def _debug_create(**kwargs):
                tool_choice = kwargs.get("tool_choice")
                tools = kwargs.get("tools")
                msgs = kwargs.get("messages") or []
                print(
                    f"[DEBUG] create(): tool_choice={tool_choice!r}, tools_count={len(tools) if tools else 0}, messages_count={len(msgs)}"
                )
                resp = _orig_create(**kwargs)
                try:
                    msg = resp.choices[0].message
                    content = getattr(msg, "content", None)
                    tool_calls = getattr(msg, "tool_calls", None) or []
                    tc_names = []
                    for tc in tool_calls:
                        fn = getattr(tc, "function", None)
                        tc_names.append(getattr(fn, "name", None))
                    content_len = len(content) if isinstance(content, str) else 0
                    print(
                        f"[DEBUG] create() -> content_len={content_len}; tool_calls={len(tool_calls)}; tool_names={tc_names!r}"
                    )
                    if (not content) and tool_calls:
                        first = tool_calls[0]
                        fn = getattr(first, "function", None)
                        args = getattr(fn, "arguments", None)
                        print(f"[DEBUG] first tool_call arguments={args!r}")
                except Exception as _e:
                    print(f"[DEBUG] failed to summarize response: {type(_e).__name__}: {_e}")
                return resp

            client.chat.completions.create = _debug_create  # type: ignore

    tool_registry = create_calculator_registry()  # register_function: my_calculator(input: str)

    system_prompt = (
        "你是一个严格的计算助手。\n"
        "必须先使用工具 my_calculator 计算表达式，然后把最终结果作为纯数字输出。\n"
        "禁止输出除结果之外的任何文字。"
    )

    agent = FunctionCallAgent(
        name="function-call-real-test",
        llm=llm,
        tool_registry=tool_registry,
        enable_tool_calling=True,
        max_tool_iterations=5,
        system_prompt=system_prompt,
    )

    user_question = f"计算表达式: {expression}"
    out = agent.run(user_question)

    out_norm = (out or "").strip()
    extracted = _extract_number(out_norm)
    print(f"agent输出的计算结果为{extracted}")

    ok = False
    if expected_str and expected_str in out_norm.replace(" ", ""):
        ok = True
    elif extracted is not None:
        try:
            ok = float(extracted) == float(expected_str)
        except Exception:
            ok = False

    if not ok:
        raise AssertionError(
            f"结果不匹配。\nexpression={expression!r}\nexpected={expected_str!r}\noutput={out_norm!r}\nextracted={extracted!r}"
        )
    else:
        print(f"测试通过：{expression}")


def run_all_tests() -> None:
    str="114 * 514 + 1551"
    print(f"\n测试计算：{str}")
    test_real_function_call_agent(f"{str}")

    str="sqrt(16)"
    print(f"\n测试计算：{str}")
    test_real_function_call_agent(f"{str}")


if __name__ == "__main__":
    try:
        run_all_tests()
    except LingyeAgentsException as e:
        print(f"[ERROR] Environment/LLM configuration error: {e}")
        print("请检查是否已配置 .env 或环境变量（例如 OPENAI_API_KEY/LLM_BASE_URL/LLM_MODEL_ID 等）。")
        raise
    except Exception as e:
        print(f"[ERROR] Test failed: {e}")
        raise
