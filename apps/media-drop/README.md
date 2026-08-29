# 日坛 AI 快速媒体上传

无需注册或登录的批量图片、视频上传页面。每次打开页面可创建一个不可猜测的临时上传批次，批次凭证只返回给当前浏览器，不提供公开文件读取接口。

生产环境隔离配置：

- PostgreSQL 数据库：`media_drop`
- Docker 容器：`media-drop-postgres`
- Docker 卷：`media_drop_postgres_data`
- 数据库监听：`127.0.0.1:5435`
- 媒体目录：`/home/ubuntu/media-drop/data/uploads`
- Web 服务：`127.0.0.1:8006`
- 公网路径：`/media-drop/`

默认限制：单批 100 个文件/5 GB，图片 25 MB，视频 750 MB，磁盘至少保留 10 GB。
