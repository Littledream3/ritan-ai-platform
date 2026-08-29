# ---- Stage 1: Admin Frontend Build ----
FROM node:18-alpine AS frontend-builder
WORKDIR /build
COPY admin/package.json admin/package-lock.json* ./
RUN npm config set registry https://registry.npmmirror.com && (npm install --frozen-lockfile 2>/dev/null || npm install)
COPY admin/ ./
RUN npm run build

# ---- Stage 2: Python App ----
FROM python:3.12-slim

LABEL maintainer="port"
LABEL description="多模型 API 网关 — FastAPI + 5 LLM"

# 系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    fonts-wqy-microhei \
    && rm -rf /var/lib/apt/lists/*

# 创建非 root 用户
RUN useradd --create-home --shell /bin/bash app

WORKDIR /app

# Python 依赖（分层缓存）
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt -i https://mirrors.aliyun.com/pypi/simple/ --trusted-host mirrors.aliyun.com

# 应用代码
COPY --chown=app:app app/ ./app/

# 前端构建产物
COPY --from=frontend-builder --chown=app:app /static/ ./static/

# 静态资源目录
RUN mkdir -p /app/static/videos && chown app:app /app/static/videos

# 切换到非 root 用户
USER app

# 健康检查
HEALTHCHECK --interval=15s --timeout=5s --retries=3 \
    CMD curl -f http://localhost:8000/api/v1/health || exit 1

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
