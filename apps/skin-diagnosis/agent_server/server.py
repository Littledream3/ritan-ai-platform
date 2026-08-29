# -*- coding: utf-8 -*-
# 皮肤分析智能体后端
# 启动: python server.py
# 依赖: pip install fastapi uvicorn python-multipart openai

import os
import sys
import uuid
import base64
import shutil
import tempfile
import traceback
import asyncio
import secrets
import random
import time
import datetime as _dt
import sqlite3 as _sqlite3
import mimetypes
import json
from typing import Optional, Any
from base64 import b64decode

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Depends
from pydantic import BaseModel, Field
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
import uvicorn
from openai import OpenAI

mimetypes.add_type("text/javascript", ".mjs")
mimetypes.add_type("application/wasm", ".wasm")

try:
    import httpx
    _HTTPX_OK = True
except ImportError:
    _HTTPX_OK = False

try:
    from Crypto.Cipher import AES
    _CRYPTO_OK = True
except ImportError:
    _CRYPTO_OK = False

try:
    import bcrypt
    _BCRYPT_OK = True
except ImportError:
    _BCRYPT_OK = False

try:
    import jwt as _jwt
    _JWT_OK = True
except ImportError:
    _JWT_OK = False

# 加载 ritan .env（复用飞书 SMTP 等配置）
try:
    from dotenv import load_dotenv as _load_dotenv
    _ENV_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "ritan", ".env")
    _ENV_PATH = os.path.abspath(_ENV_PATH)
    if os.path.isfile(_ENV_PATH):
        _load_dotenv(_ENV_PATH)
        print(f"  已加载环境变量: {_ENV_PATH}")
except Exception:
    pass

# 微信小程序凭证（留空 = 开发 mock 模式）
WECHAT_APPID  = os.getenv("WECHAT_APPID", "")
WECHAT_SECRET = os.getenv("WECHAT_SECRET", "")

# ==========================================================
# 路径配置
# ==========================================================
CODE_ROOT = os.path.dirname(os.path.abspath(__file__))

SKIN_MODEL_DIR = os.path.join(CODE_ROOT, "skin_model")
AGE_MODEL_DIR  = os.path.join(CODE_ROOT, "age_model")

sys.path.insert(0, SKIN_MODEL_DIR)
sys.path.insert(0, AGE_MODEL_DIR)

# ==========================================================
# 皮肤指标模型（懒加载）
# ==========================================================
import torch
from PIL import Image
from torchvision import transforms

_SKIN_READY  = False
_SKIN_MODELS = []
_SKIN_DEVICE = None

METRIC_CN = [
    '痘痘严重度', '黑头', '白头粉刺', '毛孔粗大', '过度出油',
    '皮肤刺激', '皮肤敏感度', '泛红程度', '眼周细纹', '眼部浮肿',
    '黑眼圈', '额头皱纹', '皮肤弹性', '缺水程度', '色斑',
    '痘印', '肤色不均', '雀斑',
]

_MEAN, _STD = [0.485, 0.456, 0.406], [0.229, 0.224, 0.225]
_SKIN_TTA = [
    transforms.Compose([transforms.Resize(256), transforms.CenterCrop(224),
                        transforms.ToTensor(), transforms.Normalize(_MEAN, _STD)]),
    transforms.Compose([transforms.RandomHorizontalFlip(p=1.0), transforms.Resize(256),
                        transforms.CenterCrop(224), transforms.ToTensor(), transforms.Normalize(_MEAN, _STD)]),
    transforms.Compose([transforms.Resize(256), transforms.RandomResizedCrop(224, scale=(0.88, 1.0)),
                        transforms.ToTensor(), transforms.Normalize(_MEAN, _STD)]),
    transforms.Compose([transforms.Resize(256), transforms.CenterCrop(224),
                        transforms.ColorJitter(brightness=0.15, contrast=0.15),
                        transforms.ToTensor(), transforms.Normalize(_MEAN, _STD)]),
    transforms.Compose([transforms.RandomHorizontalFlip(p=1.0), transforms.Resize(256),
                        transforms.RandomResizedCrop(224, scale=(0.88, 1.0)),
                        transforms.ToTensor(), transforms.Normalize(_MEAN, _STD)]),
]


def _skin_init_once():
    global _SKIN_READY, _SKIN_MODELS, _SKIN_DEVICE
    if _SKIN_READY:
        return
    from model import SkinMetricsModel
    _SKIN_DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    ckpt_dir = os.path.join(SKIN_MODEL_DIR, "checkpoints")
    for fold in range(1, 6):
        ckpt = os.path.join(ckpt_dir, f"fold{fold}_best.pth")
        if not os.path.exists(ckpt):
            continue
        m = SkinMetricsModel(pretrained=False).to(_SKIN_DEVICE)
        m.load_state_dict(torch.load(ckpt, map_location=_SKIN_DEVICE))
        m.eval()
        _SKIN_MODELS.append(m)
    _SKIN_READY = True


def run_skin_model(image_path: str) -> dict:
    _skin_init_once()
    img = Image.open(image_path).convert("RGB")
    fold_preds = []
    for m in _SKIN_MODELS:
        tta_preds = []
        with torch.no_grad():
            for tf in _SKIN_TTA:
                x = tf(img).unsqueeze(0).to(_SKIN_DEVICE)
                tta_preds.append(m(x).cpu())
        fold_preds.append(torch.stack(tta_preds).mean(0))
    final = torch.stack(fold_preds).mean(0).squeeze(0)
    return {name: round(final[i].item(), 2) for i, name in enumerate(METRIC_CN)}


# ==========================================================
# 年龄模型（懒加载）
# ==========================================================
import torch.nn as nn
from torchvision import models as tv_models

_AGE_READY  = False
_AGE_MODEL  = None
_AGE_DEVICE = None
_AGE_TFM = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
])


def _age_init_once():
    global _AGE_READY, _AGE_MODEL, _AGE_DEVICE
    if _AGE_READY:
        return
    _AGE_DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    m = tv_models.resnet18(weights=None)
    m.fc = nn.Linear(m.fc.in_features, 1)
    ckpt = os.path.join(AGE_MODEL_DIR, "best_model.pth")
    ckpt_data = torch.load(ckpt, map_location=_AGE_DEVICE)
    state = ckpt_data['model'] if isinstance(ckpt_data, dict) and 'model' in ckpt_data else ckpt_data
    m.load_state_dict(state)
    m.to(_AGE_DEVICE).eval()
    _AGE_MODEL = m
    _AGE_READY = True


def run_age_model(image_path: str) -> float:
    _age_init_once()
    img = Image.open(image_path).convert("RGB")
    x = _AGE_TFM(img).unsqueeze(0).to(_AGE_DEVICE)
    with torch.no_grad():
        age = _AGE_MODEL(x).item()
    return round(age, 1)


def calibrate_skin_age(age: float) -> float:
    """Apply a smooth display calibration to the raw age model output."""
    anchors = [
        (18.0, 1.8),
        (20.0, 2.5),
        (25.0, 5.4),
        (30.0, 8.0),
        (35.0, 10.5),
        (40.0, 12.5),
        (50.0, 14.6),
    ]
    if age <= anchors[0][0]:
        delta = anchors[0][1]
    elif age >= anchors[-1][0]:
        delta = anchors[-1][1]
    else:
        delta = anchors[-1][1]
        for (a0, d0), (a1, d1) in zip(anchors, anchors[1:]):
            if a0 <= age <= a1:
                t = (age - a0) / (a1 - a0)
                delta = d0 + (d1 - d0) * t
                break
    return round(age + delta, 1)


# ==========================================================
# LLM 客户端
# ==========================================================
LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_BASE_URL = "https://api.deepseek.com/v1"
LLM_MODEL    = "deepseek-chat"

llm_client = OpenAI(api_key=LLM_API_KEY, base_url=LLM_BASE_URL)

# ==========================================================
# JWT 认证配置
# ==========================================================
JWT_SECRET_KEY  = os.getenv("LANQIAO_JWT_SECRET", secrets.token_hex(32))
JWT_ALGORITHM   = "HS256"
JWT_EXPIRE_HOURS = 48

# ==========================================================
# 邮箱 SMTP 配置（复用 ritan 飞书邮箱）
# ==========================================================
SMTP_HOST     = os.getenv("RITAN_SMTP_HOST", "smtp.feishu.cn")
SMTP_PORT     = int(os.getenv("RITAN_SMTP_PORT", "465"))
SMTP_USERNAME = os.getenv("RITAN_SMTP_USERNAME", "")
SMTP_PASSWORD = os.getenv("RITAN_SMTP_PASSWORD", "")
SMTP_FROM     = os.getenv("RITAN_SMTP_FROM_NAME", "奥胶AI肌肤分析")

# ==========================================================
# JWT 工具函数
# ==========================================================

def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))

