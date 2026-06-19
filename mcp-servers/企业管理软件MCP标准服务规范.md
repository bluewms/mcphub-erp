# 企业管理软件 MCP 标准服务规范

## 目的

本规范用于指导 Odoo、金蝶、鼎捷、用友、SAP、自研 ERP、WMS、MES、CRM、OA、财务系统等企业管理软件 MCP Server 的统一开发。

统一标准后，MCPHub 可以用同一套方式管理不同系统：

- 安装和配置。
- 启停和健康检查。
- 工具发现和能力展示。
- 只读/读写模式控制。
- Group 权限和 Tool 风险治理。
- 审计、日志、告警和人工审批。

## 适用范围

适用于所有企业管理软件 MCP Server，包括：

- ERP：Odoo、金蝶、鼎捷、用友、SAP、自研 ERP。
- WMS：仓储、库存、出入库、批次、条码。
- MES：工单、工序、报工、设备、质检。
- CRM：客户、商机、合同、回款。
- OA：流程、审批、组织、人员。
- 财务：凭证、应收、应付、费用、报表。

## 设计原则

- 默认只读：任何新连接器默认不允许写入。
- 最小权限：ERP 集成账号只授予业务必需权限。
- 可解释：每个工具名、描述、参数、返回值都要让 AI 和人能理解。
- 可治理：每个工具必须能归类到业务域、读写属性和风险等级。
- 可审计：所有写入、审批、删除、批量操作必须留下审计事件。
- 可降级：ERP 不可用时返回结构化错误，不让 AI 猜测。
- 可扩展：不同 ERP 的差异通过元数据和能力清单暴露，不硬编码到 MCPHub。
- 可兼容：同一企业软件不同版本的 API、字段、流程差异必须被显式声明和检测。
- 删除默认关闭：删除能力不得随读写模式自动开放，必须单独启用、单独授权、单独审计。

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
- `system`：系统类型，例如 `odoo`、`kingdee`、`dingjie`、`yonyou`、`sap`、`wms`。
- `env`：环境，例如 `prod`、`staging`、`dev`、`test`。

## 必备启动参数

所有 MCP Server 必须支持以下环境变量或等价启动参数：

```text
MCP_MODE=readonly|readwrite
MCP_SERVER_NAME=client-a-odoo-prod
MCP_CLIENT_ID=client-a
MCP_ENV=prod|staging|dev|test
MCP_LOCALE=zh_CN
MCP_TIMEZONE=Asia/Shanghai
MCP_AUDIT_LOG=/path/to/audit.jsonl
MCP_LOG_LEVEL=INFO
MCP_ALLOWED_TOOLS=query_*,read_*
MCP_DENIED_TOOLS=delete_*,danger_*
MCP_ERP_VERSION=auto
MCP_ENABLE_DELETE=false
```

要求：

- `MCP_MODE` 默认值必须是 `readonly`。
- 当 `MCP_MODE=readonly` 时，写入、审批、删除、作废、批量更新工具必须不可执行。
- `MCP_ENABLE_DELETE` 默认值必须是 `false`。
- 即使 `MCP_MODE=readwrite`，只要 `MCP_ENABLE_DELETE` 不是显式 true，删除工具也必须不可执行。
- `MCP_ERP_VERSION=auto` 表示启动后通过 ERP API 自动识别版本；无法自动识别时必须允许人工配置。
- `MCP_ALLOWED_TOOLS` 和 `MCP_DENIED_TOOLS` 用于快速限制工具范围。
- 密钥、密码、Token 不得打印到日志。

## 企业软件版本规范

企业管理软件通常存在多版本、多补丁、多部署形态。连接器必须把版本作为一等治理对象处理。

必须支持：

- 自动识别 ERP 实际版本。
- 人工指定 ERP 版本。
- 声明连接器支持的版本范围。
- 声明当前版本下不可用或降级的工具。
- 在 `health_check` 和 `get_server_profile` 中返回版本兼容状态。

版本信息至少包含：

```json
{
  "product": "odoo",
  "edition": "enterprise",
  "version": "18.0",
  "build": "20260601",
  "api": {
    "protocol": "xmlrpc",
    "version": "1"
  },
  "compatibility": {
    "supported": true,
    "supported_versions": [">=16.0", "<=19.0"],
    "warnings": []
  }
}
```

版本差异示例：

