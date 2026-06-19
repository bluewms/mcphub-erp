# 鼎捷 ERP MCP Server 架构设计

---

## 一、系统架构

```
┌──────────────────────────────────────────────────────┐
│  AI 助手 (Claude Desktop / Claude Code / Cursor /   │
│  Cline / OpenClaw 等任意支持 MCP 协议的客户端)        │
└──────────────────┬───────────────────────────────────┘
                   │  MCP 协议 (stdio / SSE / streamable-http)
                   ▼
┌──────────────────────────────────────────────────────┐
│               dingjie-erp-mcp (本项目)               │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐ │
│  │  MCP Tools  │  │ MCP Prompts │  │ MCP Resource│ │
│  │  (15+ 工具) │  │  (工作流)    │  │  (元数据)   │ │
│  └──────┬──────┘  └─────────────┘  └─────────────┘ │
│         │                                             │
│  ┌──────▼──────────────────────────────────────────┐ │
│  │              Tool Registry (工具注册)            │ │
│  │  purchase.py │ sales.py │ inventory.py │ ...    │ │
│  └──────┬──────────────────────────────────────────┘ │
│         │                                             │
│  ┌──────▼──────────────────────────────────────────┐ │
│  │           DingjieClient (API 客户端)             │ │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────────────┐ │ │
│  │  │   Auth   │ │  Session │ │  Rate Limiter    │ │ │
│  │  │  认证模块 │ │ 会话管理  │ │   速率限制       │ │ │
│  │  └──────────┘ └──────────┘ └──────────────────┘ │ │
│  └──────┬──────────────────────────────────────────┘ │
│         │  HTTPS / RESTful API                       │
└─────────┼────────────────────────────────────────────┘
          │
          ▼
┌──────────────────────────────────────────────────────┐
│            鼎捷 ERP E10 (REST API)                   │
│        e10.oapi.purchase.receipt.*                    │
│        e10.oapi.sales.issue.*                        │
│        e10.oapi.material.*                           │
└──────────────────────────────────────────────────────┘
```

---

## 二、项目目录结构

```
dingjie-mcp/
├── src/
│   └── dingjie_erp_mcp/
│       ├── __init__.py              # 包初始化
│       ├── server.py                # FastMCP Server 入口
│       ├── sdk/                     # 鼎捷 ERP API 客户端
│       │   ├── __init__.py
│       │   ├── client.py            # REST API 客户端核心
│       │   ├── auth.py              # 认证模块
│       │   ├── session.py           # 会话管理（自动恢复）
│       │   └── models.py            # 数据模型定义
│       ├── tools/                   # MCP 工具（模块化设计）
│       │   ├── __init__.py          # 工具注册
│       │   ├── purchase_receipt.py  # 采购入库工具
│       │   ├── sales_issue.py       # 销货出库工具
│       │   ├── material.py          # 物料查询工具
│       │   ├── inventory.py         # 库存查询工具
│       │   └── common.py            # 通用工具（查询元数据等）
│       ├── utils/                   # 工具函数
│       │   ├── __init__.py
│       │   ├── rate_limit.py        # 速率限制
│       │   ├── logger.py            # 日志
│       │   └── pagination.py        # 自动翻页
│       └── py.typed                 # 类型标记
├── tests/
│   ├── __init__.py
│   ├── test_client.py               # 客户端测试
│   ├── test_tools.py                # 工具测试
│   └── conftest.py                  # 测试配置
├── docs/
│   ├── DEVELOPMENT_PLAN.md          # 开发规划
│   ├── ARCHITECTURE.md              # 架构设计
│   └── FIELD_MAPPING.md             # 字段映射参考
├── pyproject.toml                   # 项目配置
├── .env.example                     # 环境变量模板
├── README.md                        # 项目说明
├── Makefile                         # 开发命令
└── LICENSE                          # 许可证
```

---

## 三、核心模块设计

### 3.1 SDK 客户端 (`sdk/client.py`)

