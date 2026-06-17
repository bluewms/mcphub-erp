# 鼎捷 ERP MCP Server

[English](README.en.md) | [中文](README.md)

鼎捷 ERP E10 MCP Server，让 AI 助手（Claude Desktop、Claude Code、Cursor、Cline、OpenClaw 等任意支持 MCP 协议的客户端）通过自然语言查询和操作鼎捷 ERP 系统。

## 功能特性

- **20 个 MCP 工具**：覆盖采购入库、销货出库、物料查询等核心操作
- **通用接口设计**：统一的 CRUD + 审核操作模式
- **只读/读写模式**：可限制 AI 只能查询，防止误操作
- **自动会话恢复**：长时间运行时自动处理会话超时
- **多传输协议**：支持 stdio（本地）、SSE、streamable-http（远程共享）
- **字段元数据**：内置表单元数据查询，帮助 AI 正确构造参数

## 快速开始

### 方式一：uvx 直接运行（推荐）

```bash
# 设置环境变量
export DINGJIE_SERVER_URL=https://erp.company.com/
export DINGJIE_APP_ID=your_app_id
export DINGJIE_APP_SECRET=your_app_secret

# 启动 MCP Server
uvx dingjie-erp-mcp
```

### 方式二：从源码运行

```bash
git clone https://github.com/user/dingjie-erp-mcp.git
cd dingjie-erp-mcp
uv sync
uv run dingjie-erp-mcp
```

## 配置

复制环境变量模板并填写：

```bash
cp .env.example .env
```

| 环境变量 | 说明 | 示例 |
|----------|------|------|
| `DINGJIE_SERVER_URL` | 鼎捷 ERP 服务器地址 | `https://erp.company.com/` |
| `DINGJIE_APP_ID` | 应用 ID | `your_app_id` |
| `DINGJIE_APP_SECRET` | 应用密钥 | `your_app_secret` |
| `DINGJIE_ACCT_ID` | 账套 ID（可选） | `your_acct_id` |
| `DINGJIE_USERNAME` | 用户名（可选） | `your_username` |
| `DINGJIE_PASSWORD` | 密码（可选） | `your_password` |
| `DINGJIE_TIMEOUT` | 请求超时（秒） | `30` |
| `DINGJIE_VERIFY_SSL` | 是否验证 SSL | `1` |
| `DINGJIE_LOCALE` | 语言 | `zh_CN` |
| `MCP_MODE` | 模式 (readonly/readwrite) | `readwrite` |

## 客户端配置

### Claude Desktop

编辑 `~/Library/Application Support/Claude/claude_desktop_config.json`（macOS）：

```json
{
  "mcpServers": {
    "dingjie-erp": {
      "command": "uvx",
      "args": ["dingjie-erp-mcp"],
      "env": {
        "DINGJIE_SERVER_URL": "https://erp.company.com/",
        "DINGJIE_APP_ID": "your_app_id",
        "DINGJIE_APP_SECRET": "your_app_secret"
      }
    }
  }
}
```

### Claude Code

在项目目录下创建 `.mcp.json`：

```json
{
  "mcpServers": {
    "dingjie-erp": {
      "command": "uvx",
      "args": ["dingjie-erp-mcp"],
      "env": {
        "DINGJIE_SERVER_URL": "https://erp.company.com/",
        "DINGJIE_APP_ID": "your_app_id",
        "DINGJIE_APP_SECRET": "your_app_secret"
      }
    }
  }
}
```

### SSE 模式（远程共享）

```bash
DINGJIE_SERVER_URL=... \
DINGJIE_APP_ID=... \
DINGJIE_APP_SECRET=... \
MCP_API_KEY=your-mcp-key \
uvx dingjie-erp-mcp --transport sse --port 8080
```

## 可用工具

### 采购入库（7 个）

| 工具 | 说明 |
|------|------|
| `query_purchase_receipts` | 查询采购入库单列表 |
| `read_purchase_receipt` | 查看采购入库单详情 |
| `create_purchase_receipt` | 创建采购入库单 |
| `approve_purchase_receipt` | 审核采购入库单 |
| `disapprove_purchase_receipt` | 撤销审核采购入库单 |
| `delete_purchase_receipt` | 删除采购入库单 |
| `invalid_purchase_receipt` | 作废采购入库单 |

### 销货出库（7 个）

| 工具 | 说明 |
|------|------|
| `query_sales_issues` | 查询销货出库单列表 |
| `read_sales_issue` | 查看销货出库单详情 |
| `create_sales_issue` | 创建销货出库单 |
| `approve_sales_issue` | 审核销货出库单 |
| `disapprove_sales_issue` | 撤销审核销货出库单 |
| `delete_sales_issue` | 删除销货出库单 |
| `invalid_sales_issue` | 作废销货出库单 |

### 物料（2 个）

| 工具 | 说明 |
|------|------|
| `query_materials` | 查询物料列表 |
| `read_material` | 查看物料详情 |

### 通用（2 个）

| 工具 | 说明 |
|------|------|
| `health_check` | 检查 ERP 连接状态 |
| `query_metadata` | 查询表单元数据 |

## 只读模式

通过 `--mode readonly` 或 `MCP_MODE=readonly` 限制服务器只暴露查询工具：

```json
"args": ["dingjie-erp-mcp", "--mode", "readonly"]
```

## 开发

```bash
git clone https://github.com/user/dingjie-erp-mcp.git
cd dingjie-erp-mcp
uv sync --dev

# 运行测试
uv run pytest

# 代码检查
uv run ruff check .
uv run mypy src
```

## 架构

详见 [ARCHITECTURE.md](docs/ARCHITECTURE.md) 和 [DEVELOPMENT_PLAN.md](docs/DEVELOPMENT_PLAN.md)。

## 许可证

MIT License
