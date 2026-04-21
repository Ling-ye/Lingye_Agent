"""Prompt Cache 友好化纯函数

只做一件事：把任意 messages（和可选 tools）变成 cache 友好版本，
让 Provider 端（OpenAI / DeepSeek / Kimi / 智谱 等）的 Prompt Cache
能尽可能命中长前缀。

核心原则：
1. 稳定前缀：system 合并并放最前；tools 字典序排序；schema 内字段顺序固定
2. 去抖：仅在 system 文本里替换易变内容（时间戳/UUID/递增 id）
3. 不动 user 内容：user 文本就是真正的 query，不做任何修改
4. 严格保留 assistant.tool_calls 与紧邻 tool 消息的配对顺序，避免破坏对话语义
"""

from __future__ import annotations

import copy
import logging
import re
import warnings
from typing import Any, Dict, List, Optional, Pattern, Tuple


logger = logging.getLogger(__name__)


DEFAULT_VOLATILE_PATTERNS: List[str] = [
    r"\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:?\d{2})?",
    r"\d{4}-\d{2}-\d{2}",
    r"\d{2}:\d{2}:\d{2}",
    r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}",
    r"\bid=\d+\b",
    r"\btrace[_-]?id=[\w-]+\b",
    r"\brequest[_-]?id=[\w-]+\b",
]


_VOLATILE_PLACEHOLDER = "<VOL>"


_DEFAULT_COMPILED_PATTERNS: List[Pattern[str]] = [re.compile(p) for p in DEFAULT_VOLATILE_PATTERNS]


def _compile_extra_patterns(extra_patterns: Optional[List[str]]) -> List[Pattern[str]]:
    """编译额外正则；非法 pattern 通过 warnings.warn 显式提示并跳过，避免静默失效。"""
    if not extra_patterns:
        return []
    compiled: List[Pattern[str]] = []
    for pattern in extra_patterns:
        try:
            compiled.append(re.compile(pattern))
        except re.error as exc:
            warnings.warn(
                f"[lingye_agent.cache] 忽略非法的 volatile 正则 {pattern!r}: {exc}",
                stacklevel=3,
            )
    return compiled


def normalize_text(text: str, extra_patterns: Optional[List[str]] = None) -> str:
    """把文本中的易变内容（时间戳/UUID/递增 id 等）替换为占位符。

    Args:
        text: 待规范化的文本
        extra_patterns: 额外的正则模式列表，会与 DEFAULT_VOLATILE_PATTERNS 合并；
            非法正则会通过 warnings.warn 提示后跳过，而不是静默吞掉。

    Returns:
        替换后的文本；输入为 None / 空时原样返回
    """
    if not text:
        return text

    result = text
    for pattern in _DEFAULT_COMPILED_PATTERNS:
        result = pattern.sub(_VOLATILE_PLACEHOLDER, result)
    for pattern in _compile_extra_patterns(extra_patterns):
        result = pattern.sub(_VOLATILE_PLACEHOLDER, result)
    return result


def sort_tools(tools: Optional[List[Dict[str, Any]]]) -> Optional[List[Dict[str, Any]]]:
    """按 function.name 字典序排序 tools，并对每个 schema 内 properties 按 key 排序。

    传入 None 直接返回 None；不修改输入对象，返回深拷贝后的新列表。
    """
    if not tools:
        return tools

    sorted_tools = copy.deepcopy(tools)

    def _tool_name(tool: Dict[str, Any]) -> str:
        fn = tool.get("function") or {}
        return fn.get("name") or ""

    sorted_tools.sort(key=_tool_name)

    for tool in sorted_tools:
        fn = tool.get("function")
        if not isinstance(fn, dict):
            continue
        params = fn.get("parameters")
        if not isinstance(params, dict):
            continue
        properties = params.get("properties")
        if isinstance(properties, dict):
            params["properties"] = {k: properties[k] for k in sorted(properties.keys())}
        required = params.get("required")
        if isinstance(required, list):
            params["required"] = sorted(required)

    return sorted_tools


def _prepare_tools(
    tools: Optional[List[Dict[str, Any]]],
    sort_by_name: bool,
) -> Optional[List[Dict[str, Any]]]:
    """根据开关决定排序 / 仅深拷贝；统一处理 None / 空列表的边界。"""
    if not tools:
        return tools
    if sort_by_name:
        return sort_tools(tools)
    return copy.deepcopy(tools)


