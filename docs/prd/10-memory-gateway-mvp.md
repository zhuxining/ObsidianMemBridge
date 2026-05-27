> **Status**: `active`

# Memory Gateway MVP

关联架构：[Architecture Overview](../architecture/00-overview.md)

## 背景

用户同时使用多个 Agent 时，项目背景、偏好和决策分散在不同会话中。ObsidianMemBridge MVP 提供基于 Obsidian 的共享记忆入口：Agent 通过 Markdown 文件读写记忆，通过 Frontmatter 过滤查询。

## 功能描述

### Story 1：按 Frontmatter 过滤查询记忆

作为用户，我希望按 Frontmatter 字段过滤查询 Obsidian 中的记忆文件，以便快速定位上下文。

验收标准：

- Given Vault 中存在带 YAML Frontmatter 的 Markdown 文件
  When 用户按 status、type、scope、project、tags 或 source 过滤查询
  Then 系统返回匹配的文件列表，包含文件路径、标题、Frontmatter 元数据和正文摘要
- Given 某文件缺少必需 Frontmatter 字段 status、type、source 或 created_at
  When 系统构建查询结果
  Then 该文件被跳过，并输出可定位的校验警告

优先级：P0

### Story 2：写入 Markdown 记忆

作为 Agent，我希望向 Vault 写入新的 Markdown 记忆文件（带 Frontmatter），以便持久化上下文。

验收标准：

- Given 用户提供标题、内容和 Frontmatter 元数据
  When 写入请求通过校验（必需字段完整、路径合法）
  Then Vault 中新增一条 Markdown 文件，Frontmatter 包含 status、type、scope、source、created_at
- Given 写入请求缺少必需 Frontmatter 字段或路径超出 Vault 根目录
  When 系统接收请求
  Then 系统拒绝写入，并返回可读错误信息

优先级：P0

### Story 3：更新已有记忆

作为用户，我希望更新已有记忆文件的内容和 Frontmatter，以便维护记忆准确性。

验收标准：

- Given 用户指定一个已有的记忆文件路径
  When 用户提供新内容或 Frontmatter 更新
  Then 文件被更新，Frontmatter 包含 updated_at
- Given 用户指定的文件不存在
  When 更新请求提交
  Then 系统返回文件未找到错误

优先级：P0

### Story 4：CLI 入口

作为用户，我希望通过本地命令完成查询、写入和更新操作，以便在 Agent 接入前验证流程。

验收标准：

- Given 用户执行 `obsidianmembridge read --type fact --status active`
  When 命令执行完成
  Then 输出匹配的 Markdown 文件列表及其 Frontmatter 元数据
- Given 用户执行 `obsidianmembridge write --title "..." --content "..." --type fact --project obsidianmembridge`
  When 命令执行完成
  Then Vault 中新增对应的 Markdown 文件
- Given 用户执行 `obsidianmembridge init /path/to/vault`
  When 命令执行完成
  Then Vault 目录结构（记忆目录、配置文件、Frontmatter schema 说明）已创建

优先级：P1

### Story 5：MCP 工具入口

作为 Agent 使用者，我希望通过 MCP 工具调用 read 和 write 能力，以便 Agent 自主读写记忆。

验收标准：

- Given Agent 通过 MCP 调用 read_memories 工具，传入过滤条件
  When 工具执行完成
  Then 返回与 CLI read 等价的结果
- Given Agent 通过 MCP 调用 write_memory 工具，传入标题、内容和元数据
  When 工具执行完成
  Then Vault 中新增对应的 Markdown 文件

优先级：P1

## 范围界定

In Scope：

- Obsidian Vault 目录初始化。
- Markdown 文件作为记忆存储单元（读、写、更新）。
- YAML Frontmatter schema 校验。
- 按 Frontmatter 字段过滤查询。
- 本地 CLI 入口。
- MCP 入口（read_memories / write_memory）。
- 记忆状态：active、archived。

Out of Scope：

- Web UI、多用户权限、云端同步。
- 提案审批流程、事件摘要、项目状态管理（后续迭代）。
- 向量检索、图谱索引（后续迭代）。

## 非功能需求

- 性能：5,000 条记忆以内，单次查询 <= 2 秒。
- 安全：禁止写入 API key、password、token、private key。
- 审计：每条记忆的 Frontmatter 必须包含 source、created_at、status、type。
- 兼容：macOS 本地文件系统，Python 3.12+。