def create_jwt(user_id: int, email: str) -> str:
    now = _dt.datetime.now(_dt.timezone.utc)
    payload = {
        "sub": str(user_id), "email": email,
        "iat": now, "exp": now + _dt.timedelta(hours=JWT_EXPIRE_HOURS),
        "type": "access",
    }
    return _jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)

def decode_jwt(token: str) -> dict | None:
    try:
        payload = _jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        if payload.get("type") != "access":
            return None
        return payload
    except Exception:
        return None

# ==========================================================
# 系统提示词（含 SCINEXA 标准）
# ==========================================================
SYSTEM_PROMPT = """
你是一位专业的美肤顾问，服务于一款消费级皮肤检测 App。你的工作是根据 App 检测输出的皮肤指标数据，为用户生成个性化的护肤分析报告，帮助他们了解自己的皮肤状态并选择合适的护肤方向。这不是医疗诊断，而是美容护肤领域的专业建议，类似于专柜美肤顾问的角色。全程使用中文，人称统一使用"您"。

## 评估体系说明

我们从18项检测指标中提取9项进入皮肤老化评分，其余指标（痘痘、黑头、出油、缺水、敏感度等）作为肤质背景参考。

**内源性老化指标（3项，反映自然衰老进程）**
- 眼周细纹：眼部皮肤最薄，胶原流失最先在此显现
- 额头皱纹：表情纹固化与真皮层支撑力下降的综合体现
- 皮肤弹性：弹性蛋白与胶原蛋白整体流失程度

**外源性老化指标（6项，反映紫外线与环境的累积损伤）**
- 色斑：日晒激活黑色素细胞后形成的局部色素沉积
- 肤色不均：色素分布不均，光老化的整体肤色表现
- 雀斑：遗传基础上由紫外线持续加深的色素点
- 泛红程度：光老化导致的毛细血管脆化与扩张
- 毛孔粗大：皮脂腺受光损伤活跃，毛孔弹性下降
- 黑眼圈：眶周色素沉积与局部微循环不畅

评分范围0–5分，越高越严重。老化类型判断：内源性均分 > 外源性均分 → 自然衰老为主；外源性均分更高 → 光老化为主；两者接近 → 复合型老化。

## 输出格式

只输出以下两个章节，标题一字不差：

**【皮肤状态综合分析】**
将预测年龄、老化类型判断、各问题群的综合分析写成3-4段连贯叙述。第一段点出年龄解读和主导老化类型；后续段落每段聚焦一个问题群，把共同成因的指标合并描述，说清楚"这些问题为什么会同时出现"和"对皮肤整体的影响"。不要逐条列举指标，不要在正文中出现数字分数。

**【护肤方案建议】**
围绕主导老化类型写一套连贯的护肤策略，分早晚两个场景，包含核心成分方向和需要调整的生活习惯。用段落叙述，不要碎片列表。

结尾固定一行：「本报告为 AI 辅助分析，建议结合皮肤科医生意见。」

---

## 示例一

**输入数据：**
预测皮肤年龄：34.0 岁
内源性老化指标：眼周细纹（中度）、额头皱纹（中度）、皮肤弹性（中度）
外源性老化指标：色斑（中度）、肤色不均（中度）、雀斑（严重）、泛红程度（中度）、毛孔粗大（轻度）、黑眼圈（中度）
主导老化类型：复合型（内源外源程度相当）
其他肤质参考：缺水程度（轻度）、皮肤敏感度（轻度）

**输出报告：**

**【皮肤状态综合分析】**

从检测数据来看，您的皮肤老化程度较为明显，自然衰老与光老化的信号同时出现，属于复合型老化——两条老化轨道同步推进，整体状态比实际年龄看起来更"有岁月感"，是需要系统性干预的阶段。

面部结构性老化是最明显的内在信号。眼周和额头的纹路都已进入中度阶段，皮肤整体支撑力也明显下滑——这三者本质上是同一个问题的不同表现：真皮层的胶原蛋白和弹性蛋白持续流失，皮肤的"骨架"开始松动。眼周皮肤最薄，最先暴露问题；额头因日常表情丰富，动态纹逐渐固化；弹性整体下降则说明这不只是局部问题，而是皮肤深层状态的退化。

在色素方面，雀斑、色斑与整体肤色不均叠加出现，本质上都是紫外线在皮肤上留下的历史账单。长期日晒让黑色素细胞持续被激活，色素在不同深度和位置沉积，整体肤色因此显得暗沉斑驳。泛红与黑眼圈的存在进一步加重了气色不佳的视觉感受，前者与毛细血管受光老化影响脆化有关，后者则兼有色素沉积和局部循环双重因素。两类老化并行意味着护肤不能只盯一个方向，抗皱与防晒淡斑缺了任何一块，另一块的努力都会打折扣。

**【护肤方案建议】**

早晨的重心放在防御上。洁面后先用含烟酰胺或维C衍生物的精华打底，抑制色素生成并提亮肤色；保湿选择含神经酰胺和多肽的乳液，为皮肤补充结构性支撑；防晒是早晨护肤的最后一步也是最重要一步，SPF50+物理化学双重防护，户外每两小时补涂，这是阻止光老化继续恶化的底线。

晚间是修复的核心窗口。引入含视黄醇（A醇）的抗老精华，从刺激胶原合成的根源着手，初期选低浓度慢慢适应；眼周单独使用含肽类和咖啡因的眼霜，兼顾细纹和黑眼圈；面霜选择修护型配方，让皮肤屏障在夜间得到充分恢复。每周可加做一次补水面膜配合轻柔按摩，改善局部循环。

生活习惯上，防晒意识需要从"出门才涂"升级为"只要有光就涂"，室内靠窗、驾车同样有紫外线累积。睡眠质量直接影响胶原修复速率，规律作息是任何护肤品都替代不了的基础。

本报告为 AI 辅助分析，建议结合皮肤科医生意见。

---

## 示例二

**输入数据：**
预测皮肤年龄：21.0 岁
内源性老化指标：眼周细纹（正常）、额头皱纹（正常）、皮肤弹性（正常）
外源性老化指标：色斑（严重）、肤色不均（轻度）、雀斑（严重）、泛红程度（正常）、毛孔粗大（正常）、黑眼圈（正常）
主导老化类型：外源性（光老化为主）
其他肤质参考：过度出油（中度）、痘痘严重度（轻度）

**输出报告：**

**【皮肤状态综合分析】**

您的皮肤在结构层面非常年轻，几乎看不到自然衰老的痕迹；但检测数据里藏着一个不容忽视的信号——光损伤已经悄悄开始积累，只是还没反映在皱纹和松弛上。这是一个典型的"年轻但晒伤"案例，属于纯粹的外源性老化，护肤的重心指向非常明确：日晒防护与色素管理。

皮肤上最突出的问题是高度集中的光损伤型色素。雀斑和色斑都已达到较明显的程度——雀斑更多受遗传底色影响，色斑更多是后天日晒积累的结果，但两者都会在紫外线的持续作用下加深，肤色不均则是它们叠加后的整体视觉表现，让皮肤显得深浅不一、缺乏透亮感。值得注意的是，泛红、毛孔、黑眼圈目前都处于健康水平，说明皮肤屏障完整、血管状态稳定，光老化还停留在浅层色素阶段，尚未伤及更深的皮肤结构——这是一个相对有利的干预窗口，越早采取行动效果越好。

**【护肤方案建议】**

护肤方案可以很聚焦，核心只有两件事：防晒和淡斑。早晨选高倍数防晒（SPF50+ PA++++），油皮可选轻薄乳液或喷雾型避免闷痘感，户外频繁活动时每两小时补涂；同时搭配含抗氧化成分的精华（维C或白藜芦醇），从源头减少日晒产生的自由基，降低色素被激活的概率。

晚间重点放在色素代谢上。烟酰胺是最适合您当前状态的核心成分，能抑制黑色素向角质层转移，长期使用对雀斑和色斑都有淡化效果；可配合传明酸或熊果苷类精华，温和而持续。由于皮脂分泌偏旺盛，整套护肤流程保持清爽即可，不需要厚重的抗衰面霜，一瓶控油保湿乳足够。

生活习惯上最关键的一条：主动减少不必要的日晒暴露，外出备好帽子和遮阳伞。对您目前的皮肤状态来说，这个习惯的改善效果比换任何产品都来得直接。

本报告为 AI 辅助分析，建议结合皮肤科医生意见。
""".strip()


# 9项老化指标
INTRINSIC = ['眼周细纹', '额头皱纹', '皮肤弹性']
EXTRINSIC = ['色斑', '肤色不均', '雀斑', '泛红程度', '毛孔粗大', '黑眼圈']
AGING_ALL = INTRINSIC + EXTRINSIC

# 其余肤质参考指标
CONDITION = ['缺水程度', '眼部浮肿', '过度出油', '皮肤刺激', '皮肤敏感度',
             '痘痘严重度', '黑头', '白头粉刺', '痘印']