```python
class DingjieClient:
    """鼎捷 ERP E10 REST API 客户端
    
    特性：
    - 自动认证和会话管理
    - 请求重试和错误处理
    - 响应格式化
    """
    
    def __init__(self, server_url, app_id, app_secret, ...): ...
    
    # --- 采购入库 ---
    def create_purchase_receipt(self, data: dict) -> dict: ...
    def approve_purchase_receipt(self, doc_no: str) -> dict: ...
    def disapprove_purchase_receipt(self, doc_no: str) -> dict: ...
    def delete_purchase_receipt(self, doc_no: str) -> dict: ...
    def query_purchase_receipts(self, filters: dict) -> dict: ...
    def read_purchase_receipt(self, doc_no: str) -> dict: ...
    def invalid_purchase_receipt(self, doc_no: str) -> dict: ...
    
    # --- 销货出库 ---
    def create_sales_issue(self, data: dict) -> dict: ...
    def approve_sales_issue(self, doc_no: str) -> dict: ...
    def disapprove_sales_issue(self, doc_no: str) -> dict: ...
    def delete_sales_issue(self, doc_no: str) -> dict: ...
    def query_sales_issues(self, filters: dict) -> dict: ...
    def read_sales_issue(self, doc_no: str) -> dict: ...
    def invalid_sales_issue(self, doc_no: str) -> dict: ...
    
    # --- 物料 ---
    def query_materials(self, filters: dict) -> dict: ...
    def read_material(self, code: str) -> dict: ...
    
    # --- 通用 ---
    def _request(self, method, path, data=None) -> dict: ...
    def _handle_error(self, response) -> None: ...
```

### 3.2 认证模块 (`sdk/auth.py`)

```python
class DingjieAuth:
    """鼎捷 ERP 认证模块
    
    支持的认证方式（待确认）：
    1. API Key (Bearer Token)
    2. 用户名 + 密码 (Form Auth)
    3. OAuth 2.0
    4. App ID + App Secret
    """
    
    def __init__(self, app_id, app_secret, ...): ...
    def get_headers(self) -> dict: ...
    def refresh_token(self) -> None: ...
    def is_authenticated(self) -> bool: ...
```

### 3.3 会话管理 (`sdk/session.py`)

```python
class SessionManager:
    """会话管理（参考 kingdee-k3cloud-mcp）
    
    功能：
    - 自动检测会话过期
    - 自动重新认证
    - 冷却期保护（避免频繁重连）
    """
    
    SESSION_LOST_PATTERNS = ["会话信息已丢失", "session expired", "unauthorized"]
    RESET_COOLDOWN = 300  # 5 分钟冷却
    
    def check_session_expired(self, response) -> bool: ...
    def recover_session(self) -> None: ...
```

### 3.4 MCP 工具注册 (`tools/__init__.py`)

```python
"""MCP 工具注册

借鉴 muk_mcp 的模块化设计：
- 每个业务对象一个文件
- 使用装饰器注册工具
- 统一的输入输出格式
"""

from dingjie_erp_mcp.tools.purchase_receipt import register_purchase_receipt_tools
from dingjie_erp_mcp.tools.sales_issue import register_sales_issue_tools
from dingjie_erp_mcp.tools.material import register_material_tools
from dingjie_erp_mcp.tools.common import register_common_tools

def register_all_tools(mcp: FastMCP, client: DingjieClient):
    """注册所有 MCP 工具"""
    register_purchase_receipt_tools(mcp, client)
    register_sales_issue_tools(mcp, client)
    register_material_tools(mcp, client)
    register_common_tools(mcp, client)
```

### 3.5 工具模块示例 (`tools/purchase_receipt.py`)

```python
from mcp.server.fastmcp import FastMCP
from dingjie_erp_mcp.sdk.client import DingjieClient

def register_purchase_receipt_tools(mcp: FastMCP, client: DingjieClient):
    """注册采购入库相关工具"""
    
    @mcp.tool()
    def query_purchase_receipts(
        doc_no: str = "",
        supplier_no: str = "",
        start_date: str = "",
        end_date: str = "",
        limit: int = 100,
        offset: int = 0,
    ) -> str:
        """查询鼎捷 ERP 采购入库单
        
        Args:
            doc_no: 单号（模糊匹配）
            supplier_no: 供应商编号
            start_date: 开始日期 (YYYY-MM-DD)
            end_date: 结束日期 (YYYY-MM-DD)
            limit: 返回行数上限，默认100
            offset: 跳过行数，用于翻页
        """
        ...
    
    @mcp.tool()
    def create_purchase_receipt(
        om_site_id: str,
        supplier_no: str,
        doc_type_no: str = "",
        doc_date: str = "",
        remark: str = "",
        details: str = "",
    ) -> str:
        """创建鼎捷 ERP 采购入库单
        
        Args:
            om_site_id: 营运据点编号
            supplier_no: 供应商编号
            doc_type_no: 单据类型编号
            doc_date: 单据日期 (YYYY-MM-DD)
            remark: 备注
            details: 明细 JSON 数组，如:
                [{"business_qty": 100, "warehouse_no": "WH01"}]
        """
        ...
    
    @mcp.tool()
    def approve_purchase_receipt(doc_no: str) -> str:
        """审核鼎捷 ERP 采购入库单
        
        Args:
            doc_no: 单号
        """
        ...
    
    # ... 更多工具
```

