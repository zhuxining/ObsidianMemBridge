> **Status**: `active`

# MemBridge Architecture Overview

## 文档导航

- [00-overview.md](00-overview.md)：定义 MemBridge 的全局目标、模块边界、核心实体、主流程和安全边界。

## 系统目标与约束

MemBridge 是面向个人与项目工作流的 Obsidian-based shared memory layer，为 Claude、Codex、OpenClaw、Pi wrapper 和其他本地 Agent 提供统一、可治理、可审计的上下文读写能力。

核心约束：

- Obsidian Vault 是人工可读写的 canonical memory store；每条记忆以 Markdown 文件保存。
- Markdown 正文承载记忆内容，YAML Frontmatter 承载可查询元数据；元数据事实源不放在独立数据库中。
- Agent 不直接写正式记忆目录；写入必须经过受治理的 proposal、episode 或 project state 入口。
- Agent 接入通过语义化入口完成；系统不向 Agent 暴露通用文件删除能力。
- MCP Server 与 CLI 共享同一 Gateway Core；记忆分类、校验、去重、提交逻辑只存在一份。
- 每条长期记忆保留来源、状态、作用域、证据和变更关系；缺失任一项的长期记忆不得进入 active 状态。
- 查询先按 Frontmatter 过滤候选文件，再基于正文相关性组装 context package。

## 核心设计原则

- **Markdown File as Memory Unit**：一条正式记忆对应一个 Markdown 文件。理由是该粒度符合 Obsidian 的文件模型、双链和 Git 审计方式。
- **Frontmatter as Metadata Contract**：状态、类型、范围、项目、标签、来源和证据引用写入 YAML Frontmatter。理由是 Obsidian 用户可以直接用属性过滤、查询和批量维护。
- **Governed Write Path**：Agent 只提交 proposal、episode 和 project state。理由是长期偏好、事实和决策需要来源与审批边界。
- **CLI First, MCP Primary**：先用 CLI 验证 Gateway Core，再映射到 MCP 工具。理由是 CLI 可本地调试，MCP 是 Agent 自主读写的正式通道。
- **Context Package over Raw Files**：读取返回整理后的事实、项目背景、事件摘要、决策和来源。理由是 Agent 需要可注入上下文，而不是未组织的文件列表。

## 关键设计决策

| 决策问题 | 选择 | 放弃的替代方案 | 理由 | 变更条件 |
|---------|------|--------------|------|----------|
| 正式记忆存放在哪里？ | Obsidian Vault 中的 Markdown 文件 | 只存 SQLite 或向量库 | Vault 保留人类可读性、双链、Git 审计和手工编辑能力 | 用户放弃 Obsidian 作为主要工作流 |
| Agent 如何接入系统？ | MCP 作为 Agent 主入口，CLI 作为调试和自动化入口 | 只做 MCP 或只做 CLI | MCP 适配 Agent 自主调用，CLI 适配本地脚本、批量导入和索引维护 | 目标 Agent 全部不支持 MCP |
| MCP 与 CLI 如何复用逻辑？ | 两者调用同一个 Gateway Core | MCP 与 CLI 各自实现业务逻辑 | 单一核心避免分类、校验、去重和写入规则分叉 | Gateway Core 无法满足任一入口的稳定契约 |
| 记忆元数据如何存放？ | 使用 Markdown YAML Frontmatter 作为元数据事实源 | 把元数据只放 SQLite 或独立 JSON 索引 | Frontmatter 与 Obsidian 文件模型一致，用户可直接过滤、修改和审计 | Obsidian 不再是主要操作界面 |
| Agent 能否直接提交 active 记忆？ | Agent 提交 proposal，Gateway 或人类完成 commit | Agent 直接写 active 记忆 | proposal 流程降低错误事实、重复记忆和隐私内容进入长期记忆的风险 | 用户明确授权某一低风险类型自动 commit |
| 检索层如何定位？ | Frontmatter 过滤是查询契约，SQLite/vector/graph index 是派生加速层 | 索引库作为主存储 | 派生索引可以重建，Vault 和 Frontmatter 保持可审计事实来源 | Vault 不能承载目标数据规模 |

## 边界划分

