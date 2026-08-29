# 服务器项目对应关系

| 原服务器目录 | GitHub 目录 | 用途 |
| --- | --- | --- |
| `/home/ubuntu/port` | `apps/corporate-platform` | 官网及综合业务平台 |
| `/home/ubuntu/lanqiao` | `apps/skin-diagnosis` | AI 测肤服务 |
| `/home/ubuntu/lanjiao-skin` | `apps/skin-landing-source` | 测肤宣传页工程 |
| `/home/ubuntu/dfu-v2` | `apps/dfu-platform` | 当前 DFU 患者端、医生端和分级服务 |
| `/home/ubuntu/dfu-collection` | `apps/dfu-collection` | 医生数据采集系统 |
| `/home/ubuntu/media-drop` | `apps/media-drop` | 批量媒体上传 |
| `/home/ubuntu/dfu` | `apps/dfu-legacy` | DFU 旧版 |
| `/home/ubuntu/ritan` | `apps/ritan-legacy` | 官网旧版 |

## 生产服务

- `nginx.service`
- `lanjiao.service`
- `dfu.service`
- `dfu-v2.service`
- `dfu-collection.service`
- `media-drop.service`
- Docker：三个 PostgreSQL 服务，以及官网所需 MySQL、Redis 和应用容器

运行配置的原始版本保存在加密迁移包中；GitHub 只保存脱敏模板。

