"""飞书服务 — Token 管理、消息收发、事件处理"""

import hashlib
import json
import os
import time
from typing import Optional

import httpx
from loguru import logger

from app.core import redis as redis_module
from app.core.config import settings

# ---- 常量 ----

FEISHU_HOST = "https://open.feishu.cn"
TOKEN_KEY = "feishu:tenant_access_token"
TOKEN_TTL = 7200  # 2 小时，飞书实际 expire 约 2 小时
EVENT_DEDUP_KEY = "feishu:event:"  # + event_id，TTL 1h
SESSION_KEY = "feishu:session:"  # + open_id → model_name

# ---- Token 管理 ----


async def get_tenant_access_token() -> str:
    """获取 tenant_access_token（Redis 缓存，提前 60s 过期防边界问题）"""
    cached = await redis_module.redis_client.get(TOKEN_KEY)
    if cached:
        return cached  # decode_responses=True 已自动解码为 str

    app_id = settings.feishu_app_id
    app_secret = settings.feishu_app_secret

    if not app_id or not app_secret:
        raise RuntimeError("飞书 App ID / Secret 未配置，请在 .env 中设置 FEISHU_APP_ID 和 FEISHU_APP_SECRET")

    url = f"{FEISHU_HOST}/open-apis/auth/v3/tenant_access_token/internal"
    payload = {"app_id": app_id, "app_secret": app_secret}

    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.post(url, json=payload)
        data = resp.json()

    code = data.get("code")
    if code != 0:
        logger.error(f"获取 tenant_access_token 失败: code={code}, msg={data.get('msg')}")
        raise RuntimeError(f"获取飞书 Token 失败: {data}")

    token = data["tenant_access_token"]
    expire = data.get("expire", TOKEN_TTL)
    ttl = max(expire - 60, 60)

    await redis_module.redis_client.set(TOKEN_KEY, token, ex=ttl)
    logger.info("飞书 tenant_access_token 已刷新")
    return token


async def _feishu_request(method: str, path: str, payload: dict = None, timeout: int = 30) -> dict:
    """通用飞书 API 请求（自动附加 token）"""
    token = await get_tenant_access_token()
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json; charset=utf-8",
    }
    url = f"{FEISHU_HOST}{path}"
    async with httpx.AsyncClient(timeout=timeout) as client:
        if method.upper() == "GET":
            resp = await client.get(url, headers=headers, params=payload)
        elif method.upper() == "PATCH":
            resp = await client.patch(url, json=payload, headers=headers)
        else:
            resp = await client.post(url, json=payload, headers=headers)
        return resp.json()


# ---- 消息发送 ----


async def send_text_to_user(open_id: str, text: str) -> dict:
    """发送私聊文本消息"""
    return await _feishu_request(
        "POST",
        "/open-apis/im/v1/messages?receive_id_type=open_id",
        {
            "receive_id": open_id,
            "msg_type": "text",
            "content": json.dumps({"text": text}, ensure_ascii=False),
        },
    )


async def reply_text_message(message_id: str, text: str) -> dict:
    """回复文本消息（私聊/群聊通用）"""
    return await _feishu_request(
        "POST",
        f"/open-apis/im/v1/messages/{message_id}/reply",
        {
            "msg_type": "text",
            "content": json.dumps({"text": text}, ensure_ascii=False),
        },
    )


async def edit_text_message(message_id: str, text: str) -> dict:
    """编辑已发送的文本消息（用于流式更新）"""
    return await _feishu_request(
        "PATCH",
        f"/open-apis/im/v1/messages/{message_id}",
        {
            "msg_type": "text",
            "content": json.dumps({"text": text}, ensure_ascii=False),
        },
    )


async def get_message_info(message_id: str) -> dict:
    """获取消息详情"""
    return await _feishu_request("GET", f"/open-apis/im/v1/messages/{message_id}")


async def download_resource(message_id: str, file_key: str, resource_type: str = "file") -> bytes:
    """
    下载飞书消息中的文件或图片

    Args:
        message_id: 消息 ID
        file_key: 文件 key（从消息 content 中获取）
        resource_type: "file" 或 "image"

    Returns:
        文件的二进制内容
    """
    token = await get_tenant_access_token()
    headers = {"Authorization": f"Bearer {token}"}
    url = f"{FEISHU_HOST}/open-apis/im/v1/messages/{message_id}/resources/{file_key}?type={resource_type}"

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(url, headers=headers)
        if resp.status_code != 200:
            logger.error(f"下载飞书资源失败: status={resp.status_code}, body={resp.text[:200]}")
            raise RuntimeError(f"下载文件失败: HTTP {resp.status_code}")
        return resp.content


async def fetch_recent_file(chat_id: str, lookback: int = 20, filename: str = "") -> dict | None:
    """
    从群聊最近消息中查找文件消息

    Args:
        chat_id: 群聊 chat_id
        lookback: 往前翻多少条
        filename: 可选，按文件名关键词过滤（模糊匹配）

    Returns:
        {"message_id": "om_xxx", "file_key": "file_xxx", "file_name": "xxx.pdf"} 或 None
    """
    token = await get_tenant_access_token()
    headers = {"Authorization": f"Bearer {token}"}
    url = (
        f"{FEISHU_HOST}/open-apis/im/v1/messages"
        f"?container_id_type=chat"
        f"&container_id={chat_id}"
        f"&page_size={lookback}"
        f"&sort_type=ByCreateTimeDesc"
    )

    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(url, headers=headers)
        data = resp.json()

    if data.get("code") != 0:
        logger.error(f"获取群聊消息失败: code={data.get('code')}, msg={data.get('msg')}")
        return None

    items = data.get("data", {}).get("items", [])
    filename_lower = filename.strip().lower() if filename else ""

    for msg in items:
        if msg.get("msg_type") == "file":
            body = msg.get("body", {})
            content_str = body.get("content", "{}")
            try:
                content = json.loads(content_str)
            except json.JSONDecodeError:
                continue
            fname = content.get("file_name", body.get("title", "unknown"))

            # 如果指定了文件名，做模糊匹配
            if filename_lower and filename_lower not in fname.lower():
                continue

            return {
                "message_id": msg.get("message_id", ""),
                "file_key": content.get("file_key", ""),
                "file_name": fname,
            }

    return None


