# 多模型 API 网关 + 飞书集成 — 任务列表

> 状态：⏳ 等待确认，收到指令后开始实施

---

## 已确认的技术选型

| 项目 | 选择 |
|------|------|
| 后端语言 | Python (FastAPI) |
| 前端框架 | Vue 3 + Element Plus |
| 数据库 | MySQL |
| 缓存/限流 | Redis |
| 内部鉴权 | 账号密码 + JWT（已改为独立登录，原飞书待后续补回） |
| 飞书集成 | ~~企业自建应用~~ → 独立登录 |
| 管理后台 | ✅ Web 管理后台 (FastAPI 内嵌静态资源) |
| 流式输出 | ✅ SSE |
| 限流策略 | 不限流（Redis 记录 + MySQL 持久化日志仅做用量统计，不需硬拦截） |
| 部署环境 | 阿里云 |

### 5 个大模型

| # | 厂商 | 模型 ID |
|---|------|---------|
| 1 | DeepSeek | `deepseek-v4-pro` |
| 2 | Kimi (月之暗面) | `kimi-k2.7-code` |
| 3 | 阿里云百炼 | `qwen3.7-max` |
| 4 | 智谱 GLM | `glm-4.7`（5.x 需充值） |
| 5 | 豆包 (字节) | `doubao-seed-2-0-pro-260215` |

---

## Phase 1 — 项目初始化

- [x] **1.1 项目骨架搭建** ✅
  - FastAPI 项目目录结构
  - 依赖管理：`requirements.txt` + venv
  - Python 3.12.3 + 所有依赖已安装

- [x] **1.2 配置管理** ✅
  - `.env` / `.env.example`：5 个模型 API Key + Base URL、飞书 App 凭证、MySQL/Redis 连接串
  - `app/core/config.py`：Pydantic Settings 配置类
  - `app/core/database.py`：SQLAlchemy 异步引擎 + 会话管理
  - `app/core/redis.py`：Redis 异步客户端 + 生命周期管理
  - `app/main.py`：FastAPI 入口 + `/api/v1/health` 通过 ✅

---

## Phase 2 — 模型适配层 (Model Adapter)

- [x] **2.1 统一模型抽象** ✅
  - `app/adapters/base.py` — `BaseAdapter` 抽象基类 + `ModelInfo` 数据类
  - 统一方法签名：
    - `async chat(messages, **params)` → 非流式
    - `async chat_stream(messages, **params)` → AsyncGenerator，SSE
  - 统一请求/响应格式（OpenAI Chat Completion 兼容）

- [x] **2.2 五个模型适配器** ✅
  - `app/adapters/openai_compatible.py` — 通用 OpenAI 兼容适配器（httpx）
  - `app/adapters/deepseek.py` — DeepSeek
  - `app/adapters/kimi.py` — Kimi / Moonshot
  - `app/adapters/qwen.py` — 阿里云百炼 DashScope
  - `app/adapters/glm.py` — 智谱 GLM
  - `app/adapters/doubao.py` — 豆包 / 火山引擎

- [x] **2.3 模型注册中心** ✅
  - `app/adapters/registry.py` — `ModelRegistry`（全局单例）
  - `GET /api/v1/models` — 查询所有模型 + 可用性状态
  - 启动时自动注册，自动检测 API Key 是否配置

---

## Phase 3 — 用户认证（独立账号密码 + JWT）

- [x] **3.1 数据库模型** ✅
  - `users` 表：id, username(唯一), password_hash, feishu_open_id(可空), name, avatar, role, is_active, created_at
  - `usage_logs` 表：id, user_id, model, prompt_tokens, completion_tokens, latency_ms, created_at
  - Alembic 迁移已执行

- [x] **3.2 独立登录** ✅
  - `POST /api/v1/auth/register` — 注册（username + password + name）
  - `POST /api/v1/auth/login` — 登录 → JWT
  - PBKDF2-SHA256 密码哈希，60 万次迭代
  - 错误密码 / 无 Token 均正确返回 401/403

- [x] **3.3 JWT 鉴权中间件** ✅
  - `app/middleware/auth.py` — `get_current_user` / `get_admin_user`
  - `GET /api/v1/auth/me` — 需 Bearer Token
  - 飞书 OAuth 框架保留（`feishu_open_id` 字段），后续有域名后可补回

---

## Phase 4 — 核心 API

- [x] **4.1 对话接口** ✅
  - `POST /api/v1/chat` — 非流式对话 ✅（全部 5 个模型通过）
  - `POST /api/v1/chat/stream` — SSE 流式对话 ✅
  - `temperature` 改为可选（Kimi K2.7 Code 只接受 1）
  - 用量异步写入 `usage_logs` 表
  - 无效模型 → 400，无 Token → 403，上游 API 失败 → 502

- [x] **4.2 模型接口** ✅
  - `GET /api/v1/models` — 模型列表 + 基本信息（名称、厂商、状态）

- [x] **4.3 认证接口** ✅
  - `GET /api/v1/auth/me` — 当前用户信息
  - 注：暂不需要 `/logout`（JWT 无状态，客户端删除 Token 即可）

---

## Phase 5 — 用量统计（Redis + MySQL）

- [x] **5.1 数据库日志** ✅
  - `usage_logs` 表已创建，每次 `/chat` 调用异步写入（prompt_tokens, completion_tokens, latency_ms）
  - 流式调用结���后也记录到 Redis（completion_tokens 按内容长度估算）

- [x] **5.2 Redis 实时计数** ✅
  - Key 设计：`port:usage:{user_id}:{model}:{date}` → hash（calls, prompt_tokens, completion_tokens）
  - 用户当日汇总：`port:usage:{user_id}:all:{date}`
  - TTL 30 天自动过期
  - `GET /api/v1/stats/today` — 今日实时用量汇总 + 按模型明细
  - `GET /api/v1/stats/history` — MySQL 历史明细（分页 + 按模型筛选 + 按天数）

