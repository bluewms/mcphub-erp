# 企业管理软件 MCP 标准服务规范

> 以 Odoo MCP Server 的实际实现为基准。标准定在"跳一跳够得着"的水平，
> 不追求完美，确保鼎捷、金蝶、Salesforce 等连接器能在合理工作量内达标。

## 目的

本规范用于指导 Odoo、金蝶、鼎捷、用友、SAP、Salesforce、自研 ERP、WMS、MES、CRM、OA、财务系统等企业管理软件 MCP Server 的统一开发。

统一标准后，MCPHub 可以用同一套方式管理不同系统：

- 安装和配置。
- 启停和健康检查。
- 工具发现。
- 只读/读写模式控制。
- Group 权限和 Tool 风险治理。
- 审计和人工审批。

## 适用范围

适用于所有企业管理软件 MCP Server，包括：

- ERP：Odoo、金蝶、鼎捷、用友、SAP、自研 ERP。
- WMS：仓储、库存、出入库、批次、条码。
- MES：工单、工序、报工、设备、质检。
- CRM：客户、商机、合同、回款。
- OA：流程、审批、组织、人员。
- 财务：凭证、应收、应付、费用、报表。

## 设计原则

- **默认只读**：连接器默认不允许写入，需显式开启。
- **最小权限**：ERP 集成账号只授予业务必需权限。
- **可解释**：每个工具名、描述、参数都要让 AI 和人能理解。
- **可审计**：写入操作应可留下审计记录（opt-in）。
- **可降级**：ERP 不可用时返回错误信息，不让 AI 猜测。
- **不暴露任意代码执行**：禁止暴露可执行任意 SQL、脚本或代码的工具。

## Server 命名规范

服务器名称格式：

```text
{client}-{system}-{env}
```

推荐示例：

```text
client-a-odoo-prod
client-a-kingdee-prod
client-b-dingjie-staging
internal-sap-dev
```

字段说明：

- `client`：客户或租户标识。
- `system`：系统类型，例如 `odoo`、`kingdee`、`dingjie`、`yonyou`、`sap`、`salesforce`、`wms`。
- `env`：环境，例如 `prod`、`staging`、`dev`、`test`。

## 必备启动参数

所有 MCP Server 必须支持以下环境变量：

```text
MCP_MODE=readonly|readwrite      # 读写模式，默认 readonly
MCP_LOG_LEVEL=INFO               # 日志级别
```

各 ERP 自身的连接参数（如 URL、账号、密钥）通过各自的环境变量配置，命名前缀建议与系统一致：

```text
# 鼎捷
DINGJIE_SERVER_URL / DINGJIE_KEY / DINGJIE_ENT_ID / DINGJIE_COMPANY_ID

# 金蝶
KD_SERVER_URL / KD_ACCT_ID / KD_USERNAME / KD_APP_ID / KD_APP_SEC

# Odoo
ODOO_URL / ODOO_DB / ODOO_USERNAME / ODOO_PASSWORD（或 odoo_config.json）

# Salesforce
SALESFORCE_ACCESS_TOKEN / SALESFORCE_INSTANCE_URL
```

要求：

- `MCP_MODE` 默认值必须是 `readonly`。
- 当 `MCP_MODE=readonly` 时，写入、审核、删除工具必须不可执行（注册了也返回错误）。
- 密钥、密码、Token 不得打印到日志。

### 可选参数

以下参数为推荐支持，非强制：

```text
MCP_AUDIT_LOG=/path/to/audit.jsonl   # 审计日志文件路径，不设置则不记录
MCP_API_KEY=your-secret-key          # SSE/HTTP 模式下的 Bearer Token 鉴权
```

## 版本识别（推荐，非强制）

连接器应尽量在 `health_check` 中返回 ERP 实际版本，但不强制要求版本兼容矩阵。

最低要求：

- `health_check` 返回中尽量包含 `erp_version` 字段（能获取到的话）。
- 如果无法自动获取版本，可以不返回，不影响合规。

示例（Odoo 实现）：

```json
{
  "server_version": "18.0",
  "transport": "xmlrpc"
}
```

各 ERP 版本差异由工具描述和 `query_metadata` 体现，不强制做版本兼容检查。

## 必备工具

每个 MCP Server 必须实现以下 3 个工具。

### health_check

用途：检查 MCP Server 自身状态和 ERP 连接是否可用。

输出（参考 Odoo 实现，保持简单）：

```json
{
  "success": true,
  "server": {
    "name": "odoo-mcp",
    "mode": "readonly",
    "tool_count": 39
  },
  "erp": {
    "reachable": true,
    "version": "18.0"
  }
}
```

