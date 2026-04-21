"""Prompt Cache 友好化模块

提供纯函数 `optimize_for_cache`，把任意 messages（和可选 tools）
转成对 Provider 端 Prompt Cache 友好的稳定前缀版本。

典型用法：

```python
from lingye_agent.cache import optimize_for_cache

messages, tools = optimize_for_cache(messages, tools)
response = client.chat.completions.create(model=..., messages=messages, tools=tools)
```
"""

from .optimizer import (
    DEFAULT_VOLATILE_PATTERNS,
    __all__,
    normalize_text,
    optimize_for_cache,
    sort_tools,
)
