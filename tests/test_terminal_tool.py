import platform
import tempfile
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

from lingye_agent.tools import NoteTool, TerminalTool

load_dotenv()

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

_IS_WIN = platform.system().lower() == "windows"


def _setup_workspace(root: Path) -> None:
    """在临时目录中创建可复现的演示文件结构（含原 doc 中的项目 / 数据 / 日志 / 代码场景）。"""
    (root / "src").mkdir(parents=True, exist_ok=True)
    (root / "src" / "processor.py").write_text(
        "# module\n"
        "def process_data():\n"
        "    return 1\n\n"
        "def other():\n"
        "    pass\n",
        encoding="utf-8",
    )
    (root / "README.md").write_text("# Demo project\n\n用于 TerminalTool 演示。\n", encoding="utf-8")
    (root / "requirements.txt").write_text("requests\n", encoding="utf-8")

    (root / "demo_pkg").mkdir(parents=True, exist_ok=True)
    (root / "demo_pkg" / "sample_target.py").write_text(
        "# sample\n# TODO: add tests\ndef process_orders():\n    pass\n",
        encoding="utf-8",
    )

    (root / "data").mkdir(parents=True, exist_ok=True)
    (root / "data" / "sales_2024.csv").write_text(
        "id,amount,category\n1,10.5,A\n2,20,B\n3,15.5,A\n",
        encoding="utf-8",
    )
    (root / "data" / "sales_2023.csv").write_text(
        "id,amount,category\n1,1,X\n",
        encoding="utf-8",
    )

    (root / "logs").mkdir(parents=True, exist_ok=True)
    (root / "logs" / "app.log").write_text(
        "2024-01-19 14:00 INFO start\n"
        "2024-01-19 15:00 ERROR DatabaseConnectionError conn reset\n"
        "2024-01-19 15:01 ERROR TimeoutException deadline\n"
        "2024-01-19 15:02 ERROR DatabaseConnectionError pool exhausted\n"
        "2024-01-19 15:03 ERROR ValidationError bad input\n"
        "2024-01-19 16:00 WARN slow query 120ms on user_table\n"
        "2024-01-19 16:01 WARN slow query 200ms on orders\n",
        encoding="utf-8",
    )


