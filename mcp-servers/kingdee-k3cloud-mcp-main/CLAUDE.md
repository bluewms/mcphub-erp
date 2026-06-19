# Claude Code 工作指南 — kingdee-k3cloud-mcp

## 项目概述

金蝶云星空 MCP Server，基于 FastMCP + kingdee-cdp-webapi-sdk，发布到 PyPI。

## 每次 commit & push 后的版本检查

完成修改并推送后，**必须主动判断**是否需要升版本号和发布，不要等用户询问。

| 变更类型 | 版本策略 | 是否 Release |
|---------|---------|-------------|
| 新增 MCP tool | minor bump（1.0.x → 1.1.0） | 是 |
| 返回格式/行为变更（影响调用方） | minor bump | 是 |
| Bug fix | patch bump（1.1.0 → 1.1.1） | 是 |
| Breaking change（删除 tool / 入参不兼容） | major bump（1.x → 2.0.0） | 是 |
| 仅文档 / 注释 / 测试 | 不变 | 否 |

### 发布步骤

1. 更新 `pyproject.toml` 中 `version`
2. 将 `CHANGELOG.md` 的 `[Unreleased]` 改为 `[X.Y.Z] - YYYY-MM-DD`，补充底部 compare URL
3. `git add pyproject.toml CHANGELOG.md && git commit`
4. `git tag vX.Y.Z && git push && git push origin vX.Y.Z`
   → 触发 GitHub Actions Release workflow → 自动发布到 PyPI

## 关键文件

| 文件 | 说明 |
|------|------|
| `src/kingdee_k3cloud_mcp/server.py` | 入口：FastMCP 实例、SDK 管理、分页原语、setup/main |
| `src/kingdee_k3cloud_mcp/utils.py` | 工具注解常量、统一返回格式、会话检测、辅助函数 |
| `src/kingdee_k3cloud_mcp/sdk/__init__.py` | RetryableK3CloudApiSdk（会话自动恢复） |
| `src/kingdee_k3cloud_mcp/tools/__init__.py` | ToolContext + register_all_tools 统一注册 |
| `src/kingdee_k3cloud_mcp/tools/essential.py` | 必备工具：health_check, query_metadata, preview_write |
| `src/kingdee_k3cloud_mcp/tools/profile.py` | 推荐工具：get_profile |
| `src/kingdee_k3cloud_mcp/tools/query.py` | 查询工具：query_bill, count_bill 等 6 个 |
| `src/kingdee_k3cloud_mcp/tools/read.py` | 读取工具：view_bill |
| `src/kingdee_k3cloud_mcp/tools/write.py` | 写入工具：save_bill, delete_bill 等 7 个 |
| `pyproject.toml` | 版本号、依赖 |
| `CHANGELOG.md` | 每次 release 必须更新 |
| `tests/test_server.py` | 单元测试（分页、会话恢复、工具函数） |
| `tests/test_tools.py` | 工具契约测试（读写工具、只读守卫） |

## 项目结构

```
src/kingdee_k3cloud_mcp/
├── __init__.py
├── server.py              # 入口（不定义业务工具，只做注册和启动）
├── utils.py               # 公共辅助函数和工具注解常量
├── sdk/
│   └── __init__.py         # SDK 封装（RetryableK3CloudApiSdk）
└── tools/
    ├── __init__.py          # ToolContext + register_all_tools
    ├── essential.py         # 必备工具（规范要求）
    ├── profile.py           # 推荐工具
    ├── query.py             # 查询类工具
    ├── read.py              # 读取类工具
    └── write.py             # 写入类工具
```

工具按功能领域分文件组织，符合《企业管理软件 MCP 标准服务规范》。

## 新增工具流程

1. 在对应的 `tools/` 子模块中添加工具函数（模块顶层定义，使用 `_ctx` 单例）
2. 在 `register_xxx_tools()` 中注册，添加 `annotations` 注解
3. 在 `server.py` 中 re-export 新函数（供测试导入）
4. 在 `tests/test_tools.py` 补充测试
5. 更新 `README.md` 工具表
6. 更新 `CHANGELOG.md`

## 与 skill repo 的关系

新增 MCP tool 后，通常需要同步更新 `kingdee-k3cloud-skill` 的 SKILL.md 决策树或字段文档。
