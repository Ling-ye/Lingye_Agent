import re
import tempfile

from dotenv import load_dotenv

from lingye_agent.tools import NoteTool

load_dotenv()


def _parse_note_id(create_result: str) -> str:
    m = re.search(r"ID:\s*(note_\S+)", create_result)
    if not m:
        raise ValueError(f"无法从创建结果解析 note_id: {create_result!r}")
    return m.group(1)


with tempfile.TemporaryDirectory() as workspace:
    notes = NoteTool(workspace=workspace, auto_backup=False)

    print("=== 测试1: 创建笔记 ===")
    create_out = notes.run(
        {
            "action": "create",
            "title": "重构项目 - 第一阶段",
            "content": """## 完成情况
持久化层与迁移脚本已联调通过，相关单元测试全部绿灯。

## 下一步
重构业务逻辑层""",
            "note_type": "task_state",
            "tags": ["refactoring", "phase1"],
        }
    )
    print(create_out)
    note_id = _parse_note_id(create_out)
    print(f"解析得到 note_id: {note_id}\n")

    print("=== 测试2: 读取笔记 ===")
    print(notes.run({"action": "read", "note_id": note_id}))
    print()

    print("=== 测试3: 按类型列出 ===")
    print(notes.run({"action": "list", "note_type": "task_state", "limit": 10}))
    print()

    print("=== 测试4: 关键词搜索 ===")
    print(notes.run({"action": "search", "query": "业务逻辑", "limit": 10}))
    print()

    print("=== 测试5: 更新笔记 ===")
    print(
        notes.run(
            {
                "action": "update",
                "note_id": note_id,
                "title": "重构项目 - 第一阶段（已更新）",
                "content": "业务逻辑层重构进行中。",
            }
        )
    )
    print()

    print("=== 测试6: 摘要统计 ===")
    print(notes.run({"action": "summary"}))
    print()

    print("=== 测试7: 删除笔记 ===")
    print(notes.run({"action": "delete", "note_id": note_id}))
    print()

    print("=== 测试8: 删除后列表 ===")
    print(notes.run({"action": "list", "limit": 10}))