def _extract_text(content: Any) -> str:
    """从 OpenAI 风格 content 中安全取出纯文本。

    注意：当 content 是多模态 list（如 [{"type":"text",...}, {"type":"image_url",...}]）时，
    本函数只会保留 text 段，**会静默丢弃 image_url / 其他非 text 段**，
    因为 cache 友好化只处理可文本规范化的部分。遇到非 text 段会发出一次 debug log，
    便于排查"为什么我的图片没传进去"。
    """
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: List[str] = []
        dropped = 0
        for item in content:
            if isinstance(item, dict):
                text = item.get("text")
                if text:
                    parts.append(str(text))
                else:
                    dropped += 1
            else:
                text = getattr(item, "text", None)
                if text:
                    parts.append(str(text))
                else:
                    dropped += 1
        if dropped:
            logger.debug(
                "_extract_text 丢弃了 %d 个非文本片段（如 image_url），"
                "这些内容不会进入 cache 友好化后的 system 文本。",
                dropped,
            )
        return "".join(parts)
    return str(content)


def _merge_system_messages(
    messages: List[Dict[str, Any]],
    *,
    strip_volatile: bool,
    extra_volatile_patterns: Optional[List[str]],
) -> Tuple[Optional[Dict[str, Any]], List[Dict[str, Any]]]:
    """把 messages 中**所有** system 消息合并为一条挪到最前。

    注意：本函数并不区分"连续"还是"中间插入"的 system 消息，**全部抽走再合并**，
    其它角色（user / assistant / tool）的相对顺序保持不变，因此
    assistant.tool_calls 与紧邻 tool 消息的配对顺序仍然成立。
    """
    system_parts: List[str] = []
    rest: List[Dict[str, Any]] = []

    for msg in messages:
        if not isinstance(msg, dict):
            rest.append(msg)
            continue
        role = msg.get("role")
        if role == "system":
            text = _extract_text(msg.get("content"))
            if strip_volatile:
                text = normalize_text(text, extra_volatile_patterns)
            if text:
                system_parts.append(text)
        else:
            rest.append(msg)

    if not system_parts:
        return None, rest

    merged_system = {"role": "system", "content": "\n\n".join(system_parts)}
    return merged_system, rest


def optimize_for_cache(
    messages: List[Dict[str, Any]],
    tools: Optional[List[Dict[str, Any]]] = None,
    *,
    sort_tools_by_name: bool = True,
    strip_volatile_in_system: bool = True,
    merge_all_system: bool = True,
    extra_volatile_patterns: Optional[List[str]] = None,
) -> Tuple[List[Dict[str, Any]], Optional[List[Dict[str, Any]]]]:
    """让 messages 与 tools 变成 cache 友好版本，返回 (新 messages, 新 tools)。

    做的事（按顺序）：
    1) 把所有 system 消息合并为一条挪到最前（merge_all_system；不论是否连续）
    2) 仅对 system 内容做去抖正则替换，user/assistant/tool 内容不动
    3) tools 列表按 function.name 字典序排序，schema 内 properties 字段按 key 排序
    4) 严格保留 assistant.tool_calls 与紧邻 tool 消息的配对顺序
    5) 不改写 user 文本

    Args:
        messages: OpenAI 风格 messages 列表
        tools: OpenAI function calling tools schema 列表，可选
        sort_tools_by_name: 是否按 name 字典序排序 tools
        strip_volatile_in_system: 是否对 system 文本去抖
        merge_all_system: 是否把所有 system 消息合并并挪到最前；
            False 则保持原序，仅在 strip_volatile_in_system 为 True 时对 system 去抖
        extra_volatile_patterns: 额外的去抖正则；非法正则会 warnings.warn 提示

    Returns:
        (新 messages, 新 tools)，均为深拷贝/新对象，不影响入参
    """
    new_tools = _prepare_tools(tools, sort_tools_by_name)

    if not messages:
        return [], new_tools

    safe_messages = copy.deepcopy(messages)

    if merge_all_system:
        merged_system, rest = _merge_system_messages(
            safe_messages,
            strip_volatile=strip_volatile_in_system,
            extra_volatile_patterns=extra_volatile_patterns,
        )
        new_messages: List[Dict[str, Any]] = []
        if merged_system is not None:
            new_messages.append(merged_system)
        new_messages.extend(rest)
    elif strip_volatile_in_system:
        new_messages = []
        for msg in safe_messages:
            if isinstance(msg, dict) and msg.get("role") == "system":
                text = _extract_text(msg.get("content"))
                msg["content"] = normalize_text(text, extra_volatile_patterns)
            new_messages.append(msg)
    else:
        new_messages = safe_messages

    return new_messages, new_tools


__all__ = [
    "DEFAULT_VOLATILE_PATTERNS",
    "normalize_text",
    "sort_tools",
    "optimize_for_cache",
]