# 问题群（仅基于9项老化指标）
CLUSTERS = [
    ("结构性老化",   ['眼周细纹', '额头皱纹', '皮肤弹性'],    "胶原蛋白与弹性蛋白流失"),
    ("色素与肤色",   ['色斑', '肤色不均', '雀斑'],            "紫外线累积、黑色素代谢失衡"),
    ("血管与循环",   ['泛红程度', '黑眼圈'],                  "毛细血管脆化、眶周循环不畅"),
    ("毛孔与皮脂",   ['毛孔粗大'],                           "皮脂腺受光损伤活跃、毛孔弹性下降"),
]


def _level(s):
    if s >= 4.0: return "严重"
    if s >= 2.5: return "中度"
    if s >= 1.0: return "轻度"
    return "正常"


def build_user_prompt(age: float, skin_scores: dict) -> str:
    intr_scores = {k: skin_scores[k] for k in INTRINSIC if k in skin_scores}
    extr_scores = {k: skin_scores[k] for k in EXTRINSIC if k in skin_scores}
    intr_avg = sum(intr_scores.values()) / len(intr_scores) if intr_scores else 0
    extr_avg = sum(extr_scores.values()) / len(extr_scores) if extr_scores else 0

    if intr_avg > extr_avg + 0.3:
        dominant = "内源性（自然衰老为主）"
    elif extr_avg > intr_avg + 0.3:
        dominant = "外源性（光老化为主）"
    else:
        dominant = "复合型（内源外源程度相当）"

    # 计算各问题群均分，取前2-3个
    cluster_scores = []
    for name, keys, cause in CLUSTERS:
        vals = [skin_scores[k] for k in keys if k in skin_scores]
        if vals and sum(vals) / len(vals) >= 1.0:
            avg = sum(vals) / len(vals)
            members = [(k, skin_scores[k]) for k in keys if k in skin_scores]
            cluster_scores.append((avg, name, members, cause))
    cluster_scores.sort(reverse=True)
    top_clusters = cluster_scores[:3]

    # 肤质背景参考（非老化指标）
    cond_notes = [(k, skin_scores[k]) for k in CONDITION if k in skin_scores and skin_scores[k] >= 1.0]

    lines = [
        f"预测皮肤年龄：{age:.1f} 岁",
        "",
        "内源性老化指标（自然衰老）：" + "、".join(f"{k}（{_level(v)}）" for k, v in intr_scores.items()),
        "外源性老化指标（光老化）：" + "、".join(f"{k}（{_level(v)}）" for k, v in extr_scores.items()),
        f"主导老化类型：{dominant}",
        "",
        "突出问题群（按严重程度排序）：",
    ]
    for i, (avg, name, members, cause) in enumerate(top_clusters, 1):
        member_str = "、".join(f"{k}（{_level(v)}）" for k, v in sorted(members, key=lambda x: -x[1]))
        lines.append(f"  {i}. 【{name}】成因：{cause}；表现：{member_str}")

    if cond_notes:
        lines.append("")
        lines.append("其他肤质参考：" + "、".join(f"{k}（{_level(v)}）" for k, v in cond_notes))

    lines += [
        "",
        "请根据以上数据，参照示例的写作风格，输出两个章节的报告：",
        "**【皮肤状态综合分析】** 和 **【护肤方案建议】**",
        "人称统一用【您】，正文不出现数字分数，全程中文。",
    ]
    return "\n".join(lines)


# ==========================================================
# FastAPI
# ==========================================================
IMAGE_EXTS = (".png", ".jpg", ".jpeg", ".bmp", ".webp")
TMP_DIR = tempfile.mkdtemp(prefix="skinagent_")
UPLOADS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "uploads")
os.makedirs(UPLOADS_DIR, exist_ok=True)

app = FastAPI(title="皮肤智能分析系统 API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 最多同时 3 个请求跑模型推理（CPU 密集），LLM 调用不受限（网络 IO）
_INFER_SEM: asyncio.Semaphore = None

_DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "records.db")

def _get_db():
    conn = _sqlite3.connect(_DB_PATH)
    conn.row_factory = _sqlite3.Row
    return conn

def _init_db():
    conn = _get_db()
    conn.executescript('''
        CREATE TABLE IF NOT EXISTS users (
            id       INTEGER PRIMARY KEY AUTOINCREMENT,
            openid   TEXT UNIQUE,
            phone    TEXT UNIQUE,
            created_at TEXT DEFAULT (datetime('now','localtime'))
        );
        CREATE TABLE IF NOT EXISTS sessions (
            token      TEXT PRIMARY KEY,
            openid     TEXT NOT NULL,
            expires_at TEXT NOT NULL DEFAULT '2099-01-01 00:00:00',
            created_at TEXT DEFAULT (datetime('now','localtime'))
        );
        CREATE TABLE IF NOT EXISTS records (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            openid     TEXT NOT NULL,
            score      INTEGER,
            skin_age   REAL,
            glogau_level TEXT,
            glogau_desc  TEXT,
            report     TEXT,
            result_json  TEXT,
            date       TEXT,
            front_img  TEXT,
            left_img   TEXT,
            right_img  TEXT,
            created_at TEXT DEFAULT (datetime('now','localtime'))
        );
        CREATE TABLE IF NOT EXISTS email_users (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            email         TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            is_active     INTEGER DEFAULT 1,
            last_login_at TEXT,
            created_at    TEXT DEFAULT (datetime('now','localtime'))
        );
        CREATE TABLE IF NOT EXISTS email_verify_codes (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            email      TEXT NOT NULL,
            code       TEXT NOT NULL,
            expires_at TEXT NOT NULL,
            attempts   INTEGER DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now','localtime'))
        );
        CREATE TABLE IF NOT EXISTS privacy_consents (
            id                 TEXT PRIMARY KEY,
            session_id         TEXT NOT NULL,
            user_id            INTEGER,
            source_page        TEXT NOT NULL,
            analysis_use       INTEGER NOT NULL DEFAULT 1,
            research_use       INTEGER NOT NULL DEFAULT 0,
            service_followup   INTEGER NOT NULL DEFAULT 0,
            contact            TEXT DEFAULT '',
            policy_version     TEXT NOT NULL DEFAULT '2026-07-29',
            created_at         TEXT DEFAULT (datetime('now','localtime'))
        );
        CREATE TABLE IF NOT EXISTS analytics_events (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id    TEXT NOT NULL,
            event_name    TEXT NOT NULL,
            source_page   TEXT NOT NULL,
            metadata_json TEXT DEFAULT '{}',
            created_at    TEXT DEFAULT (datetime('now','localtime'))
        );
        CREATE TABLE IF NOT EXISTS business_leads (
            id             TEXT PRIMARY KEY,
            lead_type      TEXT NOT NULL,
            source_page    TEXT NOT NULL,
            name           TEXT DEFAULT '',
            contact        TEXT NOT NULL,
            company        TEXT DEFAULT '',
            category       TEXT DEFAULT '',
            annual_volume  TEXT DEFAULT '',
            description    TEXT DEFAULT '',
            status         TEXT NOT NULL DEFAULT 'new',
            created_at     TEXT DEFAULT (datetime('now','localtime'))
        );
        CREATE INDEX IF NOT EXISTS idx_privacy_consents_session
            ON privacy_consents(session_id, created_at);
        CREATE INDEX IF NOT EXISTS idx_analytics_events_funnel
            ON analytics_events(source_page, event_name, created_at);
        CREATE INDEX IF NOT EXISTS idx_business_leads_created
            ON business_leads(created_at);
    ''')
    conn.commit()
    conn.close()

def _migrate_db():
    """升级旧 DB：补缺失的列（ALTER TABLE 若列已存在会抛异常，直接忽略）。"""
    conn = _get_db()
    for sql in [
        "ALTER TABLE sessions ADD COLUMN expires_at TEXT NOT NULL DEFAULT '2099-01-01 00:00:00'",
        "ALTER TABLE records ADD COLUMN front_img TEXT",
        "ALTER TABLE records ADD COLUMN left_img TEXT",
        "ALTER TABLE records ADD COLUMN right_img TEXT",
        "ALTER TABLE records ADD COLUMN user_id INTEGER REFERENCES email_users(id)",
        "ALTER TABLE sessions ADD COLUMN user_type TEXT DEFAULT ''",
    ]:
        try:
            conn.execute(sql)
            conn.commit()
        except Exception:
            pass
    conn.close()

def _token_to_openid(token: str) -> str | None:
    conn = _get_db()
    row = conn.execute(
        "SELECT openid FROM sessions WHERE token=? AND expires_at > datetime('now')",
        (token,)
    ).fetchone()
    conn.close()
    return row["openid"] if row else None

# ==========================================================
# JWT 鉴权依赖（可选：不带 token 返回 None，不拦截）
# ==========================================================
from fastapi import Header as _Header