- Odoo 16-18 通常使用 XML-RPC，Odoo 19+ 可能使用 JSON-2。
- 金蝶云星空不同版本和补丁可能存在字段标识、表单插件、审批流差异。
- 鼎捷 E10 不同客户环境可能有自定义单据、字段和接口扩展。
- SAP ECC 与 S/4HANA 的对象模型、接口协议和字段语义可能不同。
- 用友不同产品线和版本的 API、单据状态、组织账套模型可能不同。

如果版本不兼容：

- `health_check.ok` 可以为 true，但必须返回 `compatibility.supported=false`。
- 写入、审批、删除、批量操作必须默认禁用。
- 工具描述必须说明该工具在当前版本不可用或仅部分可用。
- 错误码建议使用 `ERP_VERSION_UNSUPPORTED` 或 `ERP_FEATURE_UNSUPPORTED`。

## 必备工具

每个企业管理软件 MCP Server 必须实现以下工具。

### health_check

用途：

检查 MCP Server 自身、ERP 连接、认证、账套、组织、基础权限是否可用。

输入：

```json
{
  "include_permissions": false,
  "include_latency": true
}
```

输出：

```json
{
  "ok": true,
  "server_name": "client-a-odoo-prod",
  "system": "odoo",
  "environment": "prod",
  "mode": "readonly",
  "erp": {
    "reachable": true,
    "authenticated": true,
    "version": "18.0",
    "company": "Client A",
    "compatibility": {
      "supported": true,
      "supported_versions": [">=16.0", "<=19.0"],
      "warnings": []
    }
  },
  "latency_ms": 120,
  "warnings": []
}
```

失败时必须返回结构化错误，不得只返回字符串。

### get_server_profile

用途：

让 MCPHub 或 AI 获取该 MCP Server 的身份、版本、业务域和治理信息。

输出：

```json
{
  "server_name": "client-a-odoo-prod",
  "standard_version": "1.0",
  "connector": {
    "system": "odoo",
    "name": "Odoo MCP",
    "version": "0.1.0"
  },
  "erp_version": {
    "product": "odoo",
    "edition": "enterprise",
    "version": "18.0",
    "api_protocol": "xmlrpc",
    "supported": true,
    "supported_versions": [">=16.0", "<=19.0"]
  },
  "tenant": {
    "client_id": "client-a",
    "environment": "prod"
  },
  "mode": "readonly",
  "supported_transports": ["stdio", "sse", "streamable-http"],
  "business_domains": ["master_data", "sales", "purchase", "inventory", "finance"],
  "risk_policy": {
    "default_risk": "read",
    "write_requires_approval": true,
    "delete_enabled": false,
    "danger_tools_disabled": true
  }
}
```

### list_capabilities

用途：

声明该 MCP Server 支持哪些业务对象、操作和风险等级。MCPHub 后续可用它做模板安装、权限展示和工具治理。

输出：

```json
{
  "capabilities": [
    {
      "domain": "inventory",
      "object": "material",
      "operations": ["query", "read"],
      "tools": ["query_materials", "read_material"],
      "risk": "read"
    },
    {
      "domain": "sales",
      "object": "sales_order",
      "operations": ["query", "read", "create", "approve"],
      "tools": ["query_sales_orders", "read_sales_order", "create_sales_order", "approve_sales_order"],
      "risk": "workflow",
      "requires_approval": true,
      "supported_versions": [">=8.0"],
      "version_notes": "不同版本的审批状态字段可能不同，执行前必须调用 query_metadata"
    }
  ]
}
```

### query_metadata

用途：

查询业务对象字段、类型、必填、枚举、关联关系和权限。AI 使用该工具构造正确参数，MCPHub 可用于展示表单。

输入：

```json
{
  "object": "sales_order",
  "include_fields": true,
  "include_enums": true,
  "include_permissions": true
}
```

输出：

```json
{
  "object": "sales_order",
  "display_name": "销售订单",
  "primary_key": "id",
  "fields": [
    {
      "name": "customer_id",
      "label": "客户",
      "type": "reference",
      "required": true,
      "readonly": false,
      "relation": "customer"
    },
    {
      "name": "order_date",
      "label": "订单日期",
      "type": "date",
      "required": true,
      "readonly": false
    }
  ],
  "permissions": {
    "query": true,
    "read": true,
    "create": false,
    "update": false,
    "delete": false,
    "approve": false
  }
}
```