- [x] **5.3 无需硬限流** ✅
  - 仅记录与展示，不做强制拦截
  - `get_global_stats()` 已预置（Phase 6 管理后台可直接调用）

---

## Phase 6 — Web 管理后台

- [x] **6.1 前端项目搭建** ✅
  - Vue 3 + Element Plus + Vite（`admin/` 目录）
  - vue-router 路由守卫（未登录 → `/admin/login`）
  - axios 请求拦截器（自动附带 JWT，401/403 自动跳转登录）
  - `npm run build` → `static/` 目录
  - FastAPI 挂载 `/admin/assets` 静态资源，`/admin/*` → SPA fallback

- [x] **6.2 管理后台页面** ✅
  | 页面 | 路由 | 功能 |
  |------|------|------|
  | 登录页 | `/admin/login` | 账号密码登录 + 注册 |
  | 仪表盘 | `/admin` | 总调用量/Token/活跃用户/模型占比 + 今日用量 |
  | 用量明细 | `/admin/logs` | 全平台分页 + 按模型筛选 + 按天数 |
  | 用户管理 | `/admin/users` | 用户列表 + 编辑角色/启用状态 |
  | 模型状态 | `/admin/models` | 5 模型可用性卡片 + 快速测试对话 |

- [x] **6.3 管理后台 API** ✅
  - `GET /api/v1/admin/stats` — 全局统计概览（需 admin）
  - `GET /api/v1/admin/logs` — 全平台用量明细分页（需 admin）
  - `GET /api/v1/admin/users` — 用户列表（需 admin）
  - `PUT /api/v1/admin/users/{id}` — 编辑用户（需 admin）

---

## Phase 7 — 飞书机器人集成

- [ ] **7.1 飞书事件订阅**
  - 飞书开放平台配置事件订阅 URL（`https://your-domain/api/v1/feishu/event`）
  - 订阅 `im.message.receive_v1` 事件
  - URL 验证（challenge 响应）

- [ ] **7.2 消息处理**
  - 接收飞书消息 → 解析文本 → 调用统一对话接口 → 回复
  - 私聊：直接回复
  - 群聊：仅 @机器人 时回复

- [ ] **7.3 指令系统**
  | 指令 | 功能 |
  |------|------|
  | `/model <name>` | 切换模型（会话级） |
  | `/models` | 查看 5 个可用模型 |
  | `/help` | 使用帮助 |

- [ ] **7.4 流式回复**
  - 飞书消息卡片不支持原生 SSE
  - 方案：分段编辑消息，逐步追加内容，模拟流式效果

---

## Phase 8 — 部署（阿里云）

- [x] **8.1 基础设施** ✅
  - [x] ECS 实例（阿里云 Ubuntu 22.04，当前机器）✅
  - [x] MySQL（Docker 容器，端口 3307，数据卷 `./data/mysql`）✅
  - [x] Redis（Docker 容器，端口 6379，AOF 持久化）✅
  - [ ] 域名 + SSL 证书（待购）

- [x] **8.2 部署配置** ✅
  - ✅ Dockerfile — 多阶段构建（Node.js 前端 + Python 后端）
  - ✅ Nginx 反向代理（HTTP on :8080，SSE 流式已配置 proxy_buffering off）
  - ✅ Docker Compose — 4 服务编排（app + nginx + mysql + redis）
  - ✅ Systemd 服务 (`docker/systemd/port.service`) 作为非 Docker 部署备选

- [x] **8.3 服务启动** ✅
  - ✅ 环境变量通过 `.env` 注入，容器内 MYSQL_HOST/REDIS_HOST 自动覆盖为 Docker 服务名
  - ✅ 数据库初始化通过 Alembic 迁移完成
  - ✅ 健康检查 `GET /api/v1/health` → `{"status":"ok","database":true,"redis":true}`
  - ⚠️ asyncmy → aiomysql（纯 Python，无需 C 编译器，Docker 兼容）

---

## 目录结构预览

```
/home/ubuntu/port/
├── app/
│   ├── __init__.py
│   ├── main.py                  # FastAPI 入口
│   ├── core/
│   │   ├── config.py            # 配置管理
│   │   ├── database.py          # MySQL 连接
│   │   └── redis.py             # Redis 连接
│   ├── adapters/
│   │   ├── base.py              # 抽象基类
│   │   ├── deepseek.py
│   │   ├── kimi.py
│   │   ├── qwen.py
│   │   ├── glm.py
│   │   ├── doubao.py
│   │   └── registry.py          # 模型注册与路由
│   ├── models/
│   │   ├── user.py              # User ORM
│   │   └── usage_log.py         # UsageLog ORM
│   ├── api/
│   │   ├── chat.py              # 对话接口
│   │   ├── auth.py              # 认证接口
│   │   ├── models.py            # 模型查询接口
│   │   ├── admin.py             # 管理后台接口
│   │   └── feishu.py            # 飞书事件回调
│   ├── middleware/
│   │   └── auth.py              # JWT 鉴权中间件
│   ├── services/
│   │   ├── auth_service.py      # 飞书 OAuth 逻辑
│   │   └── stats_service.py     # 统计服务
│   └── schemas/
│       ├── chat.py              # 请求/响应 Pydantic 模型
│       └── user.py
├── admin/                       # Vue 3 管理后台
│   ├── src/
│   └── package.json
├── static/                      # 管理后台构建产物
├── alembic/                     # 数据库迁移
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
└── .env.example
```

---

> 任务列表已按你的选择更新完毕。确认无误后给我指令，我从 Phase 1 开始编码。