要求：

- 必须返回 `success` 字段。
- 必须返回当前 `mode`（readonly/readwrite）。
- 尽量检查 ERP 连接是否可达，无法检查时返回 `reachable: unknown`。
- 失败时返回 `{"success": false, "error": "错误描述"}`。

### query_metadata

用途：查询业务对象字段、类型等信息，帮助 AI 构造正确参数。

输入：

```json
{
  "object": "purchase_receipt"
}
```

输出（字段信息，格式可以灵活适配各 ERP）：

```json
{
  "object": "purchase_receipt",
  "fields": [
    {"name": "doc_no", "type": "string", "desc": "单号"},
    {"name": "supplier_no", "type": "string", "desc": "供应商编号", "required": true},
    {"name": "doc_date", "type": "date", "desc": "单据日期"}
  ]
}
```

要求：

- 返回字段名、类型、说明。
- 如果该 ERP 能获取必填信息，应返回 `required` 标记。
- 不同 ERP 的元数据格式可能不同，不需要完全统一，但要包含字段名和类型。

### preview_write（写入预览）

用途：对写入操作进行执行前预览，让 AI 和人确认将要发生的变更。

> 对应 Odoo 的 `preview_write` 工具。如果连接器暂时无法实现完整的 preview，
> 至少在写入工具的描述中说明风险，并支持只读模式拦截。

输入：

```json
{
  "object": "purchase_receipt",
  "operation": "create",
  "values": {"supplier_no": "S001", "doc_date": "2026-06-19"}
}
```

输出：

```json
{
  "success": true,
  "operation": "create",
  "object": "purchase_receipt",
  "summary": "将创建采购入库单，供应商 S001，1 条明细",
  "risk": "write",
  "warnings": []
}
```

要求：

- 只读模式下 `preview_write` 仍可调用（它不修改数据）。
- 返回操作摘要，让 AI 和人理解将要发生什么。

## 推荐工具（非强制）

以下工具为推荐实现，有助于提升体验和治理能力：

### get_profile

返回 MCP Server 的身份和配置信息。参考 Odoo 的 `get_odoo_profile`。

```json
{
  "success": true,
  "url": "https://erp.example.com",
  "database": "OLS",
  "username": "admin",
  "transport": "xmlrpc",
  "server_version": "18.0"
}
```

### list_capabilities

声明支持的业务对象和操作，便于 MCPHub 做工具治理。

```json
{
  "capabilities": [
    {"object": "purchase_receipt", "operations": ["query", "read", "create", "approve", "delete"]},
    {"object": "sales_issue", "operations": ["query", "read", "create", "approve", "delete"]},
    {"object": "material", "operations": ["query", "read"]}
  ]
}
```

## 工具分类与目录结构

### 设计原则

- **server.py 只做入口**：FastMCP 实例创建、环境初始化、参数解析、启动。不定义业务工具。
- **必备工具独立成模块**：`health_check`、`query_metadata`、`preview_write` 放入 `tools/essential.py`，不与业务工具混放。
- **函数式注册**：每个工具模块导出 `register_xxx_tools(mcp, ctx)` 函数，由 `tools/__init__.py` 统一调用。不依赖 import 副作用。
- **工具注解统一**：所有工具必须标注风险等级注解（见下文）。

### 标准目录结构

```text
src/{erp}_mcp/
├── __init__.py
├── server.py                # 入口：FastMCP 实例、setup()、main()，不定义业务工具
├── tools/
│   ├── __init__.py          # register_all_tools(mcp, ctx) — 汇总注册
│   ├── essential.py         # 必备工具：health_check, query_metadata, preview_write
│   ├── profile.py           # 推荐工具：get_profile, list_capabilities
│   ├── query.py             # 查询列表类工具（分页、过滤、批量导出）
│   ├── read.py              # 读取单条详情类工具
│   ├── write.py             # 写入类工具（create/update/approve/delete/push 等）
│   └── {business_object}.py # 业务对象专属工具（可选，见下文分类策略）
├── sdk/                     # ERP SDK 封装（如有）
│   └── __init__.py
└── utils.py                 # 公共辅助函数：_ok/_err/_paginate 等
```

### 分类策略

根据 ERP API 风格选择分类方式：

**方式一：功能领域分类（适合通用 API 的 ERP）**

当 ERP 的 API 是通用的（如金蝶的 `BillQuery(form_id, ...)`、Odoo 的 `model.search/read`、Salesforce 的 SOQL），工具不绑定特定业务对象，按功能领域分文件：

