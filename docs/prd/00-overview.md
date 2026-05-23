> **Status**: `active`

# MemBridge PRD Overview

## 产品定位

MemBridge 为本地 Agent 工作流提供基于 Obsidian 的记忆层。核心能力：让 Agent 读写 Obsidian Markdown 文件，并按 Frontmatter 元数据过滤查询。

In Scope：

- Markdown 文件作为记忆存储单元（读取、创建、更新）。
- YAML Frontmatter 作为可查询元数据。
- 按 Frontmatter 字段过滤查询记忆。
- 本地 CLI 入口。
- MCP 工具入口（与 CLI 等价的能力）。

Out of Scope：

- 多用户协作、云端同步、Agent runtime。
- 提案审批流程、事件摘要、项目状态管理等复杂实体（留给后续迭代）。
- Web UI（CLI + Obsidian 原生视图已覆盖 MVP 需求）。