---

## 四、MCP 工具清单

### 4.1 采购入库工具（7 个）

| 工具名 | 类别 | 说明 |
|--------|------|------|
| `query_purchase_receipts` | read | 查询采购入库单列表 |
| `read_purchase_receipt` | read | 查看采购入库单详情 |
| `create_purchase_receipt` | write | 创建采购入库单 |
| `approve_purchase_receipt` | write | 审核采购入库单 |
| `disapprove_purchase_receipt` | write | 撤销审核采购入库单 |
| `delete_purchase_receipt` | write | 删除采购入库单 |
| `invalid_purchase_receipt` | write | 作废采购入库单 |

### 4.2 销货出库工具（7 个）

| 工具名 | 类别 | 说明 |
|--------|------|------|
| `query_sales_issues` | read | 查询销货出库单列表 |
| `read_sales_issue` | read | 查看销货出库单详情 |
| `create_sales_issue` | write | 创建销货出库单 |
| `approve_sales_issue` | write | 审核销货出库单 |
| `disapprove_sales_issue` | write | 撤销审核销货出库单 |
| `delete_sales_issue` | write | 删除销货出库单 |
| `invalid_sales_issue` | write | 作废销货出库单 |

### 4.3 物料工具（3 个）

| 工具名 | 类别 | 说明 |
|--------|------|------|
| `query_materials` | read | 查询物料列表 |
| `read_material` | read | 查看物料详情 |
| `sync_material` | write | 同步物料信息 |

### 4.4 通用工具（3 个）

| 工具名 | 类别 | 说明 |
|--------|------|------|
| `query_metadata` | read | 查询表单元数据（字段结构） |
| `health_check` | read | 检查 ERP 连接状态 |
| `query_bill_all` | read | 自动翻页查询（大数据量） |

**合计：20 个工具**

---

## 五、安全架构

### 5.1 安全层级

```
┌─────────────────────────────────────┐
│  Layer 1: 传输层安全                │
│  - HTTPS 加密通信                   │
│  - stdio 本地进程间通信（无网络）    │
└──────────────────┬──────────────────┘
                   ▼
┌─────────────────────────────────────┐
│  Layer 2: 认证层                    │
│  - 环境变量注入凭证（不进入 LLM）   │
│  - API Key / 用户名密码认证         │
│  - MCP_API_KEY（SSE/HTTP 模式）     │
└──────────────────┬──────────────────┘
                   ▼
┌─────────────────────────────────────┐
│  Layer 3: 授权层                    │
│  - 只读模式（--mode readonly）      │
│  - 写入工具在只读模式下返回错误     │
│  - ERP 侧 ACL 权限继承             │
└──────────────────┬──────────────────┘
                   ▼
┌─────────────────────────────────────┐
│  Layer 4: 防护层                    │
│  - 速率限制（请求/分钟）            │
│  - 请求超时                         │
│  - 最大返回行数限制                 │
└──────────────────┬──────────────────┘
```

### 5.2 只读模式

```python
# 只读模式下，写入工具返回错误
_readonly = False

@mcp.tool()
def create_purchase_receipt(...):
    if _readonly:
        return json.dumps({"error": "只读模式：写入操作已禁用"})
    # ... 正常逻辑
```

### 5.3 速率限制（参考 muk_mcp）

```python
class RateLimiter:
    """滑动窗口速率限制"""
    
    def __init__(self, max_requests=60, window_seconds=60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
    
    def check(self, key_id: int) -> bool:
        """检查是否超过速率限制"""
        ...
```

---

## 六、配置管理

### 6.1 环境变量