with tempfile.TemporaryDirectory() as workspace:
    ws = Path(workspace)
    _setup_workspace(ws)

    terminal = TerminalTool(workspace=str(ws))

    print("=== 测试1: 列出工作区根目录 ===")
    cmd = "dir" if _IS_WIN else "ls -la"
    print(terminal.run({"command": cmd}))
    print()

    print("=== 测试2: 列出 Python 文件 ===")
    cmd = "dir /s /b *.py" if _IS_WIN else "find . -name '*.py'"
    print(terminal.run({"command": cmd}))
    print()

    print("=== 测试3: 查看文件前几行 ===")
    rel = "demo_pkg/sample_target.py"
    if _IS_WIN:
        cmd = (
            f'powershell -NoProfile -Command "Get-Content -Path \'{rel}\' -TotalCount 5"'
        )
    else:
        cmd = f"head -n 5 {rel}"
    print(terminal.run({"command": cmd}))
    print()

    print("=== 测试4: 查看 CSV 前几行 ===")
    rel_csv = "data/sales_2024.csv"
    if _IS_WIN:
        cmd = (
            f'powershell -NoProfile -Command "Get-Content -Path \'{rel_csv}\' -TotalCount 5"'
        )
    else:
        cmd = f"head -n 5 {rel_csv}"
    print(terminal.run({"command": cmd}))
    print()

    print("=== 测试5: 统计 CSV 行数 ===")
    if _IS_WIN:
        cmd = (
            f'powershell -NoProfile -Command "(Get-Content -Path \'{rel_csv}\').Count"'
        )
    else:
        cmd = f"wc -l {rel_csv}"
    print(terminal.run({"command": cmd}))
    print()

    print("=== 测试6: 日志中过滤 ERROR ===")
    rel_log = "logs/app.log"
    if _IS_WIN:
        cmd = (
            "powershell -NoProfile -Command "
            f"\"Select-String -Path '{rel_log}' -SimpleMatch -Pattern 'ERROR'\""
        )
    else:
        cmd = f"grep ERROR {rel_log}"
    print(terminal.run({"command": cmd}))
    print()

    print("=== 测试7: 在代码中搜索 TODO ===")
    if _IS_WIN:
        cmd = 'findstr /s /n /i "TODO" demo_pkg\\*.py'
    else:
        cmd = "grep -rn 'TODO' --include='*.py' demo_pkg/"
    print(terminal.run({"command": cmd}))
    print()

    print("=== 测试8: 安全 — 拒绝危险命令 (rm) ===")
    print(terminal.run({"command": "rm -rf /"}))
    print()

    print("=== 测试9: 安全 — 绝对路径读文件（shell 仍可能成功，与 cd 沙箱不同）===")
    print(
        terminal.run(
            {
                "command": (
                    "type C:\\Windows\\System32\\drivers\\etc\\hosts"
                    if _IS_WIN
                    else "cat /etc/passwd"
                )
            }
        )
    )
    print()

    print("=== 测试10: 安全 — cd 不可逃逸到工作区外 ===")
    print(terminal.run({"command": "cd .."}))
    print()

    # ---------- 进阶：原使用说明中的探索 / 管道 / 代码分析 ----------
    terminal.reset_dir()

    print("=== 测试11: cd 进入 src 后执行 tree ===")
    print(terminal.run({"command": "cd src"}))
    tree_cmd = "tree /F" if _IS_WIN else "tree"
    print(terminal.run({"command": tree_cmd}))
    terminal.reset_dir()
    print()

    print("=== 测试12: 递归搜索 Python 中的 def process ===")
    if _IS_WIN:
        # /C: 表示整段字面量；否则空格会被当成「或」匹配
        cmd = 'findstr /s /n /i /C:"def process" *.py'
    else:
        cmd = "grep -r 'def process' . --include='*.py'"
    print(terminal.run({"command": cmd}))
    print()

    print("=== 测试13: CSV 类别列统计（跳过表头）===")
    if _IS_WIN:
        cmd = (
            "powershell -NoProfile -Command "
            "\"Import-Csv -Path 'data/sales_2024.csv' | Group-Object category "
            "| Sort-Object Count -Descending "
            "| ForEach-Object { $_.Count.ToString() + ' ' + $_.Name }\""
        )
    else:
        cmd = (
            "tail -n +2 data/sales_2024.csv | cut -d',' -f3 | sort | uniq -c"
        )
    print(terminal.run({"command": cmd}))
    print()

    print("=== 测试14: 日志尾部再筛 ERROR ===")
    if _IS_WIN:
        cmd = (
            "powershell -NoProfile -Command "
            "\"Get-Content 'logs/app.log' -Tail 20 | Select-String 'ERROR'\""
        )
    else:
        cmd = "tail -n 20 logs/app.log | grep ERROR"
    print(terminal.run({"command": cmd}))
    print()

    print("=== 测试15: ERROR 行按第 4 列（异常类型）聚合统计 ===")
    if _IS_WIN:
        cmd = (
            "powershell -NoProfile -Command "
            "\"Select-String -Path 'logs/app.log' -Pattern ' ERROR ' | "
            "ForEach-Object { ($_ -split '\\s+', 5)[3] } | Group-Object | "
            "Sort-Object Count -Descending | "
            "ForEach-Object { $_.Count.ToString().PadLeft(4) + ' ' + $_.Name }\""
        )
    else:
        cmd = (
            "grep ERROR logs/app.log | awk '{print $4}' | sort | uniq -c | sort -rn"
        )
    print(terminal.run({"command": cmd}))
    print()

    print("=== 测试16: 按时间段过滤日志 ===")
    if _IS_WIN:
        cmd = (
            "powershell -NoProfile -Command "
            "\"Select-String -Path 'logs/app.log' -SimpleMatch -Pattern '2024-01-19 15:'\""
        )
    else:
        cmd = "grep '2024-01-19 15:' logs/app.log | tail -n 20"
    print(terminal.run({"command": cmd}))
    print()

    print("=== 测试17: 统计所有 .py 行数合计 ===")
    if _IS_WIN:
        cmd = (
            "powershell -NoProfile -Command "
            "\"(Get-ChildItem -Path . -Filter *.py -Recurse | "
            "Get-Content | Measure-Object -Line).Lines\""
        )
    else:
        cmd = "find . -name '*.py' -exec wc -l {} + | tail -n 1"
    print(terminal.run({"command": cmd}))
    print()

    print("=== 测试18: 定位 def process_data 定义 ===")
    if _IS_WIN:
        cmd = 'findstr /s /n /C:"def process_data" src\\*.py demo_pkg\\*.py'
    else:
        cmd = "grep -rn 'def process_data' --include='*.py' src/ demo_pkg/"
    print(terminal.run({"command": cmd}))
    print()

    print("=== 测试19: sed 截取至下一 def 前（仅 Unix；Windows 跳过）===")
    if _IS_WIN:
        print("(跳过: 典型 sed 管线在 Windows 上依赖额外工具)\n")
    else:
        print(
            terminal.run(
                {
                    "command": (
                        "sed -n '/def process_data/,/^def /p' src/processor.py "
                        "| head -n -1"
                    )
                }
            )
        )
        print()

    print("=== 测试20: 有限深度目录树（src）===")
    tree_src = "tree /F src" if _IS_WIN else "tree -L 2 src"
    print(terminal.run({"command": tree_src}))
    print()

    print("=== 测试21: Terminal + NoteTool — 慢查询日志写入阻塞类笔记 ===")
    terminal.reset_dir()
    log_analysis = terminal.run(
        {
            "command": (
                "powershell -NoProfile -Command "
                "\"Select-String -Path 'logs/app.log' -SimpleMatch -Pattern 'slow query' "
                "| Select-Object -Last 10\""
                if _IS_WIN
                else "grep 'slow query' logs/app.log | tail -n 10"
            )
        }
    )
    notes = NoteTool(workspace=str(ws / "notes_store"), auto_backup=False)
    print(
        notes.run(
            {
                "action": "create",
                "title": "数据库慢查询问题（演示）",
                "content": (
                    "## 问题描述\n演示：从终端摘录慢查询相关日志。\n\n"
                    f"## 日志分析\n```\n{log_analysis}\n```\n\n"
                    "## 下一步\n1. 分析 SQL\n2. 索引与优化\n"
                ),
                "note_type": "blocker",
                "tags": ["performance", "database"],
            }
        )
    )
    print()

    try:
        from context import ContextBuilder, ContextConfig, ContextPacket
        from core import Message
        from tools import MemoryTool
    except ImportError as err:
        print(
            f"=== 跳过测试 22–23（需要完整依赖，例如 numpy、tiktoken 等）: {err} ===\n"
        )
    else:
        uid = f"terminal_demo_{ws.name}"
        memory_tool = MemoryTool(user_id=uid, memory_types=["semantic"])

        print("=== 测试22: Terminal + MemoryTool — 将 tree 结果写入语义记忆并检索 ===")
        terminal.reset_dir()
        structure = terminal.run({"command": tree_src})
        print(
            memory_tool.run(
                {
                    "action": "add",
                    "content": f"项目结构:\n{structure}",
                    "memory_type": "semantic",
                    "importance": 0.8,
                }
            )
        )
        print(
            memory_tool.run(
                {"action": "search", "query": "项目结构 processor", "limit": 3}
            )
        )
        print()

        print("=== 测试23: Terminal + ContextBuilder — additional_packets 注入终端输出 ===")
        terminal.reset_dir()
        code_paths = terminal.run(
            {"command": "dir /s /b src\\*.py" if _IS_WIN else "find src -name '*.py'"}
        )
        readme_snip = terminal.run(
            {
                "command": (
                    'powershell -NoProfile -Command "Get-Content README.md -TotalCount 5"'
                    if _IS_WIN
                    else "head -n 5 README.md"
                )
            }
        )
        builder = ContextBuilder(
            memory_tool=memory_tool,
            rag_tool=None,
            config=ContextConfig(
                max_tokens=2500, min_relevance=0.01, reserve_ratio=0.15
            ),
        )
        built = builder.build(
            user_query="如何重构用户服务模块",
            conversation_history=[
                Message(
                    content="我们准备拆分单体里的用户相关逻辑。",
                    role="user",
                    timestamp=datetime.now(),
                ),
            ],
            system_instructions="你是资深后端顾问，回答要具体可执行。",
            additional_packets=[
                ContextPacket(
                    content=f"代码路径:\n{code_paths}",
                    metadata={"type": "code_structure", "source": "terminal"},
                    relevance_score=0.7,
                ),
                ContextPacket(
                    content=f"README 摘录:\n{readme_snip}",
                    metadata={"type": "readme", "source": "terminal"},
                    relevance_score=0.75,
                ),
            ],
        )
        preview = (
            built
            if len(built) <= 2400
            else built[:2400] + "\n... [输出已截断用于展示] ..."
        )
        print(preview)
        print()