```text
Agent Clients / Scripts
        |
        v
MCP Server        CLI
        \          /
         v        v
       Gateway Core
        |    |    |
        |    |    +--> Derived Search Index
        |    +------> Obsidian Vault Adapter
        +----------> Policy Engine
```

- **MCP Server**：向支持 MCP 的 Agent 暴露语义化 memory tools，不负责记忆治理规则。
- **CLI**：向用户、脚本和自动化流程暴露本地命令，不负责独立实现业务逻辑。
- **Gateway Core**：拥有记忆分类、Frontmatter schema 校验、去重、proposal、episode、project state 和 context package 组装规则。
- **Policy Engine**：拥有写入审批、敏感内容拒绝、冲突判定和状态转换规则。
- **Obsidian Vault Adapter**：拥有 Vault 文件布局、Markdown 读写和 YAML Frontmatter 解析细节。
- **Derived Search Index**：拥有正文检索、向量检索或图谱等派生查询数据，可从 Vault 全量重建；不拥有元数据事实。

跨切关注点：

- 日志、审计事件和错误翻译由 Gateway Core 的基础设施组件统一处理。
- 配置加载由入口层注入 Gateway Core；业务模块不直接读取全局环境。
- 密钥与访问令牌只存在入口层和 Vault Adapter 运行环境中，不写入记忆文件。

## 核心实体关系

**Memory**：系统管理的一条长期上下文单元，承载偏好、事实、项目上下文、决策或知识。

**FrontmatterMetadata**：Markdown 文件头部的可查询属性集合，描述 Memory、Proposal、Episode 或 ProjectState 的状态、类型、范围、项目、标签、来源、证据和时间信息。

**Proposal**：Agent 或用户提交的待治理记忆候选，经过校验、去重和审批后转为 Memory 或被拒绝。

**Episode**：一次会话、任务或事件的摘要记录，用于恢复近期上下文。

**ProjectState**：某个项目的当前背景、任务状态、阻塞点和活动决策。

**SourceAgent**：提交读取或写入请求的外部 Agent、脚本或人工入口。

**ContextPackage**：Gateway Core 为一次任务组装的可注入上下文集合，包含内容摘要和来源引用。

```mermaid
erDiagram
    FRONTMATTER_METADATA ||--|| MEMORY : describes
    FRONTMATTER_METADATA ||--|| PROPOSAL : describes
    FRONTMATTER_METADATA ||--|| EPISODE : describes
    FRONTMATTER_METADATA ||--|| PROJECT_STATE : describes
    SOURCE_AGENT ||--o{ PROPOSAL : submits
    SOURCE_AGENT ||--o{ EPISODE : records
    PROPOSAL }o--o| MEMORY : becomes
    MEMORY }o--o{ MEMORY : supersedes
    MEMORY }o--o{ PROJECT_STATE : informs
    EPISODE }o--o{ PROJECT_STATE : updates
    CONTEXT_PACKAGE }o--o{ MEMORY : includes
    CONTEXT_PACKAGE }o--o{ EPISODE : includes
    CONTEXT_PACKAGE }o--o{ PROJECT_STATE : includes
```

## 整体流程

写入主路径：

```text
Agent or CLI
  -> MCP Server or CLI
  -> Gateway Core
  -> Policy Engine
  -> Markdown file with YAML Frontmatter
  -> Obsidian Vault
  -> Derived Search Index refresh
```

读取主路径：

```text
Agent or CLI
  -> MCP Server or CLI
  -> Gateway Core
  -> Frontmatter filter over Vault files
  -> optional Derived Search Index ranking
  -> Policy Engine visibility filter
  -> ContextPackage
```

## 部署架构

MVP 运行在单机本地环境：

```text
Local machine
  ├─ Obsidian Vault directory
  ├─ membridge CLI process
  ├─ membridge MCP Server process
  └─ local derived index files
```

## 安全架构

- 信任边界位于 Agent 入口与 Gateway Core 之间；入口必须声明 actor。
- Gateway Core 在写入前执行 schema 校验、状态约束和禁止内容检查。
- Agent 提交的长期事实、偏好、身份信息和敏感信息进入 proposal 队列，不直接进入 active 记忆。
- Vault Adapter 不接受跨越 Vault 根目录的路径。
