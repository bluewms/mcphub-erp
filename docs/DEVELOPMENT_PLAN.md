# 鼎捷 ERP MCP Server 开发规划

> 基于 2026-06-16/17 日的沟通讨论整理

---

## 一、项目背景

### 1.1 目标

开发一个基于 MCP (Model Context Protocol) 协议的鼎捷 ERP 集成服务，让 AI 助手（Claude Desktop、Claude Code、Cursor、Cline、OpenClaw 等）通过自然语言查询和操作鼎捷 ERP 系统。

### 1.2 鼎捷 ERP API 分析

根据提供的接口文档（`【振锋】WMS集成栏位对照清单_20260615.xlsx`、`采购入库.xlsx`、`销货出库.xlsx`），鼎捷 ERP 的 API 特征如下：

| 项目 | 说明 |
|------|------|
| **产品代号** | E10 |
| **技术类型** | RESTful API |
| **API 命名空间** | `e10.oapi.*` |
| **方法提供方** | E10 |
| **通信协议** | HTTPS (RESTful) |
| **数据格式** | JSON |

#### API 端点格式

```
POST/GET http://{server}/oapi/{对象路径}/{数据类型}/{操作}
```

#### 已识别的业务对象

| 对象名 | API 路径前缀 | 说明 |
|--------|-------------|------|
| PURCHASE_RECEIPT | `purchase/receipt` | 采购入库 |
| SALES_ISSUE | `sales/issue` | 销货出库 |
| ITEM | `material` | 物料（推断） |

#### 支持的 API 操作

| 操作 | 方法名称 | 说明 |
|------|----------|------|
| 创建 | `data.create` | 创建单据 |
| 审核 | `data.approve` | 审核单据 |
| 删除 | `data.delete` | 删除单据 |
| 撤销审核 | `data.disapprove` | 撤销审核 |
| 查询列表 | `list.data.query.get` | 查询单据列表 |
| 查询明细 | `details.data.read.get` | 查询单据明细 |
| 作废 | `data.invalid` | 作废单据 |

#### 字段命名规则

鼎捷 ERP 使用特殊的引用字段命名规则：

- `SUPPLIER_ID_SUPPLIER_CODE` → 报文字段 `supplier_no`（供应商编号）
- `WAREHOUSE_ID_WAREHOUSE_CODE` → 报文字段 `warehouse_no`（仓库编号）
- `DOC_ID_DOC_CODE` → 报文字段 `doc_type_no`（单据类型编号）
- `Owner_Org_PLANT_PLANT_CODE` → 报文字段 `om_site_id`（营运据点编号）

#### 采购入库单字段

**单头字段**：

| 报文字段 | E10 属性 | 类型 | 长度 | 说明 |
|----------|----------|------|------|------|
| doc_no | DOC_NO | String | 20 | 单号 |
| om_site_id | Owner_Org_PLANT_PLANT_CODE | String | 6 | 营运据点编号 |
| doc_type_no | DOC_ID_DOC_CODE | String | 4 | 单据类型编号 |
| doc_date | DOC_DATE | Date | - | 单据日期 |
| responsibility_employee_no | Owner_Emp_EMPLOYEE_CODE | String | 40 | 负责人员编号 |
| department_no | Owner_Dept_ADMIN_UNIT_CODE | String | 40 | 部门编号 |
| supplier_no | SUPPLIER_ID_SUPPLIER_CODE | String | 40 | 供应商编号 |
| teamwork_no | GROUP_SYNERGY_ID_SUPPLY_SYNERGY_SUPPLY_SYNERGY_CODE | String | 40 | 整单协同关系编号 |
| final_supplier_no | SOURCE_SUPPLIER_ID_SUPPLIER_CODE | String | 40 | 最终供应商编号 |
| remark | REMARK | String | 255 | 备注 |

**单身字段**：

| 报文字段 | E10 属性 | 类型 | 说明 |
|----------|----------|------|------|
| seq_no | SequenceNumber | Int32 | 序号 |
| source_doc_seq | SOURCE_ID_SequenceNumber | Int32 | 来源序号 |
| source_doc_no | SOURCE_ID_Parent_DOC_NO | String(20) | 来源单号 |
| business_qty | BUSINESS_QTY | Decimal(16,6) | 业务数量 |
| return_business_qty | RETURN_BUSINESS_QTY | Decimal(16,6) | 拒收业务数量 |
| scrap_business_qty | SCRAP_BUSINESS_QTY | Decimal(16,6) | 报废业务数量 |
| warehouse_no | WAREHOUSE_ID_WAREHOUSE_CODE | String(10) | 仓库编号 |
| storage_spaces_no | BIN_ID_BIN_CODE | String(10) | 库位编号 |
| lot_no | ITEM_LOT_ID_LOT_CODE | String(30) | 批号 |
| remark | REMARK | String(255) | 备注 |

