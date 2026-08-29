"""邮件发送服务 — 通过飞书 SMTP 发送验证码"""

import asyncio
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import smtplib

from app.core.config import settings

logger = logging.getLogger(__name__)


def _send_smtp(to_email: str, subject: str, body_html: str) -> bool:
    """同步 SMTP 发送（运行在 asyncio.to_thread 中）"""
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = settings.smtp_from
    msg["To"] = to_email
    msg.attach(MIMEText(body_html, "html", "utf-8"))

    try:
        if settings.smtp_use_ssl:
            server = smtplib.SMTP_SSL(settings.smtp_host, settings.smtp_port, timeout=15)
        else:
            server = smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=15)
            server.starttls()

        server.login(settings.smtp_user, settings.smtp_password)
        server.sendmail(settings.smtp_from, to_email, msg.as_string())
        server.quit()
        return True
    except Exception as e:
        logger.error(f"发送邮件失败: {e}")
        return False


async def send_verification_email(to_email: str, code: str) -> bool:
    """异步发送验证码邮件"""
    subject = "【多模型 API 网关】邮箱验证码"
    body_html = f"""\
<html>
<body style="font-family: Arial, sans-serif; padding: 20px;">
  <h2>邮箱验证码</h2>
  <p>您的验证码是：</p>
  <h1 style="color: #409EFF; font-size: 36px; letter-spacing: 8px;">{code}</h1>
  <p>验证码 5 分钟内有效，请勿泄露给他人。</p>
  <hr />
  <p style="color: #999; font-size: 12px;">此邮件由系统自动发送，请勿回复。</p>
</body>
</html>"""
    return await asyncio.to_thread(_send_smtp, to_email, subject, body_html)


async def send_password_reset_email(to_email: str, code: str) -> bool:
    """异步发送密码重置验证码邮件"""
    subject = "【多模型 API 网关】密码重置"
    body_html = f"""\
<html>
<body style="font-family: Arial, sans-serif; padding: 20px;">
  <h2>密码重置</h2>
  <p>您正在重置登录密码，验证码是：</p>
  <h1 style="color: #E6A23C; font-size: 36px; letter-spacing: 8px;">{code}</h1>
  <p>验证码 5 分钟内有效，请勿泄露给他人。</p>
  <p style="color: #999;">如非本人操作，请忽略此邮件。</p>
  <hr />
  <p style="color: #999; font-size: 12px;">此邮件由系统自动发送，请勿回复。</p>
</body>
</html>"""
    return await asyncio.to_thread(_send_smtp, to_email, subject, body_html)
