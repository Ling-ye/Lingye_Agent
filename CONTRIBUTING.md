# Contributing / 贡献指南

## 中文

感谢你改进 Lingye Agent。提交前请先搜索现有 Issue，确认问题尚未被报告。

### 本地环境

Windows PowerShell 下方命令要求 `python` 指向 Python 3.10+；否则请改用该解释器 `python.exe` 的绝对路径。

~~~powershell
git clone https://github.com/Ling-ye/Lingye_Agent.git
cd Lingye_Agent
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
~~~

Linux 或 macOS 用户在进入仓库后执行：

~~~bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
~~~

### 修改要求

- 一个 Pull Request 只处理一个清晰问题。
- 保留无关行为，不顺带重构未涉及模块。
- 新功能或 Bug 修复应添加聚焦测试，并同步更新 README、指南或 CHANGELOG。
- 不得提交 .env、API Key、运行时数据库、知识库内容、模型权重或用户数据。
- 提交信息保持简短清晰；仓库维护者使用中文提交描述。

### 快速验证

~~~bash
python -m pytest -q tests/test_release_contract.py tests/test_function_call_agent_unit.py tests/test_simple_calculator.py::test_calculator_tool
python -m build
python -m twine check dist/*.whl dist/*.tar.gz
python scripts/verify_release_artifact.py dist/lingye_agent-0.1.0-py3-none-any.whl
~~~

完整测试可使用 python -m pytest。若测试需要外部服务，请在 PR 中写明服务、凭据类型和实际结果，不要上传凭据。

Pull Request 应说明目标、实现边界、验证命令、风险和文档变化。

---

## English

Thank you for improving Lingye Agent. Search existing issues before opening a new report or pull request.

### Local setup

The Windows PowerShell commands below require `python` to resolve to Python 3.10+. Otherwise, use the absolute path to the required `python.exe`.

~~~powershell
git clone https://github.com/Ling-ye/Lingye_Agent.git
cd Lingye_Agent
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
~~~

Linux / macOS:

~~~bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
~~~

### Change requirements

- Keep each pull request focused on one clear problem.
- Preserve unrelated behavior and avoid opportunistic refactors.
- Add focused tests for features and bug fixes, and update the README, guide, or changelog when public behavior changes.
- Never commit .env files, API keys, runtime databases, knowledge-base contents, model weights, or user data.
- Use concise commit messages.

### Quick validation

~~~bash
python -m pytest -q tests/test_release_contract.py tests/test_function_call_agent_unit.py tests/test_simple_calculator.py::test_calculator_tool
python -m build
python -m twine check dist/*.whl dist/*.tar.gz
python scripts/verify_release_artifact.py dist/lingye_agent-0.1.0-py3-none-any.whl
~~~

Run python -m pytest for the full suite. If a test requires an external service, document the service, credential type, and exact result in the pull request without exposing credentials.

A pull request should describe its goal, scope, verification commands, risks, and documentation changes.