#### 销货出库单字段

**单头字段**：

| 报文字段 | E10 属性 | 类型 | 说明 |
|----------|----------|------|------|
| doc_no | DOC_NO | String(20) | 单号 |
| doc_date | DOC_DATE | Date | 单据日期 |
| customer_no | SHIP_TO_CUSTOMER_ID_CUSTOMER_CODE | String(40) | 客户编号 |
| doc_type_no | DOC_ID_DOC_CODE | String(4) | 单据类型编号 |
| administration_unit_no | Owner_Dept_ADMIN_UNIT_CODE | String(40) | 仓管部门编号 |
| employee_no | Owner_Emp_EMPLOYEE_CODE | String(40) | 仓管员编号 |
| om_site_id | Owner_Org_PLANT_PLANT_CODE | String(6) | 营运据点编号 |
| remark | REMARK | String(255) | 备注 |

**单身字段**：

| 报文字段 | E10 属性 | 类型 | 说明 |
|----------|----------|------|------|
| seq | SequenceNumber | Int32 | 序号 |
| sales_delivery_seq | SOURCE_ID_SALES_DELIVERY_SALES_DELIVERY_D_SequenceNumber | Int32 | 来源序号 |
| sales_delivery_no | SOURCE_ID_SALES_DELIVERY_SALES_DELIVERY_D_Parent_DOC_NO | String(20) | 来源单号 |
| business_qty | BUSINESS_QTY | Decimal(16,6) | 业务数量 |
| warehouse_no | WAREHOUSE_ID_WAREHOUSE_CODE | String(10) | 仓库编号 |
| storage_spaces_no | BIN_ID_BIN_CODE | String(10) | 库位编号 |
| lot_no | ITEM_LOT_ID_LOT_CODE | String(30) | 批号 |
| remark | REMARK | String(255) | 备注 |
| second_qty | SECOND_QTY | Decimal(16,6) | 第二数量 |

#### 物料同步字段

| 报文字段 | E10 属性 | 类型 | 必填 | 说明 |
|----------|----------|------|------|------|
| code | ITEM_CODE | String | 是 | 产品编码 |
| name | ITEM_NAME | String | 是 | 产品名称 |
| spec | ITEM_SPEC | String | 否 | 规格 |
| unit_no | UNIT_ID_UNIT_CODE | String | 是 | 单位编号 |
| item_type | ITEM_TYPE | String | 否 | 品号属性 |

---

## 二、技术选型分析

### 2.1 参考项目对比

我们对比了三个 MCP 项目：

| 维度 | mcp-odoo | kingdee-k3cloud-mcp | muk_mcp (Odoo 模块) |
|------|----------|---------------------|---------------------|
| **集成方式** | 外部 MCP Server | 外部 MCP Server | Odoo 原生模块 |
| **通信协议** | XML-RPC / JSON-2 | Web API SDK | 直接访问 ORM |
| **代码量** | ~5000+ 行 (30+ 文件) | ~950 行 (1 文件) | ~2000+ 行 (9 文件) |
| **MCP 框架** | 低级 mcp 库 | FastMCP | 手动实现 |
| **模块化** | 紧耦合 | 单文件 | 清晰分离 |
| **安全控制** | 字段级 ACL、审计 | 只读模式 | API Key、Scope、速率限制 |
| **会话管理** | ❌ | ✅ 自动恢复 | ✅ 完整会话管理 |
| **Web UI** | ❌ | ❌ | ✅ Playground |

### 2.2 选型决策

**选择方案：外部 MCP Server（基于 kingdee-k3cloud-mcp 架构，借鉴 muk_mcp 优点）**

理由：

1. **kingdee-k3cloud-mcp 的优点**：
   - 代码简洁（950 行），易于理解和改造
   - 使用 FastMCP 框架，开发效率高
   - 使用官方 SDK 集成，可靠性好
   - 支持多种传输协议（stdio、SSE、streamable-http）
   - 支持只读/读写模式

2. **借鉴 muk_mcp 的优点**：
   - 模块化的工具定义（`mcp/read.py`、`mcp/write.py` 等）
   - API Key + Scope 权限控制
   - 速率限制
   - 会话管理
   - 请求日志和审计

3. **鼎捷 ERP 的特点**：
   - RESTful API（与金蝶类似，适合外部 MCP Server 模式）
   - 没有官方 Python SDK（需要自己封装 HTTP 客户端）
   - 需要支持多种业务对象（采购入库、销货出库、物料同步等）

---

## 三、开发计划

### Phase 1: 基础框架搭建（3-5 天）

**目标**：搭建项目骨架，实现基本的 MCP Server 和 API 客户端