# ---- 文件/图片上传与发送 ----


async def upload_file(file_path: str, file_type: str = "stream") -> dict:
    """上传文件到飞书，返回 {"file_key": "..."} 或含 code/msg 的错误

    Args:
        file_path: 本地文件路径
        file_type: 文件类型 (stream/opus/mp4/pdf/doc/ppt/xls 等)
    """
    token = await get_tenant_access_token()
    headers = {"Authorization": f"Bearer {token}"}
    url = f"{FEISHU_HOST}/open-apis/im/v1/files"

    file_name = os.path.basename(file_path)
    file_size = os.path.getsize(file_path)

    # 飞书限制：文件 ≤ 200MB
    if file_size > 200 * 1024 * 1024:
        return {"code": -1, "msg": f"文件过大 ({file_size/1024**2:.0f}MB)，飞书限制 200MB"}

    async with httpx.AsyncClient(timeout=60) as client:
        with open(file_path, "rb") as f:
            files = {
                "file": (file_name, f, "application/octet-stream"),
            }
            data = {
                "file_type": file_type,
                "file_name": file_name,
            }
            resp = await client.post(url, headers=headers, data=data, files=files)
            return resp.json()


async def upload_image(file_path: str) -> dict:
    """上传图片到飞书，返回 {"image_key": "..."} 或含 code/msg 的错误"""
    token = await get_tenant_access_token()
    headers = {"Authorization": f"Bearer {token}"}
    url = f"{FEISHU_HOST}/open-apis/im/v1/images"

    file_name = os.path.basename(file_path)

    async with httpx.AsyncClient(timeout=30) as client:
        with open(file_path, "rb") as f:
            files = {
                "image": (file_name, f, "application/octet-stream"),
            }
            data = {
                "image_type": "message",
            }
            resp = await client.post(url, headers=headers, data=data, files=files)
            return resp.json()


async def reply_file_message(message_id: str, file_key: str) -> dict:
    """回复文件消息"""
    return await _feishu_request(
        "POST",
        f"/open-apis/im/v1/messages/{message_id}/reply",
        {
            "msg_type": "file",
            "content": json.dumps({"file_key": file_key}, ensure_ascii=False),
        },
    )


async def reply_image_message(message_id: str, image_key: str) -> dict:
    """回复图片消息"""
    return await _feishu_request(
        "POST",
        f"/open-apis/im/v1/messages/{message_id}/reply",
        {
            "msg_type": "image",
            "content": json.dumps({"image_key": image_key}, ensure_ascii=False),
        },
    )


async def send_file_to_user(open_id: str, file_key: str) -> dict:
    """发送文件给用户（私聊）"""
    return await _feishu_request(
        "POST",
        "/open-apis/im/v1/messages?receive_id_type=open_id",
        {
            "receive_id": open_id,
            "msg_type": "file",
            "content": json.dumps({"file_key": file_key}, ensure_ascii=False),
        },
    )


# ---- 事件去重 ----


async def is_event_processed(event_id: str) -> bool:
    """检查事件是否已处理（幂等）"""
    key = f"{EVENT_DEDUP_KEY}{event_id}"
    # SETNX 返回 True 表示 key 不存在，已设置成功 → 未处理过
    was_set = await redis_module.redis_client.set(key, "1", nx=True, ex=3600)
    return not was_set  # 如果设置失败（NX），说明已存在 → 已处理过


# ---- 会话管理 ----


async def get_session_model(open_id: str) -> str:
    """获取用户在飞书中的当前模型（默认 kimi）"""
    key = f"{SESSION_KEY}{open_id}"
    model = await redis_module.redis_client.get(key)
    return model if model else "kimi-k2.7-code"  # decode_responses=True 已自动解码


async def set_session_model(open_id: str, model: str):
    """设置用户在飞书中的当前模型"""
    key = f"{SESSION_KEY}{open_id}"
    await redis_module.redis_client.set(key, model, ex=86400 * 7)  # 7天过期


# ---- 事件解密（兼容旧版加密事件）----


def decrypt_event(encrypt_str: str, encrypt_key: str = None) -> dict:
    """
    解密飞书加密事件体（AES-256-CBC + PKCS#7）

    飞书事件加密格式:
      - encrypt_key 做 SHA256 → 32 字节 AES 密钥
      - Base64 解码密文
      - 前 16 字节 = IV
      - 剩余 = AES-256-CBC 密文
      - 解密后去 PKCS#7 填充
    """
    from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
    from cryptography.hazmat.backends import default_backend

    key = encrypt_key or settings.feishu_app_secret
    if not key:
        raise ValueError("未配置加密密钥")

    aes_key = hashlib.sha256(key.encode()).digest()
    raw = __import__("base64").b64decode(encrypt_str)
    iv = raw[:16]
    ciphertext = raw[16:]

    cipher = Cipher(algorithms.AES(aes_key), modes.CBC(iv), backend=default_backend())
    decryptor = cipher.decryptor()
    padded = decryptor.update(ciphertext) + decryptor.finalize()

    # 去 PKCS#7 填充
    pad_len = padded[-1]
    plaintext = padded[:-pad_len]

    return json.loads(plaintext.decode("utf-8"))