```text
tools/
├── essential.py     # health_check, query_metadata, preview_write
├── profile.py       # get_profile
├── query.py         # query_bill, count_bill, query_bill_all, query_bill_to_file, query_bill_range
├── read.py          # view_bill
└── write.py         # save_bill, submit_bill, audit_bill, delete_bill, push_bill
```

适用系统：金蝶、Odoo、SAP、Salesforce。

**方式二：业务对象分类（适合按对象封装 API 的 ERP）**

当 ERP 的 API 按业务对象独立封装（如鼎捷的 `create_purchase_receipt` / `query_sales_issues`），每个业务对象一个文件，包含完整 CRUD 工具链：

```text
tools/
├── essential.py           # health_check, query_metadata, preview_write
├── profile.py             # get_profile
├── purchase_receipt.py    # query/read/create/approve/disapprove/delete/invalid
├── sales_issue.py         # query/read/create/approve/disapprove/delete/invalid
└── material.py            # query/read
```

适用系统：鼎捷、用友、自研 ERP。

### 工具注解标准

所有工具必须使用 MCP 工具注解（`annotations`）标注风险等级，便于 MCPHub 做权限治理和 Group 分组。

三种注解常量（定义在 `server.py` 或 `utils.py` 中）：

```python
from mcp.types import ToolAnnotations

READ_ONLY_TOOL = ToolAnnotations(readOnlyHint=True, destructiveHint=False)
PREVIEW_TOOL = ToolAnnotations(readOnlyHint=True, destructiveHint=False)
WRITE_TOOL = ToolAnnotations(readOnlyHint=False, destructiveHint=False)
DESTRUCTIVE_TOOL = ToolAnnotations(readOnlyHint=False, destructiveHint=True)
```

使用方式（FastMCP）：

```python
@mcp.tool(annotations=READ_ONLY_TOOL)
def query_bill(...):
    ...

@mcp.tool(annotations=DESTRUCTIVE_TOOL)
def delete_bill(...):
    ...
```

风险等级映射：

| 注解 | 对应风险等级 | 适用工具 | 只读模式可用 |
|------|:---:|:---|:---:|
| `READ_ONLY_TOOL` | read | query/read/count/metadata/profile | 是 |
| `PREVIEW_TOOL` | read | preview_write（不修改数据） | 是 |
| `WRITE_TOOL` | write | create/update/approve/disapprove/push | 否 |
| `DESTRUCTIVE_TOOL` | danger | delete/invalid | 否 |

### 注册方式标准

统一使用函数式注册，不依赖 import 副作用。

每个工具模块导出 `register_xxx_tools(mcp, ctx)` 函数：

```python
# tools/query.py

def register_query_tools(mcp, ctx):
    """注册查询类工具。

    Args:
        mcp: FastMCP 实例
        ctx: ToolContext，包含 get_client/is_readonly/ok_fn/err_fn 等回调
    """

    @mcp.tool(annotations=READ_ONLY_TOOL)
    def query_bill(form_id: str, field_keys: str, ...):
        """查询单据数据。只读工具。"""
        sdk = ctx.get_sdk()
        ...
        return ctx.ok(result)
```

`tools/__init__.py` 汇总注册：

```python
# tools/__init__.py

from dataclasses import dataclass
from .essential import register_essential_tools
from .profile import register_profile_tools
from .query import register_query_tools
from .read import register_read_tools
from .write import register_write_tools


@dataclass
class ToolContext:
    """工具注册上下文，传递给每个 register 函数。"""
    get_sdk: callable        # 获取 SDK 实例
    is_readonly: callable    # 检查是否只读模式
    ok: callable             # 构造成功返回
    err: callable            # 构造错误返回
    server_name: str         # 服务器名称


def register_all_tools(mcp, ctx: ToolContext):
    """注册所有 MCP 工具。"""
    register_essential_tools(mcp, ctx)
    register_profile_tools(mcp, ctx)
    register_query_tools(mcp, ctx)
    register_read_tools(mcp, ctx)
    register_write_tools(mcp, ctx)
```

`server.py` 调用注册：

```python
# server.py

mcp = FastMCP("kingdee-k3cloud")

def main():
    ...
    setup()
    from .tools import register_all_tools, ToolContext
    ctx = ToolContext(
        get_sdk=_sdk,
        is_readonly=lambda: _readonly,
        ok=_ok,
        err=_err,
        server_name="kingdee-k3cloud",
    )
    register_all_tools(mcp, ctx)
    mcp.run(transport=args.transport)
```