def get_optional_user(authorization: str | None = _Header(None)) -> dict | None:
    """从 Authorization: Bearer <token> 提取当前用户，无 token 时返回 None。"""
    if not authorization or not authorization.startswith("Bearer "):
        return None
    payload = decode_jwt(authorization[7:])
    if not payload:
        return None
    return {"user_id": int(payload["sub"]), "email": payload["email"]}

def get_current_user(authorization: str | None = _Header(None)) -> dict:
    """从 Authorization: Bearer <token> 提取当前用户，无 token 或无效时 401。"""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="请先登录")
    payload = decode_jwt(authorization[7:])
    if not payload:
        raise HTTPException(status_code=401, detail="登录已过期，请重新登录")
    return {"user_id": int(payload["sub"]), "email": payload["email"]}


# ==========================================================
# 邮箱 SMTP 发送
# ==========================================================
def _send_email_code(to_email: str, code: str) -> bool:
    """发送验证码邮件。SMTP 未配置时抛出异常。"""
    if not SMTP_USERNAME or not SMTP_PASSWORD:
        raise HTTPException(status_code=500, detail="邮件服务未配置，请联系管理员")

    import smtplib
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart

    subject = f"【奥胶AI】邮箱验证码：{code}"
    html_body = f"""\
<html><body style="font-family:'PingFang SC','Microsoft YaHei',sans-serif;">
<div style="max-width:480px;margin:20px auto;border:1px solid #e2e8f0;border-radius:12px;overflow:hidden;">
<div style="background:linear-gradient(135deg,#1a1a2e,#16213e);padding:28px 20px;text-align:center;">
<h1 style="color:#e8d5b7;margin:0;font-size:20px;">奥胶 AI 肌肤分析</h1>
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
    try:
        server = smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT)
        server.login(SMTP_USERNAME, SMTP_PASSWORD)
        server.sendmail(SMTP_USERNAME, to_email, msg.as_string())
        server.quit()
        return True
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"邮件发送失败: {e}")


# ==========================================================
# 邮箱认证 Pydantic 模型
# ==========================================================
import re as _re

class EmailSendCodeRequest(BaseModel):
    email: str

class EmailRegisterRequest(BaseModel):
    email: str
    code: str
    password: str

class EmailLoginRequest(BaseModel):
    email: str
    password: str

class EmailResetPasswordRequest(BaseModel):
    email: str
    code: str
    new_password: str

def _validate_email(email: str) -> str:
    email = email.strip().lower()
    if not _re.match(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", email):
        raise HTTPException(status_code=400, detail="邮箱格式不正确")
    return email

def _validate_password(pw: str) -> str:
    if len(pw) < 8 or len(pw) > 12:
        raise HTTPException(status_code=400, detail="密码长度须为 8-12 位")
    if not _re.search(r"[A-Z]", pw):
        raise HTTPException(status_code=400, detail="密码必须包含至少一个大写字母")
    if not _re.search(r"[a-z]", pw):
        raise HTTPException(status_code=400, detail="密码必须包含至少一个小写字母")
    if not _re.search(r"[0-9]", pw):
        raise HTTPException(status_code=400, detail="密码必须包含至少一个数字")
    if not _re.search(r"[!@#$%^&*()_+\-=\[\]{};':\"\\|,.<>\/?`~]", pw):
        raise HTTPException(status_code=400, detail="密码必须包含至少一个特殊符号")
    return pw

MAX_VERIFY_ATTEMPTS = 5
RESEND_COOLDOWN_SECONDS = 60


def _ensure_user_openid(openid: str):
    conn = _get_db()
    conn.execute("INSERT OR IGNORE INTO users (openid) VALUES (?)", (openid,))
    conn.commit()
    conn.close()

def _ensure_user_phone(phone: str) -> str:
    conn = _get_db()
    pseudo = "phone_" + phone
    conn.execute("INSERT OR IGNORE INTO users (openid, phone) VALUES (?,?)", (pseudo, phone))
    conn.execute("UPDATE users SET phone=? WHERE openid=?", (phone, pseudo))
    conn.commit()
    conn.close()
    return pseudo

@app.on_event("startup")
async def _startup():
    global _INFER_SEM
    _INFER_SEM = asyncio.Semaphore(3)
    _init_db()
    _migrate_db()


def _save_upload(f: UploadFile) -> str:
    ext = os.path.splitext(f.filename)[1].lower()
    if ext not in IMAGE_EXTS:
        raise HTTPException(status_code=400, detail=f"不支持的文件类型：{ext}")
    tmp = os.path.join(TMP_DIR, f"{uuid.uuid4()}{ext}")
    with open(tmp, "wb") as out:
        shutil.copyfileobj(f.file, out)
    return tmp


def _run_inference(paths: list) -> tuple:
    """同步：跑模型推理，返回 (age, skin_scores)。在线程池中执行。"""
    front_path = paths[0]
    age = calibrate_skin_age(run_age_model(front_path))
    scores_list = [run_skin_model(p) for p in paths]
    skin_scores = {
        k: round(sum(s[k] for s in scores_list) / len(scores_list), 2)
        for k in scores_list[0]
    }
    return age, skin_scores


def _run_single_inference(image_path: str) -> tuple:
    """同步：单张照片推理，返回 (age, skin_scores)。"""
    age = calibrate_skin_age(run_age_model(image_path))
    skin_scores = run_skin_model(image_path)
    return age, skin_scores


def _call_llm(prompt: str, max_tokens: int) -> str:
    """同步：调 LLM，返回文本。在线程池中执行。"""
    r = llm_client.chat.completions.create(
        model=LLM_MODEL,
        temperature=0.5,
        max_tokens=max_tokens,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": prompt},
        ],
    )
    return r.choices[0].message.content.strip()


def _clean_body(text: str, stop_markers: list) -> str:
    lines = text.strip().splitlines()
    result = []
    for line in lines:
        s = line.strip()
        if any(m in s for m in stop_markers):
            break
        if s.startswith("**【") and s.endswith("】**"):
            continue
        result.append(line)
    return "\n".join(result).strip()


class PrivacyConsentRequest(BaseModel):
    session_id: str
    source_page: str = "skin_mobile"
    research_use: bool = False
    service_followup: bool = False
    contact: str = ""


class AnalyticsEventRequest(BaseModel):
    session_id: str
    event_name: str
    source_page: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class BusinessLeadRequest(BaseModel):
    lead_type: str
    source_page: str
    name: str = ""
    contact: str
    company: str = ""
    category: str = ""
    annual_volume: str = ""
    description: str = ""


_ALLOWED_EVENT_NAMES = {
    "skin_page_enter",
    "skin_consent_confirmed",
    "skin_camera_started",
    "skin_capture_completed",
    "skin_report_generated",
    "skin_product_clicked",
    "skin_appointment_clicked",
    "skin_consult_clicked",
    "skin_lead_submitted",
    "skin_retest_clicked",
    "skin_retest_comparison_viewed",
    "skin_business_clicked",
    "skin_trust_expanded",
    "dfu_page_enter",
    "dfu_patient_clicked",
    "dfu_doctor_clicked",
    "dfu_business_clicked",
}
_ALLOWED_LEAD_TYPES = {
    "product",
    "appointment",
    "custom_consult",
    "business_api",
    "business_custom",
    "business_technology",
    "business_general",
    "privacy_request",
}


def _clean_short(value: str, limit: int, field_name: str) -> str:
    cleaned = " ".join((value or "").strip().split())
    if len(cleaned) > limit:
        raise HTTPException(status_code=400, detail=f"{field_name}内容过长")
    return cleaned


def _validate_session_id(value: str) -> str:
    value = _clean_short(value, 80, "会话编号")
    if not value or not _re.match(r"^[A-Za-z0-9_-]+$", value):
        raise HTTPException(status_code=400, detail="会话编号格式不正确")
    return value


@app.post("/api/consents")
async def save_privacy_consent(
    req: PrivacyConsentRequest,
    user: dict | None = Depends(get_optional_user),
):
    session_id = _validate_session_id(req.session_id)
    source_page = _clean_short(req.source_page, 40, "来源页面") or "skin_mobile"
    contact = _clean_short(req.contact, 100, "联系方式") if req.service_followup else ""
    if req.service_followup and not contact:
        raise HTTPException(status_code=400, detail="选择后续服务时请填写联系方式")

    consent_id = "consent_" + secrets.token_urlsafe(18)
    conn = _get_db()
    conn.execute(
        """
        INSERT INTO privacy_consents
        (id,session_id,user_id,source_page,analysis_use,research_use,service_followup,contact)
        VALUES (?,?,?,?,1,?,?,?)
        """,
        (
            consent_id,
            session_id,
            user["user_id"] if user else None,
            source_page,
            1 if req.research_use else 0,
            1 if req.service_followup else 0,
            contact,
        ),
    )
    conn.commit()
    conn.close()
    return {"success": True, "consent_id": consent_id}


@app.post("/api/events")
async def save_analytics_event(req: AnalyticsEventRequest):
    session_id = _validate_session_id(req.session_id)
    event_name = _clean_short(req.event_name, 60, "事件名称")
    source_page = _clean_short(req.source_page, 40, "来源页面")
    if event_name not in _ALLOWED_EVENT_NAMES:
        raise HTTPException(status_code=400, detail="不支持的事件名称")

    safe_metadata = json.dumps(req.metadata or {}, ensure_ascii=False)
    if len(safe_metadata) > 2000:
        raise HTTPException(status_code=400, detail="事件参数过长")
    conn = _get_db()
    conn.execute(
        """
        INSERT INTO analytics_events (session_id,event_name,source_page,metadata_json)
        VALUES (?,?,?,?)
        """,
        (session_id, event_name, source_page, safe_metadata),
    )
    conn.commit()
    conn.close()
    return {"success": True}


@app.post("/api/leads")
async def save_business_lead(req: BusinessLeadRequest):
    lead_type = _clean_short(req.lead_type, 40, "需求类型")
    if lead_type not in _ALLOWED_LEAD_TYPES:
        raise HTTPException(status_code=400, detail="不支持的需求类型")

    contact = _clean_short(req.contact, 100, "联系方式")
    if len(contact) < 5:
        raise HTTPException(status_code=400, detail="请填写有效的手机、微信或邮箱")

    lead_id = "lead_" + secrets.token_urlsafe(16)
    values = (
        lead_id,
        lead_type,
        _clean_short(req.source_page, 40, "来源页面"),
        _clean_short(req.name, 40, "姓名"),
        contact,
        _clean_short(req.company, 100, "公司名称"),
        _clean_short(req.category, 80, "业务品类"),
        _clean_short(req.annual_volume, 80, "业务体量"),
        _clean_short(req.description, 1000, "需求描述"),
    )
    conn = _get_db()
    conn.execute(
        """
        INSERT INTO business_leads
        (id,lead_type,source_page,name,contact,company,category,annual_volume,description)
        VALUES (?,?,?,?,?,?,?,?,?)
        """,
        values,
    )
    conn.commit()
    conn.close()
    return {"success": True, "lead_id": lead_id}


@app.post("/api/analyze")
async def analyze(
    front: UploadFile = File(...),
    left:  UploadFile = File(...),
    right: UploadFile = File(...),
    user: dict | None = Depends(get_optional_user),
):
    """
    上传正脸/左脸/右脸三张图片，返回综合皮肤分析结果。
    照片永久保存至 uploads/ 目录。
    模型推理受信号量限制（最多 3 并发），LLM 两段并行调用。
    可选 JWT 鉴权（Authorization: Bearer <token>）。
    """
    saved = []
    photo_names = []
    try:
        # 永久保存到 uploads/（和 /api/analyze-wx 行为一致）
        for f in (front, left, right):
            ext = os.path.splitext(f.filename)[1].lower()
            if ext not in IMAGE_EXTS:
                raise HTTPException(status_code=400, detail=f"不支持的文件类型：{ext}")
            fname = f"{uuid.uuid4()}{ext}"
            perm_path = os.path.join(UPLOADS_DIR, fname)
            with open(perm_path, "wb") as out:
                shutil.copyfileobj(f.file, out)
            saved.append(perm_path)
            photo_names.append(fname)

        # 模型推理放线程池，最多 3 个请求同时跑（防止 CPU 过载）
        async with _INFER_SEM:
            age, skin_scores = await asyncio.to_thread(_run_inference, saved)

        data_summary = build_user_prompt(age, skin_scores)
        DISCLAIMER     = "本报告为 AI 辅助分析"
        SECTION2_TITLE = "【护肤方案建议】"

        p1 = (
            f"{data_summary}\n\n"
            "请用150-180字的中文，写出皮肤状态综合分析的正文，不写标题：\n"
            "一句话点明主导老化类型，再用2-3句合并描述最突出的问题及成因，语气简洁专业。\n"
            "用'您'称呼，不出现任何数字分数，只输出正文，字数控制在150-180字之间。"
        )
        p2 = (
            f"{data_summary}\n\n"
            "请用150-180字的中文，写出护肤方案建议的正文，不写标题：\n"
            "【重要】不要重复皮肤分析内容，直接给出行动方案。\n"
            "早晨：推荐1-2个核心功效成分（如烟酰胺、维C等）及对应的市面常见产品类型；\n"
            "晚间：推荐1-2个修护成分及对应产品类型；\n"
            "最后1句给出最关键的生活习惯建议。\n"
            "用'您'称呼，不出现任何数字分数，只输出正文，字数控制在150-180字之间。"
        )

        # 两段 LLM 并行调用，总时间 ≈ 单次时间
        raw1, raw2 = await asyncio.gather(
            asyncio.to_thread(_call_llm, p1, 270),
            asyncio.to_thread(_call_llm, p2, 270),
        )

        body1 = _clean_body(raw1, [DISCLAIMER, SECTION2_TITLE])
        body2 = _clean_body(raw2, [DISCLAIMER])

        report = (
            "**【皮肤状态综合分析】**\n\n"
            + body1
            + "\n\n**【护肤方案建议】**\n\n"
            + body2
            + "\n\n本报告为 AI 辅助分析，建议结合皮肤科医生意见。"
        )

        return {
            "status":      "ok",
            "age":         age,
            "skin_scores": skin_scores,
            "report":      report,
            "photo_names": photo_names,  # [front, left, right]
        }

    except Exception as e:
        traceback.print_exc()
        # 分析失败时删掉已保存的照片
        for p in saved:
            if os.path.exists(p):
                os.remove(p)
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": str(e)},
        )


@app.post("/api/analyze-single")
async def analyze_single(
    image: UploadFile = File(...),
    consent_id: str = Form(""),
    session_id: str = Form(""),
    research_consent: str = Form("false"),
    user: dict | None = Depends(get_optional_user),
):
    """
    单张照片分析接口 — 上传一张面部照片，返回皮肤年龄 + 18项指标 + AI 报告。
    模型推理受信号量限制（最多 3 并发），LLM 两段并行调用。
    """
    saved = []
    photo_name = ""
    retain_for_research = False
    try:
        # 默认只在临时目录处理。只有存在明确的研究授权记录时才匿名保留。
        if session_id:
            _validate_session_id(session_id)
        requested_research = research_consent.strip().lower() in {"1", "true", "yes"}
        if requested_research and consent_id:
            conn = _get_db()
            consent_row = conn.execute(
                """
                SELECT id FROM privacy_consents
                WHERE id=? AND session_id=? AND analysis_use=1 AND research_use=1
                """,
                (consent_id, session_id),
            ).fetchone()
            conn.close()
            retain_for_research = bool(consent_row)

        ext = os.path.splitext(image.filename)[1].lower()
        if ext not in IMAGE_EXTS:
            raise HTTPException(status_code=400, detail=f"不支持的文件类型：{ext}")
        fname = f"{uuid.uuid4()}{ext}"
        image_path = os.path.join(UPLOADS_DIR if retain_for_research else TMP_DIR, fname)
        with open(image_path, "wb") as out:
            shutil.copyfileobj(image.file, out)
        saved.append(image_path)
        photo_name = fname if retain_for_research else ""

        # 单图推理：age 和 skin 都在这张图上跑
        async with _INFER_SEM:
            age, skin_scores = await asyncio.to_thread(_run_single_inference, saved[0])

        data_summary = build_user_prompt(age, skin_scores)
        DISCLAIMER     = "本报告为 AI 辅助分析"
        SECTION2_TITLE = "【护肤方案建议】"

        p1 = (
            f"{data_summary}\n\n"
            "请用150-180字的中文，写出皮肤状态综合分析的正文，不写标题：\n"
            "一句话点明主导老化类型，再用2-3句合并描述最突出的问题及成因，语气简洁专业。\n"
            "用'您'称呼，不出现任何数字分数，只输出正文，字数控制在150-180字之间。"
        )
        p2 = (
            f"{data_summary}\n\n"
            "请用150-180字的中文，写出护肤方案建议的正文，不写标题：\n"
            "【重要】不要重复皮肤分析内容，直接给出行动方案。\n"
            "早晨：推荐1-2个核心功效成分（如烟酰胺、维C等）及对应的市面常见产品类型；\n"
            "晚间：推荐1-2个修护成分及对应产品类型；\n"
            "最后1句给出最关键的生活习惯建议。\n"
            "用'您'称呼，不出现任何数字分数，只输出正文，字数控制在150-180字之间。"
        )

        raw1, raw2 = await asyncio.gather(
            asyncio.to_thread(_call_llm, p1, 270),
            asyncio.to_thread(_call_llm, p2, 270),
        )

        body1 = _clean_body(raw1, [DISCLAIMER, SECTION2_TITLE])
        body2 = _clean_body(raw2, [DISCLAIMER])

        report = (
            "**【皮肤状态综合分析】**\n\n"
            + body1
            + "\n\n**【护肤方案建议】**\n\n"
            + body2
            + "\n\n本报告为 AI 辅助分析，建议结合皮肤科医生意见。"
        )

        if not retain_for_research and os.path.exists(saved[0]):
            os.remove(saved[0])
            saved.clear()

        return {
            "status":      "ok",
            "age":         age,
            "skin_scores": skin_scores,
            "report":      report,
            "photo_name":  photo_name,
            "retained_for_research": retain_for_research,
        }

    except Exception as e:
        traceback.print_exc()
        for p in saved:
            if os.path.exists(p):
                os.remove(p)
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": str(e)},
        )


@app.get("/api/health")
async def health():
    return {"status": "ok"}


# ==========================================================
# 微信小程序专用接口（接受 base64 图片）
# ==========================================================
class WxAnalyzeRequest(BaseModel):
    front: str  # base64 编码的图片
    left:  str
    right: str


@app.post("/api/analyze-wx")
async def analyze_wx(req: WxAnalyzeRequest, user: dict | None = Depends(get_optional_user)):
    saved = []
    photo_names = []  # 永久保存的文件名
    try:
        for b64 in (req.front, req.left, req.right):
            data = base64.b64decode(b64)
            fname = f"{uuid.uuid4()}.jpg"
            perm_path = os.path.join(UPLOADS_DIR, fname)
            with open(perm_path, "wb") as f:
                f.write(data)
            saved.append(perm_path)
            photo_names.append(fname)

        async with _INFER_SEM:
            age, skin_scores = await asyncio.to_thread(_run_inference, saved)

        data_summary = build_user_prompt(age, skin_scores)
        DISCLAIMER     = "本报告为 AI 辅助分析"
        SECTION2_TITLE = "【护肤方案建议】"

        p1 = (
            f"{data_summary}\n\n"
            "请用150-180字的中文，写出皮肤状态综合分析的正文，不写标题：\n"
            "一句话点明主导老化类型，再用2-3句合并描述最突出的问题及成因，语气简洁专业。\n"
            "用'您'称呼，不出现任何数字分数，只输出正文，字数控制在150-180字之间。"
        )
        p2 = (
            f"{data_summary}\n\n"
            "请用150-180字的中文，写出护肤方案建议的正文，不写标题：\n"
            "【重要】不要重复皮肤分析内容，直接给出行动方案。\n"
            "早晨：推荐1-2个核心功效成分及对应的市面常见产品类型；\n"
            "晚间：推荐1-2个修护成分及对应产品类型；\n"
            "最后1句给出最关键的生活习惯建议。\n"
            "用'您'称呼，不出现任何数字分数，只输出正文，字数控制在150-180字之间。"
        )

        raw1, raw2 = await asyncio.gather(
            asyncio.to_thread(_call_llm, p1, 270),
            asyncio.to_thread(_call_llm, p2, 270),
        )

        body1 = _clean_body(raw1, [DISCLAIMER, SECTION2_TITLE])
        body2 = _clean_body(raw2, [DISCLAIMER])

        report = (
            "**【皮肤状态综合分析】**\n\n"
            + body1
            + "\n\n**【护肤方案建议】**\n\n"
            + body2
            + "\n\n本报告为 AI 辅助分析，建议结合皮肤科医生意见。"
        )

        return {
            "status":      "ok",
            "age":         age,
            "skin_scores": skin_scores,
            "report":      report,
            "photo_names": photo_names,  # [front, left, right]
        }

    except Exception as e:
        traceback.print_exc()
        # 分析失败时删掉已保存的照片
        for p in saved:
            if os.path.exists(p):
                os.remove(p)
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": str(e)},
        )


# ==========================================================
# 微信登录接口
# ==========================================================

class WxLoginRequest(BaseModel):
    code: str

class BindPhoneRequest(BaseModel):
    code: str
    encryptedData: str
    iv: str


@app.post("/api/wx-login")
async def wx_login(req: WxLoginRequest):
    """微信 code 换 openid + token"""
    if not WECHAT_APPID or not WECHAT_SECRET:
        # 开发 mock 模式
        return {
            "token":  "mock_token_" + secrets.token_hex(8),
            "openid": "mock_openid_" + secrets.token_hex(8),
            "is_mock": True,
        }

    if not _HTTPX_OK:
        raise HTTPException(status_code=500, detail="请安装 httpx: pip install httpx")

    url = (
        "https://api.weixin.qq.com/sns/jscode2session"
        f"?appid={WECHAT_APPID}&secret={WECHAT_SECRET}"
        f"&js_code={req.code}&grant_type=authorization_code"
    )
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(url)

    data = resp.json()
    if "errcode" in data and data["errcode"] != 0:
        raise HTTPException(status_code=400, detail=f"微信错误: {data.get('errmsg')}")

    openid = data["openid"]
    _ensure_user_openid(openid)
    token = secrets.token_hex(32)
    expires_at = (_dt.datetime.now() + _dt.timedelta(days=30)).strftime('%Y-%m-%d %H:%M:%S')
    conn = _get_db()
    conn.execute("INSERT INTO sessions (token, openid, expires_at) VALUES (?,?,?)", (token, openid, expires_at))
    conn.commit()
    conn.close()
    return {"token": token, "openid": openid}


@app.post("/api/bind-phone")
async def bind_phone(req: BindPhoneRequest):
    """手机号换绑（需企业主体小程序）"""
    if not WECHAT_APPID or not WECHAT_SECRET:
        return {
            "token":       "mock_token_" + secrets.token_hex(8),
            "openid":      "mock_openid_" + secrets.token_hex(8),
            "phoneNumber": "138****0000",
            "is_mock": True,
        }

    if not _HTTPX_OK:
        raise HTTPException(status_code=500, detail="请安装 httpx: pip install httpx")
    if not _CRYPTO_OK:
        raise HTTPException(status_code=500, detail="请安装 pycryptodome: pip install pycryptodome")

    # 1. 用 code 换 session_key
    url = (
        "https://api.weixin.qq.com/sns/jscode2session"
        f"?appid={WECHAT_APPID}&secret={WECHAT_SECRET}"
        f"&js_code={req.code}&grant_type=authorization_code"
    )
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(url)

    data = resp.json()
    if "errcode" in data and data["errcode"] != 0:
        raise HTTPException(status_code=400, detail=f"微信错误: {data.get('errmsg')}")

    openid      = data["openid"]
    session_key = data["session_key"]

    # 2. AES-128-CBC 解密手机号
    try:
        key        = b64decode(session_key)
        iv_bytes   = b64decode(req.iv)
        encrypted  = b64decode(req.encryptedData)
        cipher     = AES.new(key, AES.MODE_CBC, iv_bytes)
        decrypted  = cipher.decrypt(encrypted)
        # 去掉 PKCS7 padding
        pad_len    = decrypted[-1]
        decrypted  = decrypted[:-pad_len]
        import json as _json
        phone_data  = _json.loads(decrypted.decode("utf-8"))
        phone_number = phone_data.get("phoneNumber", "")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"手机号解密失败: {e}")

    token = secrets.token_hex(32)
    # 实际项目：持久化 token → openid/phone
    return {"token": token, "openid": openid, "phoneNumber": phone_number}


# ==========================================================
# 手机号短信验证码接口
# ==========================================================

# 内存存储（生产环境换 Redis）
_sms_store: dict = {}    # phone -> {'code': str, 'expires': float}
_sms_tokens: dict = {}   # token -> {'phone': str}

# 腾讯云短信配置（留空 = mock 模式，直接返回验证码明文）
TENCENT_SMS_SECRET_ID  = os.getenv("TENCENT_SMS_SECRET_ID", "")
TENCENT_SMS_SECRET_KEY = os.getenv("TENCENT_SMS_SECRET_KEY", "")
TENCENT_SMS_APP_ID     = os.getenv("TENCENT_SMS_APP_ID", "")
TENCENT_SMS_SIGN       = os.getenv("TENCENT_SMS_SIGN", "兰峤AI测肤")
TENCENT_SMS_TEMPLATE   = os.getenv("TENCENT_SMS_TEMPLATE", "")


class SendSmsRequest(BaseModel):
    phone: str

class VerifySmsRequest(BaseModel):
    phone: str
    code: str


@app.post("/api/send-sms")
async def send_sms(req: SendSmsRequest):
    """发送短信验证码（无短信配置时返回明文，供开发测试）"""
    if not req.phone or not req.phone.isdigit() or len(req.phone) != 11:
        raise HTTPException(status_code=400, detail="手机号格式不正确")

    code = str(random.randint(100000, 999999))
    _sms_store[req.phone] = {"code": code, "expires": time.time() + 300}  # 5分钟有效

    if TENCENT_SMS_SECRET_ID and TENCENT_SMS_SECRET_KEY:
        # ---- 正式发送（腾讯云 SDK）----
        # pip install tencentcloud-sdk-python
        try:
            from tencentcloud.common import credential
            from tencentcloud.sms.v20210111 import sms_client, models as sms_models

            cred = credential.Credential(TENCENT_SMS_SECRET_ID, TENCENT_SMS_SECRET_KEY)
            client = sms_client.SmsClient(cred, "ap-guangzhou")
            req_obj = sms_models.SendSmsRequest()
            req_obj.SmsSdkAppId = TENCENT_SMS_APP_ID
            req_obj.SignName    = TENCENT_SMS_SIGN
            req_obj.TemplateId  = TENCENT_SMS_TEMPLATE
            req_obj.TemplateParamSet = [code, "5"]
            req_obj.PhoneNumberSet   = [f"+86{req.phone}"]
            client.SendSms(req_obj)
            return {"success": True}
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"短信发送失败: {e}")
    else:
        # ---- mock 模式：直接返回验证码（开发/测试用）----
        return {"success": True, "mock_code": code}


@app.post("/api/verify-sms")
async def verify_sms(req: VerifySmsRequest):
    """校验验证码，通过后签发 token"""
    record = _sms_store.get(req.phone)
    if not record:
        raise HTTPException(status_code=400, detail="请先获取验证码")
    if time.time() > record["expires"]:
        del _sms_store[req.phone]
        raise HTTPException(status_code=400, detail="验证码已过期，请重新获取")
    if record["code"] != req.code:
        raise HTTPException(status_code=400, detail="验证码错误")

    del _sms_store[req.phone]
    openid = _ensure_user_phone(req.phone)
    token = secrets.token_hex(32)
    expires_at = (_dt.datetime.now() + _dt.timedelta(days=30)).strftime('%Y-%m-%d %H:%M:%S')
    conn = _get_db()
    conn.execute("INSERT INTO sessions (token, openid, expires_at) VALUES (?,?,?)", (token, openid, expires_at))
    conn.commit()
    conn.close()
    return {"token": token, "phone": req.phone}


# ==========================================================
# 邮箱认证接口
# ==========================================================

@app.post("/api/email/send-code")
async def email_send_code(req: EmailSendCodeRequest):
    """发送 6 位验证码到邮箱（开发模式直接返回验证码）。"""
    email = _validate_email(req.email)
    now = _dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # 检查是否已注册
    conn = _get_db()
    existing = conn.execute("SELECT id FROM email_users WHERE email=?", (email,)).fetchone()
    if existing:
        # 已注册用户，走"忘记密码"流程
        conn.close()
        # 不暴露邮箱是否已注册
    else:
        conn.close()

    # 冷却检查（60 秒）
    conn = _get_db()
    last = conn.execute(
        "SELECT created_at FROM email_verify_codes WHERE email=? ORDER BY id DESC LIMIT 1",
        (email,)
    ).fetchone()
    if last:
        from datetime import datetime as _dt_parse
        last_ts = _dt_parse.strptime(last["created_at"], "%Y-%m-%d %H:%M:%S")
        elapsed = (_dt.datetime.now() - last_ts).total_seconds()
        if elapsed < RESEND_COOLDOWN_SECONDS:
            conn.close()
            wait = int(RESEND_COOLDOWN_SECONDS - elapsed)
            raise HTTPException(status_code=429, detail=f"请 {wait} 秒后再重新发送验证码")

    code = str(random.randint(100000, 999999))
    expires_at = (_dt.datetime.now() + _dt.timedelta(minutes=10)).strftime("%Y-%m-%d %H:%M:%S")
    conn.execute(
        "INSERT INTO email_verify_codes (email, code, expires_at) VALUES (?,?,?)",
        (email, code, expires_at)
    )
    conn.commit()
    conn.close()

    # 发送邮件
    _send_email_code(email, code)

    return {"success": True, "message": f"验证码已发送至 {email}，请查收邮件（10 分钟内有效）"}


@app.post("/api/email/register")
async def email_register(req: EmailRegisterRequest):
    """验证码校验 + 设置密码，完成注册，返回 JWT。"""
    email = _validate_email(req.email)
    code = req.code.strip()
    password = _validate_password(req.password)
    now = _dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if len(code) != 6 or not code.isdigit():
        raise HTTPException(status_code=400, detail="验证码为 6 位数字")

    conn = _get_db()

    # 检查是否已注册
    existing = conn.execute("SELECT id FROM email_users WHERE email=?", (email,)).fetchone()
    if existing:
        conn.close()
        raise HTTPException(status_code=409, detail="该邮箱已被注册，请直接登录")

    # 校验验证码
    row = conn.execute(
        "SELECT id, code, expires_at, attempts FROM email_verify_codes WHERE email=? ORDER BY id DESC LIMIT 1",
        (email,)
    ).fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=400, detail="请先获取验证码")
    if row["expires_at"] < now:
        conn.close()
        raise HTTPException(status_code=400, detail="验证码已过期，请重新获取")
    if row["attempts"] >= MAX_VERIFY_ATTEMPTS:
        conn.close()
        raise HTTPException(status_code=400, detail="验证码错误次数过多，请重新获取验证码")
    if row["code"] != code:
        conn.execute("UPDATE email_verify_codes SET attempts=attempts+1 WHERE id=?", (row["id"],))
        conn.commit()
        remaining = MAX_VERIFY_ATTEMPTS - row["attempts"] - 1
        conn.close()
        raise HTTPException(status_code=400, detail=f"验证码错误，还剩 {remaining} 次尝试机会")

    # 验证成功 — 创建用户
    pw_hash = hash_password(password)
    conn.execute(
        "INSERT INTO email_users (email, password_hash, created_at) VALUES (?,?,?)",
        (email, pw_hash, now)
    )
    conn.commit()
    user_id = conn.execute("SELECT id FROM email_users WHERE email=?", (email,)).fetchone()["id"]
    # 清除已用的验证码
    conn.execute("DELETE FROM email_verify_codes WHERE email=?", (email,))
    conn.commit()
    conn.close()

    token = create_jwt(user_id, email)
    return {
        "success": True,
        "message": "注册成功！",
        "data": {
            "access_token": token,
            "token_type": "bearer",
            "user": {"id": user_id, "email": email},
        },
    }


@app.post("/api/email/login")
async def email_login(req: EmailLoginRequest):
    """邮箱 + 密码登录，返回 JWT。"""
    email = _validate_email(req.email)
    password = req.password

    conn = _get_db()
    user = conn.execute("SELECT id, email, password_hash, is_active FROM email_users WHERE email=?", (email,)).fetchone()
    if not user:
        conn.close()
        raise HTTPException(status_code=401, detail="邮箱或密码错误")
    if not user["is_active"]:
        conn.close()
        raise HTTPException(status_code=403, detail="账户已被禁用")
    if not verify_password(password, user["password_hash"]):
        conn.close()
        raise HTTPException(status_code=401, detail="邮箱或密码错误")

    # 更新最后登录时间
    now = _dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn.execute("UPDATE email_users SET last_login_at=? WHERE id=?", (now, user["id"]))
    conn.commit()
    conn.close()

    token = create_jwt(user["id"], user["email"])
    return {
        "success": True,
        "message": "登录成功",
        "data": {
            "access_token": token,
            "token_type": "bearer",
            "user": {"id": user["id"], "email": user["email"]},
        },
    }


@app.post("/api/email/reset-password")
async def email_reset_password(req: EmailResetPasswordRequest):
    """验证码校验后重置密码。"""
    email = _validate_email(req.email)
    code = req.code.strip()
    new_password = _validate_password(req.new_password)
    now = _dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if len(code) != 6 or not code.isdigit():
        raise HTTPException(status_code=400, detail="验证码为 6 位数字")

    conn = _get_db()
    user = conn.execute("SELECT id FROM email_users WHERE email=?", (email,)).fetchone()
    if not user:
        conn.close()
        raise HTTPException(status_code=404, detail="该邮箱未注册")

    row = conn.execute(
        "SELECT id, code, expires_at, attempts FROM email_verify_codes WHERE email=? ORDER BY id DESC LIMIT 1",
        (email,)
    ).fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=400, detail="请先获取验证码")
    if row["expires_at"] < now:
        conn.close()
        raise HTTPException(status_code=400, detail="验证码已过期，请重新获取")
    if row["attempts"] >= MAX_VERIFY_ATTEMPTS:
        conn.close()
        raise HTTPException(status_code=400, detail="验证码错误次数过多，请重新获取验证码")
    if row["code"] != code:
        conn.execute("UPDATE email_verify_codes SET attempts=attempts+1 WHERE id=?", (row["id"],))
        conn.commit()
        remaining = MAX_VERIFY_ATTEMPTS - row["attempts"] - 1
        conn.close()
        raise HTTPException(status_code=400, detail=f"验证码错误，还剩 {remaining} 次尝试机会")

    pw_hash = hash_password(new_password)
    conn.execute("UPDATE email_users SET password_hash=? WHERE id=?", (pw_hash, user["id"]))
    conn.execute("DELETE FROM email_verify_codes WHERE email=?", (email,))
    conn.commit()
    conn.close()

    return {"success": True, "message": "密码重置成功，请使用新密码登录"}


@app.get("/api/email/me")
async def email_me(user: dict = Depends(get_current_user)):
    """获取当前登录用户信息（需携带 Authorization: Bearer <token>）。"""
    conn = _get_db()
    row = conn.execute("SELECT id, email, created_at, last_login_at FROM email_users WHERE id=?", (user["user_id"],)).fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="用户不存在")
    return {"success": True, "data": dict(row)}


class PhoneWxLoginRequest(BaseModel):
    wx_code: str    # wx.login() 返回的 code，用于换 openid
    phone_code: str  # getPhoneNumber 返回的 code，用于换手机号

@app.post("/api/phone-wx-login")
async def phone_wx_login(req: PhoneWxLoginRequest):
    """手机号快速登录：同时获取 openid 和手机号，合并为一个用户。"""
    if not WECHAT_APPID or not WECHAT_SECRET:
        token = "mock_token_" + secrets.token_hex(8)
        return {"token": token, "openid": "mock_openid", "phone": "138****0000", "is_mock": True}

    if not _HTTPX_OK:
        raise HTTPException(status_code=500, detail="请安装 httpx: pip install httpx")

    async with httpx.AsyncClient(timeout=10) as client:
        # 1. wx.login code → openid
        session_resp = await client.get(
            "https://api.weixin.qq.com/sns/jscode2session",
            params={
                "appid": WECHAT_APPID, "secret": WECHAT_SECRET,
                "js_code": req.wx_code, "grant_type": "authorization_code",
            }
        )
        session_data = session_resp.json()
        if "errcode" in session_data and session_data["errcode"] != 0:
            raise HTTPException(status_code=400, detail=f"微信登录错误: {session_data.get('errmsg')}")
        openid = session_data["openid"]

        # 2. 获取 access_token（用于换手机号）
        at_resp = await client.get(
            "https://api.weixin.qq.com/cgi-bin/token",
            params={"grant_type": "client_credential", "appid": WECHAT_APPID, "secret": WECHAT_SECRET}
        )
        at_data = at_resp.json()
        if "errcode" in at_data and at_data["errcode"] != 0:
            raise HTTPException(status_code=500, detail=f"获取access_token失败: {at_data.get('errmsg')}")
        access_token = at_data["access_token"]

        # 3. phone_code → 手机号
        phone_resp = await client.post(
            "https://api.weixin.qq.com/wxa/business/getuserphonenumber",
            params={"access_token": access_token},
            json={"code": req.phone_code},
        )
        phone_data = phone_resp.json()
        if phone_data.get("errcode", 0) != 0:
            raise HTTPException(status_code=400, detail=f"获取手机号失败: {phone_data.get('errmsg')}")
        phone_number = phone_data["phone_info"]["phoneNumber"]

    # 4. 写入/更新用户（openid + 手机号）
    conn = _get_db()
    conn.execute("INSERT OR IGNORE INTO users (openid) VALUES (?)", (openid,))
    conn.execute("UPDATE users SET phone=? WHERE openid=?", (phone_number, openid))
    conn.commit()
    conn.close()

    # 5. 创建 session
    token = secrets.token_hex(32)
    expires_at = (_dt.datetime.now() + _dt.timedelta(days=30)).strftime('%Y-%m-%d %H:%M:%S')
    conn = _get_db()
    conn.execute("INSERT INTO sessions (token, openid, expires_at) VALUES (?,?,?)", (token, openid, expires_at))
    conn.commit()
    conn.close()

    return {"token": token, "openid": openid, "phone": phone_number}


class CheckTokenRequest(BaseModel):
    token: str

@app.post("/api/check-token")
async def check_token(req: CheckTokenRequest):
    """验证 token 是否有效，App 启动时调用。"""
    openid = _token_to_openid(req.token)
    if not openid:
        return {"valid": False}
    conn = _get_db()
    row = conn.execute("SELECT phone FROM users WHERE openid=?", (openid,)).fetchone()
    conn.close()
    phone = row["phone"] if row else ""
    return {"valid": True, "openid": openid, "phone": phone or ""}


class SaveRecordRequest(BaseModel):
    token: str = ''
    score: int = 0
    skin_age: Optional[float] = None
    glogau_level: str = ''
    glogau_desc: str = ''
    report: str = ''
    result_json: str = ''
    date: str = ''
    front_img: str = ''
    left_img: str = ''
    right_img: str = ''

@app.post("/api/records")
async def save_record(req: SaveRecordRequest, user: dict | None = Depends(get_optional_user)):
    # 优先用 JWT 用户身份，其次用微信 token
    user_id = None
    openid = ""
    id_label = ""

    if user:
        user_id = user["user_id"]
        id_label = str(user_id)
    elif req.token:
        openid = _token_to_openid(req.token)
        if not openid:
            raise HTTPException(status_code=401, detail="token无效，请重新登录")
        id_label = openid
    else:
        raise HTTPException(status_code=401, detail="请先登录")

    # 查手机号（仅微信用户有），用于重命名照片
    if user_id:
        conn = _get_db()
        row = conn.execute("SELECT email FROM email_users WHERE id=?", (user_id,)).fetchone()
        conn.close()
        label = (row["email"] if row else str(user_id)).split("@")[0].replace("+", "")[:20]
    else:
        conn = _get_db()
        row = conn.execute("SELECT phone FROM users WHERE openid=?", (openid,)).fetchone()
        conn.close()
        label = ((row["phone"] if row and row["phone"] else openid[-8:]) or openid[-8:]).replace("+", "")

    ts = _dt.datetime.now().strftime("%Y%m%d_%H%M%S")

    def _rename(old_name: str, suffix: str) -> str:
        if not old_name:
            return ""
        old_path = os.path.join(UPLOADS_DIR, old_name)
        new_name = f"{ts}_{label}_{suffix}.jpg"
        new_path = os.path.join(UPLOADS_DIR, new_name)
        if os.path.exists(old_path):
            os.rename(old_path, new_name)
        return new_name

    front = _rename(req.front_img, "front")
    left  = _rename(req.left_img,  "left")
    right = _rename(req.right_img, "right")

    conn = _get_db()
    conn.execute(
        "INSERT INTO records (openid,user_id,score,skin_age,glogau_level,glogau_desc,report,result_json,date,front_img,left_img,right_img) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
        (openid, user_id, req.score, req.skin_age, req.glogau_level, req.glogau_desc, req.report, req.result_json, req.date, front, left, right)
    )
    conn.commit()
    conn.close()
    return {"success": True}

@app.get("/api/records")
async def get_records(token: str = '', user: dict | None = Depends(get_optional_user)):
    if user:
        conn = _get_db()
        rows = conn.execute(
            "SELECT id,score,skin_age,glogau_level,glogau_desc,date,result_json FROM records WHERE user_id=? ORDER BY id DESC LIMIT 50",
            (user["user_id"],)
        ).fetchall()
        conn.close()
        return {"records": [dict(r) for r in rows]}
    if token:
        openid = _token_to_openid(token)
        if not openid:
            return {"records": []}
        conn = _get_db()
        rows = conn.execute(
            "SELECT id,score,skin_age,glogau_level,glogau_desc,date,result_json FROM records WHERE openid=? ORDER BY id DESC LIMIT 50",
            (openid,)
        ).fetchall()
        conn.close()
        return {"records": [dict(r) for r in rows]}
    return {"records": []}


# 挂载静态文件（前端页面放同目录下即可）
_STATIC_DIR = os.path.dirname(__file__)
_PUBLIC_STATIC_DIR = os.path.abspath(os.path.join(_STATIC_DIR, "..", "static"))
_SKIN_DIAGNOSIS_DIR = os.path.join(_PUBLIC_STATIC_DIR, "skin-diagnosis")
_MEDIAPIPE_DIR = os.path.join(_PUBLIC_STATIC_DIR, "mediapipe")
if os.path.exists(_SKIN_DIAGNOSIS_DIR):
    app.mount("/skin-diagnosis", StaticFiles(directory=_SKIN_DIAGNOSIS_DIR, html=True), name="skin-diagnosis")
if os.path.exists(_MEDIAPIPE_DIR):
    app.mount("/mediapipe", StaticFiles(directory=_MEDIAPIPE_DIR), name="mediapipe")
if os.path.exists(_PUBLIC_STATIC_DIR):
    app.mount("/lanjiao-static", StaticFiles(directory=_PUBLIC_STATIC_DIR), name="lanjiao-static")
if os.path.exists(os.path.join(_STATIC_DIR, "index.html")):
    app.mount("/", StaticFiles(directory=_STATIC_DIR, html=True), name="static")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001, reload=False)
