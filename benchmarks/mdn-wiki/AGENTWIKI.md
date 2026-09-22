---
default_type: note
required_fields: []
---

# Wiki 使用指南

检索命中后请使用原生文件工具读取关键文档原文，再形成结论。
新建或首次修改陌生目录前，先调用 `get_wiki_rules` 获取适用规则。
使用原生工具修改 Markdown 后，调用 `validate_wiki` 检查格式、Frontmatter、目录约束和内部链接。