## 工具命名规范

统一使用小写蛇形命名。

推荐动词：

```text
query_*        查询列表，支持分页、过滤
read_*         读取单条记录详情
search_*       模糊搜索
count_*        统计数量
create_*       新建
update_*       修改
approve_*      审核
disapprove_*   反审核
delete_*       删除
invalid_*      作废
```

推荐对象名：

```text
customer
supplier
material
product
warehouse
inventory
purchase_order
purchase_receipt
sales_order
sales_issue
invoice
payment
voucher
```

示例：

```text
query_materials
read_material
query_purchase_receipts
read_purchase_receipt
create_purchase_receipt
approve_purchase_receipt
```

要求：

- 工具名应包含业务对象，避免纯通用名如 `run`、`execute`、`do_action`。
- 如果 ERP 的 API 是通用的（如金蝶的 `BillQuery`、Salesforce 的 SOQL），应在工具名中体现用途，如 `query_bill`、`run_soql_query`。

## 工具描述规范

每个工具描述应包含：

- 业务对象和操作类型。
- 是否只读。
- 重要限制。

示例：

```text
查询物料主数据列表。只读工具。支持按编码、名称筛选，返回分页结果。
```

写入工具示例：

```text
创建采购入库单。写入工具，只读模式下不可用。执行前建议先调用 preview_write 预览变更。
```

## 输入参数规范

### 查询类工具

应支持分页和基本过滤：

```json
{
  "filters": {"doc_no": "PR2026"},
  "limit": 50,
  "offset": 0
}
```

要求：

- `limit` 必须有上限（建议默认 50-100，最大 200）。
- 日期字段使用 ISO 8601 字符串（YYYY-MM-DD）。

### 写入类工具

写入工具在只读模式下必须返回错误。

推荐支持预览机制：

- 方式一（推荐）：提供 `preview_write` 工具，先预览再执行。
- 方式二（简化）：写入工具描述中说明风险，由 MCPHub Group 控制可见性。

批量写入应限制最大条数（建议 100 条）。

## 返回结果规范

### 成功返回

```json
{
  "success": true,
  "data": {}
}
```

查询列表可以简化为直接返回数据数组或带分页信息的对象：

```json
{
  "items": [],
  "total": 120,
  "limit": 50,
  "offset": 0
}
```

写入返回：

```json
{
  "success": true,
  "record_id": "PR202606190001"
}
```

### 错误返回

统一使用简单格式（参考 Odoo 实现）：

```json
{
  "success": false,
  "error": "ERP 认证失败，请检查账号配置"
}
```

要求：

- `error` 为人类可读的中文描述。
- 不要把 ERP 原始异常堆栈直接返回给 AI。
- 不要在错误信息中暴露密钥、Token。

## 风险等级

工具按风险分为三类（简化版，用于 MCPHub Group 管理）：

```text
read       查询、读取、元数据 — 只读 Group 可用
write      新建、修改、审核、反审核 — 需写入 Group
danger     删除、作废、批量操作 — 需独立高危 Group
```

默认策略：

- `read` 工具在只读模式下可用。
- `write` 工具在只读模式下返回错误，需 `MCP_MODE=readwrite`。
- `danger` 工具建议独立授权，MCPHub 管理员放入独立 Group。

## 写入控制和审批

### 只读模式

- `MCP_MODE=readonly` 时，所有写入工具返回 `{"success": false, "error": "只读模式：写入操作已禁用"}`。
- 写入工具可以注册但不可执行，返回明确错误信息。

### 写入三段式（推荐）

参考 Odoo 的实现，推荐写入操作使用三段式：

```text
preview_write  →  validate_write  →  execute_approved_write
```

- `preview_write`：预览将要发生的变更，不修改数据。
- `validate_write`：校验字段和权限，生成审批 token。
- `execute_approved_write`：凭 token 执行实际写入。

审批 token 有有效期（Odoo 默认 10 分钟），过期需重新预览。

如果三段式实现成本高，可以简化为：

- 只读模式拦截 + 工具描述标注风险。
- 由 MCPHub 的 Group 权限控制写入工具的可见性。

### 删除控制

删除工具（`delete_*`）属于高风险操作：

- 只读模式下不可执行。
- 建议通过独立环境变量或配置控制（如 Odoo 的 `ODOO_MCP_ENABLE_WRITES`）。
- MCPHub 管理员应把删除工具放入独立高危 Group。
- 删除工具描述应说明："删除操作可能不可恢复"。

## 审计日志（推荐，非强制）