| 任务 | 预估时间 | 说明 |
|------|----------|------|
| 创建项目结构 | 0.5 天 | pyproject.toml、src/、tests/ 等 |
| 实现 REST API 客户端 | 1 天 | 认证、请求/响应处理 |
| 实现 MCP Server 框架 | 0.5 天 | FastMCP Server、配置管理 |
| 实现第一个工具（query_purchase_receipt） | 1 天 | 查询采购入库单 |
| 测试和调试 | 1 天 | 与鼎捷 ERP 联调 |

**交付物**：
- 可运行的 MCP Server
- 一个查询工具（query_purchase_receipt）
- 基本的认证和错误处理

### Phase 2: 核心功能开发（5-7 天）

**目标**：实现采购入库和销货出库的完整 CRUD 操作

| 任务 | 预估时间 | 说明 |
|------|----------|------|
| 采购入库工具 | 2 天 | 创建、审核、撤销审核、删除、查询 |
| 销货出库工具 | 2 天 | 创建、审核、撤销审核、删除、查询 |
| 物料同步工具 | 1 天 | 查询物料信息 |
| 高级查询功能 | 1 天 | 自动翻页、日期分片（参考 kingdee-k3cloud-mcp） |
| 单元测试 | 1 天 | 测试覆盖 |

**交付物**：
- 采购入库完整工具集
- 销货出库完整工具集
- 物料查询工具
- 高级查询功能

### Phase 3: 安全和运维（3-5 天）

**目标**：增强安全性、可观测性和可运维性

| 任务 | 预估时间 | 说明 |
|------|----------|------|
| 只读/读写模式 | 0.5 天 | 参考 kingdee-k3cloud-mcp |
| API Key 认证 | 1 天 | 参考 muk_mcp |
| 速率限制 | 0.5 天 | 参考 muk_mcp |
| 请求日志和审计 | 1 天 | 参考 muk_mcp |
| 会话自动恢复 | 1 天 | 参考 kingdee-k3cloud-mcp |
| 部署文档 | 0.5 天 | Docker、配置说明 |

**交付物**：
- 完整的安全机制
- 日志和审计
- 部署文档

### Phase 4: 扩展和优化（3-5 天）

**目标**：扩展更多业务对象，优化性能

| 任务 | 预估时间 | 说明 |
|------|----------|------|
| 更多业务对象 | 2 天 | 销售订单、采购订单、库存查询等 |
| 大数据量导出 | 1 天 | query_bill_to_file（参考 kingdee-k3cloud-mcp） |
| 配套 Skill | 1 天 | 常用表单字段、工作流知识 |
| 性能优化 | 0.5 天 | 缓存、连接池 |
| 发布到 PyPI | 0.5 天 | 打包和发布 |

**交付物**：
- 更多业务对象支持
- 大数据量导出
- 配套 Skill
- PyPI 包

---

## 四、风险和待确认事项

### 4.1 高优先级（阻塞性）

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| **鼎捷 ERP 认证方式未确认** | 无法连接 ERP | 需要确认：API Key / 用户名密码 / OAuth / Session Cookie |
| **API 端点格式未确认** | 无法构造正确请求 | 需要一个完整的 API 调用示例 |
| **没有完整 API 文档** | 无法实现更多业务对象 | 需要获取更多对象的接口文档 |

### 4.2 中优先级

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| 会话超时处理 | 长时间运行时断连 | 参考 kingdee-k3cloud-mcp 的自动恢复 |
| 大数据量查询性能 | 查询超时 | 实现自动翻页和流式导出 |
| 字段映射错误 | 数据不一致 | 完善的单元测试和集成测试 |

### 4.3 低优先级

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| ERP 版本兼容性 | 不同版本字段不同 | 支持多版本配置 |
| 网络延迟 | 响应慢 | 缓存和连接池 |

---

## 五、成功标准

1. **基本功能**：AI 可以通过自然语言查询和操作鼎捷 ERP
2. **安全性**：凭证不进入 LLM 上下文，支持只读模式
3. **可靠性**：自动会话恢复，完善的错误处理
4. **易用性**：5 分钟内完成配置和启动
5. **可扩展性**：可以轻松添加新的业务对象

---

## 附录：参考项目

| 项目 | 地址 | 参考价值 |
|------|------|----------|
| mcp-odoo | https://github.com/tuanle96/mcp-odoo | MCP Server 框架、安全控制、审计日志 |
| kingdee-k3cloud-mcp | https://github.com/adamzhang1987/kingdee-k3cloud-mcp | **主要参考**：架构、FastMCP 使用、会话恢复、自动翻页 |
| muk_mcp | Odoo 第三方模块 | 工具模块化、API Key + Scope、速率限制、Playground |