```bash
# === 必填 ===
DINGJIE_SERVER_URL=https://erp.company.com/     # 鼎捷 ERP 服务器地址
DINGJIE_APP_ID=your_app_id                       # 应用 ID
DINGJIE_APP_SECRET=your_app_secret               # 应用密钥

# === 可选 ===
DINGJIE_ACCT_ID=your_acct_id                     # 账套 ID
DINGJIE_USERNAME=your_username                    # 用户名（如需）
DINGJIE_PASSWORD=your_password                    # 密码（如需）
DINGJIE_TIMEOUT=30                                # 请求超时（秒）
DINGJIE_VERIFY_SSL=1                              # 是否验证 SSL
DINGJIE_LOCALE=zh_CN                              # 语言

# === MCP 配置 ===
MCP_MODE=readwrite                                # readonly / readwrite
MCP_API_KEY=                                      # SSE/HTTP 模式 API Key
MCP_LOG_LEVEL=INFO                                # 日志级别
MCP_LOG_FILE=                                     # 日志文件路径
MCP_RATE_LIMIT=60                                 # 速率限制（请求/分钟）
```

### 6.2 客户端配置

**Claude Desktop** (`claude_desktop_config.json`)：

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

**Claude Code** (`.mcp.json`)：

```json
{
  "mcpServers": {
    "dingjie-erp": {
      "command": "uvx",
      "args": ["dingjie-erp-mcp"],
      "env": {
        "DINGJIE_SERVER_URL": "https://erp.company.com/",
        "DINGJIE_APP_ID": "your_app_id",
        "DINGJIE_APP_SECRET": "your_app_secret",
        "MCP_MODE": "readonly"
      }
    }
  }
}
```

---

## 七、错误处理

### 7.1 错误类型

| 错误 | 处理方式 |
|------|----------|
| 认证失败 | 抛出异常，提示检查凭证 |
| 会话过期 | 自动重新认证（参考 kingdee-k3cloud-mcp） |
| 网络超时 | 重试（指数退避，最多 3 次） |
| ERP 业务错误 | 透传错误信息 |
| 速率限制 | 返回 429 状态码 |
| 字段验证失败 | 返回友好的错误提示 |

### 7.2 错误响应格式

```json
{
  "error": true,
  "message": "供应商编号 SUP001 不存在",
  "code": "BUSINESS_ERROR",
  "details": {
    "field": "supplier_no",
    "value": "SUP001"
  }
}
```

---

## 八、性能优化

### 8.1 查询优化

| 优化项 | 实现方式 | 参考 |
|--------|----------|------|
| 自动翻页 | `query_bill_all` 工具 | kingdee-k3cloud-mcp |
| 日期分片 | `query_bill_range` 工具 | kingdee-k3cloud-mcp |
| 流式导出 | `query_bill_to_file` 工具 | kingdee-k3cloud-mcp |
| 查询预检 | `count_bill` 估算行数 | kingdee-k3cloud-mcp |

### 8.2 连接优化

| 优化项 | 实现方式 |
|--------|----------|
| 连接复用 | requests.Session |
| 请求超时 | 默认 30 秒 |
| SSL 缓存 | Session 级别 |

---

## 九、测试策略

### 9.1 测试层次

| 层次 | 工具 | 覆盖范围 |
|------|------|----------|
| 单元测试 | pytest | SDK 客户端、工具逻辑 |
| 集成测试 | pytest + mock | ERP API 调用 |
| 端到端测试 | MCP Inspector | 完整流程 |
| 冒烟测试 | 手动 | 与真实 ERP 联调 |

### 9.2 Mock 策略

```python
# tests/conftest.py
import pytest
from unittest.mock import MagicMock

@pytest.fixture
def mock_client():
    client = MagicMock(spec=DingjieClient)
    client.query_purchase_receipts.return_value = {
        "rows": [...],
        "row_count": 10,
    }
    return client
```

---

## 十、部署方案

### 10.1 本地使用（stdio）

```bash
uvx dingjie-erp-mcp
```

### 10.2 远程共享（SSE/HTTP）

```bash
DINGJIE_SERVER_URL=... \
DINGJIE_APP_ID=... \
DINGJIE_APP_SECRET=... \
MCP_API_KEY=your-mcp-api-key \
uvx dingjie-erp-mcp --transport sse --port 8080
```

### 10.3 Docker

```dockerfile
FROM python:3.12-slim
RUN pip install dingjie-erp-mcp
ENTRYPOINT ["dingjie-erp-mcp"]
```

```bash
docker run -i --rm \
  -e DINGJIE_SERVER_URL \
  -e DINGJIE_APP_ID \
  -e DINGJIE_APP_SECRET \
  dingjie-erp-mcp
```
