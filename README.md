# MCPHub ERP 部署项目

通过 Docker Compose 一键部署 [MCPHub](https://github.com/samanhappy/mcphub) + 多个 ERP MCP Server，让 AI 助手通过自然语言操作鼎捷、金蝶、Odoo 等 ERP 与 MES、WMS 系统。

## 目录结构

```
mcphub-erp/
├── docker-compose.yml          # mcphub + PostgreSQL 启动配置
├── .env.example                # 环境变量模板（复制为 .env）
├── .env                        # 实际环境变量（不进 Git）
├── .gitignore
├── README.md                   # 本文档
└── mcp-servers/                # 各 ERP MCP Server 源码（挂载进容器）
    ├── dingjie-mcp-sever/      # 鼎捷 ERP E10 MCP
    ├── kingdee-k3cloud-mcp-main/  # 金蝶 K3Cloud MCP
    └── mcp-odoo/               # Odoo MCP
```

## 架构原理

```
你的本机 (IDE 编辑代码)
    │
    ▼  docker -v 挂载
┌─────────────────────────────────────────┐
│  mcphub 容器 (samanhappy/mcphub:latest) │
│  内置 uv + node 22                      │
│                                         │
│  /app/mcp-servers/  ← 挂载的源码        │
│    ├── dingjie-mcp-sever/               │
│    ├── kingdee-k3cloud-mcp-main/        │
│    └── mcp-odoo/                        │
│                                         │
│  Dashboard (端口 3000)                  │
│    └─ uv run --directory ... 启动 MCP   │
└─────────────────────────────────────────┘
              │
              ▼
         PostgreSQL (配置持久化)
```

**核心优势**：代码挂载进容器，改代码后在 Dashboard 点 **reload** 即可生效，无需重新构建镜像。

## 快速开始

### 1. 配置环境变量

```bash
cp .env.example .env
```

编辑 `.env`，填写各 ERP 的连接信息（必填项见文件内注释）。

### 2. 配置 Odoo（如使用）

Odoo 通过 JSON 配置文件连接，不走环境变量：

```bash
cp mcp-servers/mcp-odoo/odoo_config.json.example mcp-servers/mcp-odoo/odoo_config.json
```

编辑 `odoo_config.json`：

```json
{
  "url": "https://your-odoo-instance.com",
  "db": "your-database-name",
  "username": "your-username",
  "password": "your-password-or-api-key"
}
```

### 3. 启动服务

```bash
docker compose up -d
```

首次启动会拉取镜像并初始化数据库，约 1-2 分钟。

### 4. 访问管理面板

打开浏览器访问 `http://localhost:3000`，使用 `.env` 中设置的 `ADMIN_PASSWORD` 登录。

### 5. 添加 MCP Server

在 Dashboard → **Servers** 页面，按下方配置逐个添加。

## MCP Server 配置

> **重要**：mcphub 会将容器环境变量自动注入每个 MCP Server 子进程。
> 因此下方的 `env` 只需填写需要**覆盖**的值，ERP 凭证已在 `.env` 中统一配置。

### 鼎捷 ERP E10

| 字段 | 值 |
|------|-----|
| **名称** | `dingjie-e10` |
| **类型** | stdio |
| **command** | `uv` |
| **args** | `run` `--directory` `/app/mcp-servers/dingjie-mcp-sever` `dingjie-erp-mcp` |
| **env** | `{}`（凭证已从容器环境继承） |

### 金蝶 K3Cloud

| 字段 | 值 |
|------|-----|
| **名称** | `kingdee-k3cloud` |
| **类型** | stdio |
| **command** | `uv` |
| **args** | `run` `--directory` `/app/mcp-servers/kingdee-k3cloud-mcp-main` `kingdee-k3cloud-mcp` |
| **env** | `{}` |

### Odoo

| 字段 | 值 |
|------|-----|
| **名称** | `odoo` |
| **类型** | stdio |
| **command** | `uv` |
| **args** | `run` `--directory` `/app/mcp-servers/mcp-odoo` `odoo-mcp` |
| **env** | `{}` |

### JSON 批量导入

也可在 Dashboard → **Import** → 粘贴以下 JSON 一次性导入全部三个：

```json
{
  "mcpServers": {
    "dingjie-e10": {
      "type": "stdio",
      "command": "uv",
      "args": ["run", "--directory", "/app/mcp-servers/dingjie-mcp-sever", "dingjie-erp-mcp"]
    },
    "kingdee-k3cloud": {
      "type": "stdio",
      "command": "uv",
      "args": ["run", "--directory", "/app/mcp-servers/kingdee-k3cloud-mcp-main", "kingdee-k3cloud-mcp"]
    },
    "odoo": {
      "type": "stdio",
      "command": "uv",
      "args": ["run", "--directory", "/app/mcp-servers/mcp-odoo", "odoo-mcp"]
    }
  }
}
```

导入后在各 Server 的 **Env** 标签页确认凭证已从容器继承，无需重复填写。

## 更新代码

改完任意 MCP Server 代码后：

1. 保存文件（IDE 直接编辑 `mcp-servers/` 下的源码）
2. 打开 Dashboard → Servers
3. 对应 Server 点 **reload**（重载图标）
4. `uv run --directory` 会用挂载目录里的最新代码重启 → **立即生效**

无需 `docker compose build`、无需重新部署。

## 常用命令

```bash
# 启动
docker compose up -d

# 查看日志
docker compose logs -f mcphub

# 停止
docker compose down

# 停止并删除数据卷（⚠️ 清空所有配置）
docker compose down -v

# 更新 mcphub 镜像
docker compose pull && docker compose up -d
```

## 内网/离线部署

如容器无法访问公网 PyPI，可在 `.env` 中设置内网镜像：

```bash
# 取消 docker-compose.yml 中对应行的注释，或在 .env 中设置
UV_DEFAULT_INDEX=https://pypi.your-company.com/simple/
npm_config_registry=https://npm.your-company.com/
```

mcphub 会在启动 `uv`/`uvx`/`python` 命令的 Server 时自动注入 `UV_DEFAULT_INDEX`。

## 环境变量说明

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `MCPHUB_PORT` | 管理面板端口 | `3000` |
| `ADMIN_PASSWORD` | 首次启动管理员密码 | `mcphub2024` |
| `DB_PASSWORD` | PostgreSQL 密码 | `mcphub_password` |
| `DB_PORT` | PostgreSQL 端口 | `5432` |
| `DINGJIE_*` | 鼎捷互联中台连接参数 | — |
| `KD_*` | 金蝶 K3Cloud 连接参数 | — |
| `MCP_MODE` | 全局模式：`readonly` / `readwrite` | `readwrite` |

完整变量列表见 [`.env.example`](.env.example)。

## 关于 Git 管理

本仓库将 `mcp-servers/` 下的各 MCP Server 源码一并纳入 Git，便于：

- **单仓库部署**：`git clone` 即可获得完整运行环境
- **版本锁定**：所有 ERP 接口代码与部署配置同步版本管理
- **团队协作**：同事 clone 后填入 `.env` 即可启动

> 如果各 MCP Server 有独立远程仓库且希望保持同步，可改用 Git Submodule：
> ```bash
> git submodule add <repo-url> mcp-servers/dingjie-mcp-sever
> ```

## 许可证

本部署配置遵循 MIT 协议。各 MCP Server 的许可证见各自目录。
