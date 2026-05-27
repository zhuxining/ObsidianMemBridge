> **Status**: `active`

# Directory Structure

## 目录树

```text
.
├── docs/
│   ├── architecture/
│   │   ├── 00-overview.md
│   │   └── reference/
│   │       └── directory-structure.md
│   └── prd/
├── src/
│   └── obsidianmembridge/
│       ├── commands/
│       ├── models/
│       ├── services/
│       └── utils/
└── tests/
    └── unit/
        ├── models/
        ├── services/
        └── utils/
```

## 包职责

| 路径 | 职责 | 禁止内容 |
|------|------|----------|
| `src/obsidianmembridge/commands/` | 外部入口编排，包括 Typer CLI 和 FastMCP 工具；负责参数映射、输出格式和调用服务 | 文件系统细节、Frontmatter 核心校验、业务规则 |
| `src/obsidianmembridge/models/` | 共享数据契约，包括记忆模型、查询过滤模型、配置对象和错误类型 | 文件读写、命令输出、服务编排、通用校验函数 |
| `src/obsidianmembridge/services/` | 应用服务层，承接 CLI/MCP 请求并编排模型、校验工具和 `utils` | CLI 参数解析、MCP 协议细节、Markdown 序列化细节 |
| `src/obsidianmembridge/utils/` | 通用支撑能力，包括标题 slug、正文摘要、Frontmatter 校验、Vault 文件工具和安全检测 | 命令入口、服务编排、共享数据模型 |
| `src/obsidianmembridge/cli.py`、`src/obsidianmembridge/mcp.py`、`src/obsidianmembridge/config.py` | 兼容旧导入路径的薄转发文件 | 新功能实现 |

## 入口文件

- CLI 主入口：`src/obsidianmembridge/commands/cli.py`，由 `pyproject.toml` 的 `meb = "obsidianmembridge.commands.cli:cli"` 启动。
- MCP 主入口：`src/obsidianmembridge/commands/mcp.py`，导出 `mcp` 和三个工具函数。
- 兼容入口：`src/obsidianmembridge/cli.py`、`src/obsidianmembridge/mcp.py`、`src/obsidianmembridge/config.py` 只做 re-export，避免旧导入路径立即失效。

## 依赖方向

允许的主要依赖方向：

```text
commands -> services -> models -> utils
```

规则：

- `commands/` 只负责入口编排，调用 `services/` 完成业务动作。
- `services/` 可以组合 `models/` 和 `utils/`。
- `models/` 承载数据契约和错误类型，不承载校验流程。
- `utils/validation.py` 承载 Frontmatter 校验和敏感 key 检查。
- `utils/store.py`、`utils/markdown.py`、`utils/paths.py` 承载 Obsidian Vault 文件工具。
- `utils/sensitive.py` 只提供安全检测函数，不承载业务流程。
- `utils/` 不依赖 `commands/` 或 `services/`。
- 兼容转发文件不能被新实现依赖；新代码必须直接使用 canonical 路径。

## 变更规则

- 新增 CLI 命令或 MCP 工具时，放入 `commands/`，并通过 `services/` 调用核心能力。
- 新增 Pydantic 模型、配置对象、状态枚举或跨模块 DTO 时，放入 `models/`。
- 新增模型相关校验函数时，放入 `utils/validation.py` 或新的 `utils/*` 平铺模块。
- 新增 Obsidian Vault、Markdown 或文件系统工具行为时，放入 `utils/` 下的对应平铺模块。
- 新增安全检测工具时，放入 `utils/sensitive.py` 或新的 `utils/*` 平铺模块。
- 新增无业务状态、可跨模块复用的纯函数时，放入 `utils/`。
- 新增业务流程时，优先放入 `services/`，不要放进 `commands/`。
- 新增一级目录、移动入口文件、移动模型或抽取工具后，必须同步更新本文档。