### validate_operation

用途：

对写入、审核、删除、作废、批量变更进行执行前校验。

输入：

```json
{
  "operation": "approve",
  "object": "sales_order",
  "record_id": "SO202606190001",
  "payload": {}
}
```

输出：

```json
{
  "ok": true,
  "operation": "approve",
  "object": "sales_order",
  "record_id": "SO202606190001",
  "risk": "workflow",
  "requires_approval": true,
  "warnings": ["该订单审核后将影响可发货数量"],
  "approval_hint": "需要业务负责人确认"
}
```

## 工具命名规范

统一使用小写蛇形命名。

推荐动词：

```text
query_*        查询列表，支持分页、过滤、排序
read_*         读取单条记录详情
search_*       模糊搜索或智能搜索
count_*        统计数量
aggregate_*    分组汇总
create_*       新建
update_*       修改
submit_*       提交
approve_*      审核
disapprove_*   反审核
close_*        关闭
cancel_*       取消
invalid_*      作废
delete_*       删除
export_*       导出
import_*       导入
sync_*         同步
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
work_order
approval_task
```

示例：

```text
query_materials
read_material
query_purchase_orders
read_purchase_order
create_purchase_receipt
approve_purchase_receipt
query_sales_issues
read_sales_issue
```

禁止：

- 使用含糊名称，例如 `do_action`、`run`、`execute`。
- 一个工具承担多个不相关业务动作。
- 工具名里包含客户密钥、账套、组织等敏感信息。

## 工具描述规范

每个工具描述必须包含：

- 业务对象。
- 操作类型。
- 是否只读。
- 风险等级。
- 典型使用场景。
- 重要限制。

示例：

```text
查询物料主数据列表。只读工具，风险等级 read。支持按编码、名称、物料分类和启用状态过滤，返回分页结果。不会修改 ERP 数据。
```

写入工具示例：

```text
创建采购入库单。写入工具，风险等级 write。执行前应先调用 validate_operation 校验字段和权限。生产环境建议要求人工审批。
```

## 输入参数规范

查询类工具必须支持：

```json
{
  "filters": {},
  "fields": [],
  "page": 1,
  "page_size": 50,
  "sort": []
}
```

要求：

- `page_size` 必须有上限，默认不超过 50 或 100。
- `fields` 为空时返回业务常用字段。
- 日期字段使用 ISO 8601 字符串。
- 金额使用数字，返回时保留币种。
- 复杂过滤条件必须结构化，不建议让 AI 拼接 ERP 原生 SQL。

写入类工具必须支持：

```json
{
  "payload": {},
  "idempotency_key": "optional-client-generated-key",
  "dry_run": true
}
```

要求：

- 支持 `dry_run` 或先提供 `validate_operation`。
- 批量写入必须限制最大条数。
- 高风险操作必须有审批 token 或人工确认机制。

## 返回结果规范

查询列表返回：

```json
{
  "items": [],
  "page": 1,
  "page_size": 50,
  "total": 120,
  "has_more": true,
  "warnings": []
}
```

单条详情返回：

```json
{
  "item": {},
  "metadata": {
    "object": "sales_order",
    "record_id": "SO202606190001",
    "last_updated_at": "2026-06-19T10:00:00+08:00"
  },
  "warnings": []
}
```

写入返回：

```json
{
  "ok": true,
  "operation": "create",
  "object": "purchase_receipt",
  "record_id": "PR202606190001",
  "status": "draft",
  "audit_id": "audit-20260619-0001",
  "warnings": []
}
```

## 错误规范

所有错误必须结构化：

```json
{
  "ok": false,
  "error": {
    "code": "ERP_AUTH_FAILED",
    "message": "ERP authentication failed",
    "user_message": "ERP 认证失败，请检查账号、密钥或账套配置。",
    "retryable": false,
    "details": {
      "system": "kingdee",
      "server_name": "client-a-kingdee-prod"
    }
  }
}
```

推荐错误码：

```text
ERP_AUTH_FAILED
ERP_PERMISSION_DENIED
ERP_NOT_FOUND
ERP_VALIDATION_FAILED
ERP_VERSION_UNSUPPORTED
ERP_FEATURE_UNSUPPORTED
ERP_RATE_LIMITED
ERP_TIMEOUT
ERP_UNAVAILABLE
ERP_CONFLICT
ERP_WRITE_DISABLED
MCP_INVALID_ARGUMENT
MCP_TOOL_DENIED
MCP_APPROVAL_REQUIRED
MCP_INTERNAL_ERROR
```

