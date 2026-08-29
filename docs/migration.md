# 新服务器恢复手册

## 1. 基础环境

- Ubuntu 24.04 LTS 或兼容发行版
- Docker Engine 与 Docker Compose
- Nginx
- Python 3.12
- Node.js（仅前端重新构建时需要）

## 2. 数据服务

需要恢复：

- `dfu_v2` PostgreSQL
- `dfu_collection` PostgreSQL
- `media_drop` PostgreSQL
- 官网 MySQL
- 官网 Redis（如旧实例没有有效 RDB，可重新初始化）
- 测肤服务 SQLite 记录库

数据库先恢复到隔离环境，完成表数量、记录数量和外键检查后再连接应用。

## 3. 媒体数据

脱敏影像按来源和分级保存。恢复时应维持 Grade 0–5 目录与媒体清单的对应关系，不使用原患者姓名、电话、邮箱或住院号作为路径。

## 4. 模型

从 Hugging Face 私有仓库下载固定版本，不直接使用浮动的 `main`：

- DFU：0–5 级标签顺序、预处理尺寸、归一化参数必须和模型卡一致。
- 测肤：年龄模型和皮肤模型分别校验 SHA-256。

## 5. 配置

根据 `.env.example` 创建新配置，并更换：

- PostgreSQL/MySQL/Redis 密码
- JWT 密钥
- 医生注册引荐码
- SMTP 密码
- 第三方模型 API Key
- GitHub/Hugging Face Token

## 6. HTTPS 与域名

在新服务器重新签发 TLS 证书。确认 HTTPS、子路径静态资源、摄像头权限和报告下载全部正常后，再切换 DNS。

## 7. 验收

- 所有服务健康检查通过
- 患者端、医生端和采集端能完成完整流程
- 报告 PDF 可下载
- Grade 0–5 推理接口返回结构正确
- PostgreSQL/MySQL 表数量和脱敏记录数量一致
- 分级影像文件数量和 SHA-256 清单一致

