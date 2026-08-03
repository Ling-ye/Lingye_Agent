# Changelog / 更新日志

This file records user-visible changes to Lingye Agent.
本文件记录 Lingye Agent 面向用户的变更。

## [Unreleased] / 未发布

### Changed / 变更

- No changes yet. / 暂无变更。

## [0.1.0] - 2026-08-03

### Added / 新增

- Six agent patterns: Simple, Function Call, ReAct, Plan-and-Solve, Reflection, and Context-Aware.
- 六种 Agent 范式：Simple、Function Call、ReAct、Plan-and-Solve、Reflection 与 Context-Aware。
- Tool registry, memory modules, RAG components, MCP integration, streaming events, lifecycle hooks, and GSSC context construction.
- 工具注册表、记忆模块、RAG、MCP、流式事件、生命周期钩子与 GSSC 上下文构建。
- GitHub wheel distribution, bilingual documentation, governance files, and release-contract CI checks.
- GitHub wheel 分发、中英文文档、治理文件与发布契约 CI 检查。

### Changed / 变更

- Project maturity is Beta and package metadata now points to the canonical repository.
- 项目成熟度调整为 Beta，包元数据指向正式仓库。
- Runtime databases and local knowledge-base contents are excluded from new releases.
- 运行时数据库与本地知识库内容不再进入新版本。
- Repository text files use stable LF line endings, and source distributions exclude editor and internal maintenance files.
- 仓库文本统一使用 LF 行尾，源码发行包排除编辑器与内部维护文件。

### Known limitations / 已知限制

- The full test suite contains slower and external-service scenarios and exceeded the five-minute local audit window during release preparation. Fast offline release checks remain blocking.
- 完整测试套件包含较慢及依赖外部服务的场景，在发布准备期间超过五分钟本地审计窗口；快速离线发布检查仍为阻断门槛。
- The package is not published on PyPI. Install from the GitHub release wheel or source.
- 当前未发布到 PyPI，请使用 GitHub Release wheel 或源码安装。

[Unreleased]: https://github.com/Ling-ye/Lingye_Agent/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/Ling-ye/Lingye_Agent/releases/tag/v0.1.0