推荐支持审计日志，但非强制要求。

### 实现方式（参考 Odoo）

通过环境变量开启，不设置则不记录（opt-in）：

```text
MCP_AUDIT_LOG=/path/to/audit.jsonl
```

审计日志为 JSONL 格式（每行一条），追加写入：

```json
{
  "timestamp": "2026-06-19T10:00:00Z",
  "event": "write",
  "operation": "create",
  "object": "purchase_receipt",
  "record_id": "PR202606190001",
  "outcome": "success"
}
```

要求：

- 只记录写入操作（create/update/delete/approve 等）。
- 不记录明文密码、Token、API Key。
- 审计失败不应阻断业务操作（fail-open）。

## 分页规范

查询工具必须支持分页。

默认限制：

```text
limit 默认 50
limit 最大 200
批量写入最大 100 条
```

不同 ERP 的分页参数可以不同（如鼎捷用 `limit/offset`，金蝶用 `start_row/top_count`），但必须支持翻页。

大数据量导出建议提供落盘工具（参考金蝶的 `query_bill_to_file`）。

## 安全规范

- 默认只读。
- **禁止暴露可执行任意代码的工具**（如任意 SQL 执行、任意脚本执行、任意 REST 调用）。
- 不允许把 ERP 原始异常堆栈直接返回给 AI。
- 不允许日志输出密钥。
- 所有 HTTP 请求必须设置超时。

## Tool Schema 规范

每个工具应提供参数描述：

- 参数应有 `description`。
- 必填参数应在描述中说明。
- 使用 FastMCP 时，通过函数签名和 docstring 自动生成 Schema。

## 连接器 manifest（产品化阶段）

产品化阶段，每个 MCP Server 仓库建议提供 `mcp-connector.json`，用于 MCPHub 模板安装：

```json
{
  "name": "kingdee-k3cloud",
  "display_name": "金蝶云星空",
  "description": "金蝶云星空 K3Cloud MCP Server",
  "command": "uv",
  "args": ["run", "--directory", "${__dirname}", "kingdee-k3cloud-mcp"],
  "arguments": {
    "KD_SERVER_URL": {"label": "金蝶服务器地址", "required": true, "secret": false},
    "KD_ACCT_ID": {"label": "账套 ID", "required": true, "secret": false},
    "KD_APP_SEC": {"label": "应用密钥", "required": true, "secret": true}
  },
  "health_check_tool": "health_check",
  "default_mode": "readonly"
}
```

## 开发验收清单

一个新的企业管理软件 MCP Server 交付前必须满足：

### 强制项

- [ ] 可以通过 stdio 启动。
- [ ] 支持 `MCP_MODE=readonly`，默认只读。
- [ ] 实现 `health_check` 工具。
- [ ] 实现 `query_metadata` 工具。
- [ ] 只读模式下写入工具返回错误。
- [ ] 工具名包含业务对象，避免纯通用名。
- [ ] 查询工具支持分页（有 limit 上限）。
- [ ] 错误返回 `{"success": false, "error": "描述"}` 格式。
- [ ] 不打印密钥到日志。
- [ ] 不暴露可执行任意代码的工具。
- [ ] 工具按功能领域或业务对象分文件组织，不全部堆在 `server.py`。
- [ ] 必备工具放入 `tools/essential.py`，`server.py` 只做入口。
- [ ] 使用函数式注册（`register_xxx_tools(mcp, ctx)`），不依赖 import 副作用。
- [ ] 所有工具标注风险等级注解（`READ_ONLY_TOOL` / `WRITE_TOOL` / `DESTRUCTIVE_TOOL`）。

### 推荐项

- [ ] 实现 `preview_write`（写入预览）。
- [ ] 支持 `MCP_AUDIT_LOG` 审计日志。
- [ ] 删除工具有独立控制（不随 readwrite 自动开放）。
- [ ] `health_check` 返回 ERP 版本信息。
- [ ] 实现 `get_profile` 工具。
- [ ] README 包含 MCPHub 接入示例。

## 推荐 README 模板

每个连接器 README 至少包含：

```text
# {系统名} MCP Server

## 功能
## 安装方式
## MCPHub 配置示例
## 环境变量
## 工具列表
## 只读模式说明
## 写入和风险说明
```

## 版本管理

连接器版本使用语义化版本：

```text
connector_version: MAJOR.MINOR.PATCH
```

破坏性变更（需提升主版本号）：

- 删除工具或改变工具参数含义。
- 修改返回结构。
- 写入工具默认策略发生变化。