## 风险等级规范

工具必须归入以下风险等级之一：

```text
metadata   元数据、能力清单、健康检查
read       查询、读取、搜索、统计、导出只读数据
write      新建、修改、保存草稿
workflow   提交、审核、反审核、下推、过账、关闭
danger     删除、作废、批量修改、不可逆操作
admin      系统配置、权限、凭据、同步任务、维护动作
```

默认策略：

- `metadata` 和 `read` 可进入只读 Group。
- `write` 只能进入业务写入 Group。
- `workflow` 必须独立授权，建议人工审批。
- `danger` 默认禁用。
- `admin` 只允许内部管理员使用。

## 删除权限规范

删除能力必须作为独立高风险能力治理，不能和普通读写权限混在一起。

默认要求：

- `delete_*` 工具默认不注册或默认不可执行。
- `MCP_ENABLE_DELETE=false` 时，所有删除工具必须返回 `MCP_TOOL_DENIED`。
- `MCP_MODE=readwrite` 不代表允许删除。
- `danger_tools_enabled=false` 时，删除、作废、批量修改、不可逆动作必须关闭。

开通删除权限必须满足：

- 管理员显式设置 `MCP_ENABLE_DELETE=true` 或等价配置。
- MCPHub 把删除工具放入独立 Group，例如 `client-a-delete-approved`。
- 开通界面必须提示风险：删除可能不可恢复，并可能影响财务、库存、审计和上下游单据。
- 调用删除工具前必须先调用 `validate_operation` 或 `preview_operation`。
- 执行删除必须要求人工审批、审批 token 或同等强确认。
- 删除操作必须写入审计日志。

删除工具返回的校验结果必须包含风险提示：

```json
{
  "ok": true,
  "operation": "delete",
  "object": "sales_order",
  "record_id": "SO202606190001",
  "risk": "danger",
  "requires_approval": true,
  "warnings": [
    "删除可能不可恢复",
    "删除可能影响库存、财务、审计和上下游单据"
  ]
}
```

删除工具描述必须明确写出：

```text
删除销售订单。危险工具，风险等级 danger。默认关闭。删除可能不可恢复，并可能影响库存、财务、审计和上下游单据。执行前必须调用 validate_operation，并需要人工审批。
```

## 审计规范

以下操作必须审计：

- create
- update
- submit
- approve
- disapprove
- close
- cancel
- invalid
- delete
- import
- sync
- admin

审计事件格式：

```json
{
  "audit_id": "audit-20260619-0001",
  "timestamp": "2026-06-19T10:00:00+08:00",
  "server_name": "client-a-odoo-prod",
  "client_id": "client-a",
  "system": "odoo",
  "tool": "approve_sales_order",
  "risk": "workflow",
  "object": "sales_order",
  "record_id": "SO202606190001",
  "actor": {
    "type": "mcp-client",
    "id": "ai-assistant-prod"
  },
  "input_summary": {
    "fields_changed": [],
    "record_count": 1
  },
  "result": {
    "ok": true,
    "status": "approved"
  }
}
```

要求：

- 不记录明文密码、Token、API Key。
- 对手机号、身份证、银行账号等敏感字段脱敏。
- 审计日志应可落地到文件、数据库或外部日志系统。

## 人工审批规范

高风险工具建议使用三段式：

```text
validate_operation -> preview_operation -> execute_operation
```

或按业务对象拆分：

```text
validate_sales_order_approval
preview_sales_order_approval
approve_sales_order
```

审批摘要必须包含：

- 操作对象。
- 记录编号。
- 影响字段。
- 风险等级。
- ERP 返回的业务提示。
- 是否可回滚。

## 分页和大数据规范

查询工具必须分页。

默认限制：

```text
page_size 默认 50
page_size 最大 200
导出最大行数默认 10000
批量写入最大条数默认 100
```

大数据导出建议提供：

```text
query_*_to_file
export_*_to_file
submit_async_task
get_async_task
```

返回大结果时，应优先返回文件路径、任务 ID 或摘要，避免一次性塞满上下文。

## 安全规范

