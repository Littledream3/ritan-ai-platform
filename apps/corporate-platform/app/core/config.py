"""应用配置 — 基于 Pydantic Settings，从 .env 和环境变量加载"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """全局配置，所有字段可从环境变量 / .env 文件读取"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ---- 应用 ----
    app_debug: bool = True
    app_host: str = "0.0.0.0"
    app_port: int = 8000

    # ---- MySQL ----
    mysql_host: str = "127.0.0.1"
    mysql_port: int = 3307
    mysql_user: str = "port"
    mysql_password: str = ""
    mysql_database: str = "port"

    # ---- Redis ----
    redis_host: str = "127.0.0.1"
    redis_port: int = 6379
    redis_password: str = ""

    # ---- 模型 API ----
    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com/v1"

    kimi_api_key: str = ""
    kimi_base_url: str = "https://api.moonshot.cn/v1"

    qwen_api_key: str = ""
    qwen_base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"

    glm_api_key: str = ""
    glm_base_url: str = "https://open.bigmodel.cn/api/paas/v4"

    doubao_api_key: str = ""
    doubao_base_url: str = "https://ark.cn-beijing.volces.com/api/v3"

    # ---- 飞书 ----
    feishu_app_id: str = ""
    feishu_app_secret: str = ""

    # ---- SMTP / 邮件（飞书邮箱）----
    smtp_host: str = ""
    smtp_port: int = 465
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = ""
    smtp_use_ssl: bool = True

    # ---- 上传 ----
    upload_max_file_size: int = 20 * 1024 * 1024   # 20MB 文本/PDF/DOCX
    upload_max_video_size: int = 100 * 1024 * 1024  # 100MB 视频

    # ---- JWT ----
    jwt_secret_key: str = ""
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 1440

    # ---- 数据库连接串（派生） ----
    @property
    def database_url(self) -> str:
        return (
            f"mysql+aiomysql://{self.mysql_user}:{self.mysql_password}"
            f"@{self.mysql_host}:{self.mysql_port}/{self.mysql_database}"
        )

    @property
    def database_url_sync(self) -> str:
        """Alembic 迁移用的同步连接串"""
        return (
            f"mysql+pymysql://{self.mysql_user}:{self.mysql_password}"
            f"@{self.mysql_host}:{self.mysql_port}/{self.mysql_database}"
        )

    @property
    def redis_url(self) -> str:
        if self.redis_password:
            return f"redis://:{self.redis_password}@{self.redis_host}:{self.redis_port}"
        return f"redis://{self.redis_host}:{self.redis_port}"


settings = Settings()
