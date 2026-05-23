> **Status**: `active`

# Memory Gateway MVP

关联架构：[Architecture Overview](../architecture/00-overview.md)

## 背景与目标

用户同时使用多个 Agent 工具时，项目背景、偏好、决策和任务状态分散在不同会话中，导致重复解释、上下文丢失和错误记忆污染。MemBridge MVP 要提供一个基于 Obsidian 的共享记忆入口，让 Agent 能读取整理后的上下文，并把新记忆以可治理方式提交给用户。

目标：

- 用户可以让多个 Agent 共享同一套项目上下文、事件摘要和长期记忆。
- 用户可以控制哪些 Agent 产出的内容进入正式记忆。
- 用户可以在 Obsidian 中审计和修改正式记忆。

## 功能描述

### Story 1：任务开始前读取上下文

作为 Agent 使用者，我希望 Agent 在开始项目任务前获得与当前问题相关的共享上下文，以便减少重复说明。

验收标准：

- Given Vault 中存在 active profile memory、project memory、episode 和 decision
  When 用户通过任一已接入 Agent 发起带项目名的任务
  Then Agent 获得一个包含 profile、project_context、recent_episodes、decisions、conflicts、sources 六类字段的上下文包
- Given 上下文包引用了 Vault 中的正式记忆
  When Agent 展示或使用该上下文
  Then 每条引用包含可定位到 Vault 文件的 source

优先级：P0

### Story 2：任务结束后提交事件摘要

作为 Agent 使用者，我希望 Agent 在完成有意义任务后提交短事件摘要，以便未来 Agent 可以恢复近期工作背景。

验收标准：

- Given Agent 完成一次项目任务
  When Agent 提交 episode
  Then Vault 中新增一条状态为 active 的 episode 记录
- Given episode 已写入 Vault
  When 用户查看该记录
  Then 记录包含任务结果、关键决策、未解决问题、下一步动作和来源 Agent

优先级：P0

### Story 3：提交长期记忆候选

作为 Agent 使用者，我希望 Agent 发现偏好、事实、项目约定或决策时提交候选记忆，以便我决定是否进入正式记忆。

验收标准：

- Given Agent 识别到长期记忆候选
  When Agent 提交 proposal
  Then Vault 的 Inbox 中新增一条 status 为 proposed 的记录
- Given proposal 内容缺少 evidence、type、scope、source_agent 或 confidence
  When 系统接收该 proposal
  Then 系统拒绝写入，并返回可读错误信息
- Given proposal 类型为 preference、fact、identity 或 sensitive
  When 系统完成接收
  Then proposal 的 requires_approval 为 true

优先级：P0

### Story 4：审核记忆候选

作为用户，我希望查看、批准、拒绝和废弃记忆候选，以便正式记忆保持可信。

验收标准：

- Given Inbox 中存在 proposed 记录
  When 用户列出待审核项
  Then 系统按创建时间倒序返回全部 proposed 记录
- Given 用户批准一条 proposed 记录
  When 系统提交该记录
  Then 正式记忆目录新增 active 记录，原 proposal 标记为 committed
- Given 用户拒绝一条 proposed 记录
  When 系统保存拒绝结果
  Then proposal 状态变为 rejected，正式记忆目录不新增记录

优先级：P1

### Story 5：共享项目状态

作为 Agent 使用者，我希望跨 Agent 共享项目当前状态，以便不同工具接手任务时知道当前进度。

验收标准：

- Given 项目存在 active task、blocked task 和 done task
  When Agent 请求项目状态
  Then 系统返回项目背景、活动任务、阻塞任务、已完成任务和最近决策
- Given Agent 更新项目任务状态
  When 更新内容包含项目名、任务名、状态、来源 Agent
  Then Vault 中的项目状态记录被更新，并保留更新时间

优先级：P1

### Story 6：本地人工入口

作为用户，我希望通过本地命令完成初始化、检索、提交摘要、提交候选、审核候选和重建索引，以便在 Agent 接入前验证记忆流程。

验收标准：

- Given 用户在空目录执行初始化
  When 初始化完成
  Then Vault 目录结构、系统配置记录和 Inbox 目录存在
- Given Vault 中已有 active 记忆
  When 用户执行检索命令
  Then 命令输出上下文包，并包含 sources 字段
- Given 用户执行重建索引命令
  When 命令完成
  Then 检索结果与 Vault 中 active 记录保持一致

优先级：P1

## 范围界定

In Scope：

- Obsidian Vault 目录初始化。
- 上下文包读取。
- episode 自动写入。
- proposal 提交、批准、拒绝和废弃。
- project state 读取和更新。
- 本地 CLI 入口。
- MCP 入口暴露与 CLI 同等的 Agent 语义能力。
- active、proposed、committed、rejected、deprecated 五种记忆状态。

Out of Scope：

- Web UI。排除原因：CLI 与 Obsidian 文件视图已覆盖 MVP 审核入口。
- 多用户权限。排除原因：MVP 运行在单用户本地环境。
- 云端服务。排除原因：项目目标是本地优先的 Obsidian-based memory layer。
- 自动总结完整聊天原文。排除原因：长期存储原文会放大隐私和噪音风险。
- 直接接管 Agent 执行流程。排除原因：MemBridge 是共享记忆层，不是 Agent runtime。

## 非功能需求

- 性能约束：在 5,000 条 active 记忆以内，单次上下文包读取在本地开发机上完成时间 <= 2 秒。
- 数据安全：系统不得把 API key、password、token、private key 写入 active 记忆。
- 审计约束：所有 active 长期记忆必须包含 source_agent、created_at、status、type、scope、evidence。
- 兼容性约束：MVP 支持 macOS 本地文件系统和 Python 3.14。