- 默认只读。
- 不允许执行任意 SQL、任意 Python、任意 JavaScript。
- 不允许把 ERP 原始异常堆栈直接返回给 AI。
- 不允许日志输出密钥。
- 不允许绕过 ERP 权限系统。
- 所有 HTTP 请求必须设置超时。
- 所有写入工具必须幂等或支持 `idempotency_key`。
- 删除、作废、批量更新必须默认关闭；删除能力必须独立显式启用。

## Tool Schema 规范

每个工具必须提供完整 JSON Schema：

- 所有字段必须有 `description`。
- 必填字段必须放入 `required`。
- 枚举字段必须使用 `enum`。
- 数组必须限制最大条数。
- 字符串字段应声明格式，例如 `date`、`date-time`、`email`。

示例：

```json
{
  "type": "object",
  "properties": {
    "filters": {
      "type": "object",
      "description": "查询过滤条件"
    },
    "page": {
      "type": "integer",
      "description": "页码，从 1 开始",
      "minimum": 1,
      "default": 1
    },
    "page_size": {
      "type": "integer",
      "description": "每页数量，最大 200",
      "minimum": 1,
      "maximum": 200,
      "default": 50
    }
  }
}
```

## 连接器 manifest 建议

产品化阶段，每个 MCP Server 仓库建议提供 `mcp-connector.json`：

```json
{
  "name": "kingdee-k3cloud",
  "display_name": "金蝶云星空",
  "standard_version": "1.0",
  "description": "金蝶云星空 K3Cloud MCP Server",
  "supported_erp_versions": [">=8.0"],
  "version_detection": {
    "mode": "auto",
    "health_check_field": "erp.version"
  },
  "installations": {
    "uvx": {
      "command": "uvx",
      "args": ["kingdee-k3cloud-mcp"]
    }
  },
  "arguments": {
    "KD_SERVER_URL": {
      "label": "金蝶服务器地址",
      "required": true,
      "secret": false
    },
    "KD_ACCT_ID": {
      "label": "账套 ID",
      "required": true,
      "secret": false
    },
    "KD_USERNAME": {
      "label": "集成用户",
      "required": true,
      "secret": false
    },
    "KD_APP_ID": {
      "label": "应用 ID",
      "required": true,
      "secret": false
    },
    "KD_APP_SEC": {
      "label": "应用密钥",
      "required": true,
      "secret": true
    }
  },
  "health_check_tool": "health_check",
  "default_mode": "readonly",
  "business_domains": ["master_data", "sales", "purchase", "inventory", "finance"],
  "risk_defaults": {
    "delete_enabled": false,
    "danger_tools_enabled": false,
    "workflow_requires_approval": true
  }
}
```

## 开发验收清单

一个新的企业管理软件 MCP Server 交付前必须满足：

- 可以通过 stdio 启动。
- 支持 `MCP_MODE=readonly`。
- 支持 `health_check`。
- 支持 `get_server_profile`。
- 支持 `list_capabilities`。
- 支持 `query_metadata`。
- 能识别或配置企业软件版本。
- 能声明支持的企业软件版本范围。
- 版本不兼容时能禁用写入、审核、删除等高风险工具。
- 工具命名符合规范。
- 查询工具支持分页。
- 写入工具支持 validate 或 dry run。
- 高风险工具默认禁用或要求审批。
- 删除工具默认关闭，显式开启时必须有风险提示、人工审批和审计。
- 错误返回结构化 JSON。
- 不打印密钥。
- 有最小单元测试或模拟测试。
- README 包含 MCPHub 接入示例。

## 推荐 README 模板

每个连接器 README 至少包含：

```text
# {系统名} MCP Server

## 功能
## 支持的业务域
## 安装方式
## MCPHub 配置示例
## 环境变量
## 支持的软件版本
## 版本兼容说明
## 工具列表
## 权限和风险等级
## 只读模式
## 删除权限和风险提示
## 写入和审批说明
## 审计日志
## 故障排查
```

## 版本管理

标准版本使用语义化版本：

```text
standard_version: 1.0
connector_version: MAJOR.MINOR.PATCH
```

破坏性变更：

- 删除工具。
- 修改工具参数含义。
- 修改返回结构。
- 改变默认风险等级。
- 写入工具默认启用。
- 扩大或缩小支持的 ERP 版本范围。
- 删除能力默认策略发生变化。

发生破坏性变更必须提升主版本号。
