# 日坛 AI 医生数据采集系统

独立的医生端临床数据采集服务。每位患者由系统自动分配稳定患者编号，每次住院另生成独立采集编号。医生可通过手机号、患者编号、住院 ID 或采集编号查询历史记录。每个采集任务包含：

- 手机号、住院 ID、年龄、性别、糖尿病等级（必填）
- 患者姓名、居住地、饮食习惯（选填）
- 5 张全足基础照
- 5 张创口特写照
- 2 段不超过 15 秒的视频（选填）

医生端提供历史工作台、自由步骤导航、照片返回重拍或更换、最终统一校验、提交确认及医生信息核对。

## 数据隔离

生产环境使用独立 PostgreSQL 数据库 `dfu_collection`，独立 Docker 卷
`dfu_collection_postgres_data`，媒体文件写入独立目录
`/home/ubuntu/dfu-collection/data/media`。不读取或写入现有 DFU 系统数据库。

## 本地运行

```powershell
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
$env:DATABASE_URL="sqlite:///./collection-dev.db"
python -m alembic upgrade head
.venv\Scripts\uvicorn app.main:app --reload --port 8005
```

浏览器访问 `http://127.0.0.1:8005/`。
