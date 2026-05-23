> **Status**: `active`

# MemBridge PRD Overview

## 功能导航

- [10-memory-gateway-mvp.md](10-memory-gateway-mvp.md)：定义 MemBridge MVP 的用户可见能力，包括上下文读取、事件摘要、记忆候选、任务状态和人工审核。

## 产品边界

MemBridge 的首个可交付版本服务于单机本地 Agent 工作流。核心用户是同时使用 Claude、Codex、OpenClaw、Pi wrapper 和脚本自动化的工程师。

In Scope：

- 让 Obsidian Vault 中的每条记忆以 Markdown 文件保存，并使用 Frontmatter 作为可过滤元数据。
- 让 Agent 在任务开始前获得共享上下文。
- 让 Agent 在任务结束后提交可复用摘要。
- 让 Agent 提交长期记忆候选，等待治理后进入正式记忆。
- 让用户查看、批准、拒绝和废弃记忆候选。
- 让用户按 status、type、scope、project、tags、source_agent 等 Frontmatter 字段过滤查询记忆。
- 让用户维护项目状态，供多个 Agent 读取。

Out of Scope：

- 多用户团队协作。排除原因：首版目标是个人本地 Vault，团队权限会扩大安全边界。
- 云端同步服务。排除原因：Obsidian Sync、Git 或用户自选同步工具已覆盖文件同步。
- Agent runtime。排除原因：MemBridge 提供记忆基础设施，不调度 Agent 执行任务。
