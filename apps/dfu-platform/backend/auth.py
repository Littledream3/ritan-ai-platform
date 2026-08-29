# -*- coding: utf-8 -*-
"""
DFU 系统 — 认证模块
JWT 签发/校验、密码哈希、邮箱验证码、SMTP 发送
复用 ritan 的飞书 SMTP 配置
"""
import os
import re
import random
import secrets
import datetime as dt
import smtplib
from pathlib import Path
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

import bcrypt
import jwt as pyjwt

# ── 加载 ritan .env（复用飞书 SMTP 配置）─────────
try:
    from dotenv import load_dotenv
    _ENV_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "ritan", ".env")
    _ENV_PATH = os.path.abspath(_ENV_PATH)
    if os.path.isfile(_ENV_PATH):
        load_dotenv(_ENV_PATH)
        print(f"[DFU Auth] 已加载环境变量: {_ENV_PATH}")
except Exception:
    pass

# ── JWT 配置 ──────────────────────────────────
def _load_or_create_jwt_secret() -> str:
    """Keep JWTs valid across restarts without committing a secret to source."""
    configured = os.getenv("DFU_JWT_SECRET", "").strip()
    if configured:
        return configured

    secret_path = Path(os.getenv("DFU_JWT_SECRET_FILE", Path(__file__).with_name(".jwt_secret")))
    if secret_path.exists():
        return secret_path.read_text(encoding="utf-8").strip()

    value = secrets.token_urlsafe(64)
    secret_path.write_text(value, encoding="utf-8")
    try:
        secret_path.chmod(0o600)
    except OSError:
        pass
    return value


JWT_SECRET_KEY  = _load_or_create_jwt_secret()
JWT_ALGORITHM   = "HS256"
JWT_EXPIRE_HOURS = 48

# ── SMTP 配置（复用 ritan 飞书邮箱）────────────
SMTP_HOST     = os.getenv("RITAN_SMTP_HOST", "smtp.feishu.cn")
SMTP_PORT     = int(os.getenv("RITAN_SMTP_PORT", "465"))
SMTP_USERNAME = os.getenv("RITAN_SMTP_USERNAME", "")
SMTP_PASSWORD = os.getenv("RITAN_SMTP_PASSWORD", "")
SMTP_FROM     = os.getenv("RITAN_SMTP_FROM_NAME", "DFU智能检测")

# ── 限制参数 ──────────────────────────────────
MAX_VERIFY_ATTEMPTS = 5
RESEND_COOLDOWN_SECONDS = 60


# ══════════════════════════════════════════════
# 密码哈希
# ══════════════════════════════════════════════

def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))


# ══════════════════════════════════════════════
# JWT
# ══════════════════════════════════════════════

def create_jwt(user_id: int, email: str | None = None, role: str = "patient", username: str | None = None) -> str:
    now = dt.datetime.now(dt.timezone.utc)
    payload = {
        "sub": str(user_id),
        "email": email,
        "username": username,
        "role": role,
        "iat": now,
        "exp": now + dt.timedelta(hours=JWT_EXPIRE_HOURS),
        "type": "access",
    }
    return pyjwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


def decode_jwt(token: str) -> dict | None:
    try:
        payload = pyjwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        if payload.get("type") != "access":
            return None
        return payload
    except Exception:
        return None


# ══════════════════════════════════════════════
# 邮箱 & 密码校验
# ══════════════════════════════════════════════

def validate_email(email: str) -> str:
    email = email.strip().lower()
    if not re.match(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", email):
        raise ValueError("邮箱格式不正确")
    return email


def validate_password(pw: str) -> str:
    if len(pw) < 8 or len(pw) > 12:
        raise ValueError("密码长度须为 8-12 位")
    if not re.search(r"[A-Z]", pw):
        raise ValueError("密码必须包含至少一个大写字母")
    if not re.search(r"[a-z]", pw):
        raise ValueError("密码必须包含至少一个小写字母")
    if not re.search(r"[0-9]", pw):
        raise ValueError("密码必须包含至少一个数字")
    if not re.search(r"[!@#$%^&*()_+\-=\[\]{};':\"\\|,.<>\/?`~]", pw):
        raise ValueError("密码必须包含至少一个特殊符号")
    return pw


# ══════════════════════════════════════════════
# 邮箱验证码发送
# ══════════════════════════════════════════════

def send_email_code(to_email: str, code: str) -> bool:
    """发送验证码邮件。SMTP 未配置时抛出异常。"""
    if not SMTP_USERNAME or not SMTP_PASSWORD:
        raise RuntimeError("邮件服务未配置，请联系管理员")

    subject = f"【DFU智能检测】邮箱验证码：{code}"
    html_body = f"""\
<html><body style="font-family:'PingFang SC','Microsoft YaHei',sans-serif;">
<div style="max-width:480px;margin:20px auto;border:1px solid #e2e8f0;border-radius:12px;overflow:hidden;">
<div style="background:linear-gradient(135deg,#1a1a2e,#16213e);padding:28px 20px;text-align:center;">
<h1 style="color:#e8d5b7;margin:0;font-size:20px;">DFU 糖尿病足溃疡智能检测</h1>
</div>
<div style="padding:28px 20px;background:#fff;">
<p style="color:#333;font-size:14px;margin:0 0 18px;">您的邮箱验证码为：</p>
<div style="background:#faf7f2;border:1px dashed #c6a66f;border-radius:10px;padding:18px;text-align:center;margin-bottom:18px;">
<span style="font-size:30px;font-weight:700;color:#5a4a3a;letter-spacing:8px;">{code}</span>
</div>
<p style="color:#888;font-size:12px;">验证码 10 分钟内有效，请勿转发给他人。</p>
</div>
</div></body></html>"""
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"{SMTP_FROM} <{SMTP_USERNAME}>"
    msg["To"] = to_email
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    server = smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT)
    server.login(SMTP_USERNAME, SMTP_PASSWORD)
    server.sendmail(SMTP_USERNAME, to_email, msg.as_string())
    server.quit()
    return True
