"""媒体处理服务 — FFmpeg 视频 + Pillow 图片

所有操作均返回临时文件路径，调用方负责清理。
"""

import os
import subprocess
import tempfile
import time
from pathlib import Path

from loguru import logger

# ---- 工具函数 ----

TEMP_DIR = Path("/tmp/feishu_media")
TEMP_DIR.mkdir(parents=True, exist_ok=True)


def _temp_path(prefix: str, ext: str) -> str:
    """生成临时文件路径"""
    ts = int(time.time() * 1000)
    return str(TEMP_DIR / f"{prefix}_{ts}{ext}")


def _run_ffmpeg(args: list[str], timeout: int = 120) -> tuple[int, str, str]:
    """运行 ffmpeg，返回 (returncode, stdout, stderr)"""
    cmd = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error"] + args
    logger.debug(f"ffmpeg: {' '.join(cmd)}")
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return proc.returncode, proc.stdout.strip(), proc.stderr.strip()
    except subprocess.TimeoutExpired:
        return -1, "", "timeout"


def _get_duration(input_path: str) -> float:
    """获取视频时长（秒）"""
    try:
        proc = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", input_path],
            capture_output=True, text=True, timeout=10,
        )
        return float(proc.stdout.strip())
    except Exception:
        return 0.0


def _parse_time(time_str: str) -> float:
    """解析时间字符串 → 秒数
    支持: "90", "1:30", "1:30.5", "00:01:30", "00:01:30.500"
    """
    time_str = time_str.strip()
    parts = time_str.split(":")
    if len(parts) == 1:
        return float(parts[0])
    elif len(parts) == 2:
        return int(parts[0]) * 60 + float(parts[1])
    elif len(parts) == 3:
        return int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[2])
    return 0.0


# ============================================================
#  视频处理
# ============================================================

async def video_clip(input_path: str, start: str, end: str) -> str | None:
    """裁剪视频片段

    Args:
        input_path: 输入视频路径
        start: 开始时间 (秒/"1:30"/"00:05:00")
        end: 结束时间

    Returns:
        输出文件路径，失败返回 None
    """
    start_sec = _parse_time(start)
    end_sec = _parse_time(end)
    if end_sec <= start_sec:
        return None

    duration = end_sec - start_sec
    output = _temp_path("clip", ".mp4")

    code, _, stderr = _run_ffmpeg([
        "-ss", str(start_sec),
        "-i", input_path,
        "-t", str(duration),
        "-c", "copy",
        "-avoid_negative_ts", "make_zero",
        output,
    ])

    if code != 0:
        logger.error(f"视频裁剪失败: {stderr}")
        # 回退：重新编码（-c copy 可能对非关键帧失败）
        logger.info("回退到重新编码模式...")
        code2, _, stderr2 = _run_ffmpeg([
            "-ss", str(start_sec),
            "-i", input_path,
            "-t", str(duration),
            "-c:v", "libx264", "-preset", "fast", "-crf", "23",
            "-c:a", "aac",
            output,
        ], timeout=300)
        if code2 != 0:
            logger.error(f"视频裁剪编码失败: {stderr2}")
            return None

    logger.info(f"视频裁剪完成: {output}")
    return output


async def video_compress(
    input_path: str,
    crf: int = 28,
    preset: str = "fast",
    resolution: str = "",
) -> str | None:
    """压缩视频（降码率/分辨率）

    Args:
        input_path: 输入视频路径
        crf: 质量 (18=接近无损, 23=默认, 28=较小, 35=很糊)
        preset: 编码速度 (ultrafast/fast/medium/slow)
        resolution: 最大分辨率 (如 "1280:720" 缩到 720p)

    Returns:
        输出文件路径
    """
    output = _temp_path("compress", ".mp4")
    args = ["-i", input_path]

    if resolution:
        # scale 滤镜：保持宽高比，长边不超过指定值
        w, h = resolution.split(":") if ":" in resolution else (resolution, "-2")
        args += ["-vf", f"scale={w}:{h}:force_original_aspect_ratio=decrease"]

    args += [
        "-c:v", "libx264", "-preset", preset, "-crf", str(crf),
        "-c:a", "aac", "-b:a", "96k",
        "-movflags", "+faststart",
        output,
    ]

    code, _, stderr = _run_ffmpeg(args, timeout=600)
    if code != 0:
        logger.error(f"视频压缩失败: {stderr}")
        return None

    # 日志输出压缩前后大小
    orig_size = os.path.getsize(input_path) / 1024**2
    new_size = os.path.getsize(output) / 1024**2
    logger.info(f"视频压缩: {orig_size:.1f}MB → {new_size:.1f}MB (节省 {100*(1-new_size/orig_size):.0f}%)")

    return output


async def video_watermark(
    input_path: str,
    text: str,
    position: str = "bottom-right",
    font_size: int = 0,
) -> str | None:
    """给视频添加文字水印（纯文字阴影，无背景色块）

    Args:
        input_path: 输入视频路径
        text: 水印文字
        position: 位置 top-left/top-right/bottom-left/bottom-right/top/bottom/center
        font_size: 字号 (0=自适应，按视频高度 5% 计算，最小 22)

    Returns:
        输出文件路径
    """
    output = _temp_path("watermark", ".mp4")

    # 自动计算字号：视频高度的 5%，最小 22
    if font_size <= 0:
        info = await get_video_info(input_path)
        height = info.get("height", 720) or 720
        font_size = max(int(height * 0.05), 22)

    # 位置映射 → FFmpeg drawtext 坐标（边距按字号缩放）
    margin = max(font_size, 12)
    positions = {
        "top-left": f"x={margin}:y={margin}",
        "top-right": f"x=w-tw-{margin}:y={margin}",
        "bottom-left": f"x={margin}:y=h-th-{margin}",
        "bottom-right": f"x=w-tw-{margin}:y=h-th-{margin}",
        "top": f"x=(w-tw)/2:y={margin}",
        "bottom": f"x=(w-tw)/2:y=h-th-{margin}",
        "center": "x=(w-tw)/2:y=(h-th)/2",
    }
    pos = positions.get(position, positions["bottom-right"])

    # 转义特殊字符（FFmpeg drawtext 的冒号和引号）
    safe_text = text.replace(":", "\\:").replace("'", "\\'")

    # 阴影偏移（字号 2.5%），纯白文字半透明
    shadow = max(font_size // 40 + 1, 1)

    drawtext = (
        f"drawtext=text='{safe_text}':{pos}:"
        f"fontsize={font_size}:fontcolor=white@0.85:"
        f"shadowx={shadow}:shadowy={shadow}:shadowcolor=black@0.5"
    )

    code, _, stderr = _run_ffmpeg([
        "-i", input_path,
        "-vf", drawtext,
        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
        "-c:a", "copy",
        output,
    ], timeout=300)

    if code != 0:
        logger.error(f"添加水印失败: {stderr}")
        return None

    logger.info(f"视频水印添加完成: {output} (字号={font_size}, 位置={position})")
    return output


async def video_extract_audio(input_path: str, format: str = "mp3") -> str | None:
    """从视频提取音频

    Args:
        input_path: 输入视频路径
        format: 输出格式 (mp3/aac/wav/m4a)

    Returns:
        音频文件路径
    """
    ext = f".{format}"
    output = _temp_path("audio", ext)

    codec_map = {"mp3": "libmp3lame", "aac": "aac", "wav": "pcm_s16le", "m4a": "aac"}
    codec = codec_map.get(format, "libmp3lame")

    code, _, stderr = _run_ffmpeg([
        "-i", input_path,
        "-vn",
        "-c:a", codec,
        "-b:a", "192k" if format != "wav" else "",
        output,
    ])

    if code != 0:
        logger.error(f"提取音频失败: {stderr}")
        return None

    logger.info(f"音频提取完成: {output}")
    return output


async def video_convert(input_path: str, target_format: str) -> str | None:
    """视频格式转换

    Args:
        input_path: 输入视频路径
        target_format: 目标格式 (mp4/mkv/mov/gif/webm/avi)

    Returns:
        输出文件路径
    """
    fmt = target_format.lower().lstrip(".")
    ext = f".{fmt}"
    output = _temp_path("convert", ext)

    if fmt == "gif":
        # 视频转 GIF：截取前 15 秒，降低帧率和分辨率
        code, _, stderr = _run_ffmpeg([
            "-i", input_path,
            "-t", "15",
            "-vf", "fps=10,scale=480:-1:flags=lanczos,split[s0][s1];[s0]palettegen[p];[s1][p]paletteuse",
            "-loop", "0",
            output,
        ], timeout=120)
    else:
        code, _, stderr = _run_ffmpeg([
            "-i", input_path,
            "-c:v", "libx264", "-preset", "fast", "-crf", "23",
            "-c:a", "aac",
            output,
        ], timeout=300)

    if code != 0:
        logger.error(f"格式转换失败: {stderr}")
        return None

    logger.info(f"格式转换完成: {input_path} → {output}")
    return output


async def video_concat(input_paths: list[str]) -> str | None:
    """拼接多个视频

    Args:
        input_paths: 按顺序排列的输入视频路径列表

    Returns:
        拼接后的视频路径
    """
    if len(input_paths) < 2:
        return None

    output = _temp_path("concat", ".mp4")

    # 使用 concat filter（更可靠，支持不同编码的视频）
    filter_parts = []
    for i in range(len(input_paths)):
        filter_parts.append(f"[{i}:v:0][{i}:a:0]")

    # 构建输入参数
    args = []
    for path in input_paths:
        args += ["-i", path]

    # concat filter
    concat_inputs = "".join(f"[{i}:v:0][{i}:a:0]" for i in range(len(input_paths)))
    filter_complex = f"{concat_inputs}concat=n={len(input_paths)}:v=1:a=1[outv][outa]"

    args += [
        "-filter_complex", filter_complex,
        "-map", "[outv]", "-map", "[outa]",
        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
        "-c:a", "aac",
        output,
    ]

    code, _, stderr = _run_ffmpeg(args, timeout=600)
    if code != 0:
        logger.error(f"视频拼接失败: {stderr}")
        return None

    logger.info(f"视频拼接完成: {len(input_paths)} 个片段 → {output}")
    return output


async def get_video_info(input_path: str) -> dict:
    """获取视频信息"""
    try:
        proc = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries",
             "format=duration,size,bit_rate:stream=codec_type,codec_name,width,height,r_frame_rate",
             "-of", "json", input_path],
            capture_output=True, text=True, timeout=15,
        )
        import json
        info = json.loads(proc.stdout)
        fmt = info.get("format", {})
        streams = info.get("streams", [])

        result = {
            "duration": float(fmt.get("duration", 0)),
            "size_mb": int(fmt.get("size", 0)) / 1024**2,
            "bitrate_kbps": int(int(fmt.get("bit_rate", 0)) / 1000),
        }
        for s in streams:
            if s["codec_type"] == "video":
                result["video_codec"] = s.get("codec_name", "")
                result["width"] = s.get("width", 0)
                result["height"] = s.get("height", 0)
                fps_str = s.get("r_frame_rate", "0/1")
                if "/" in fps_str:
                    num, den = fps_str.split("/")
                    result["fps"] = round(int(num) / int(den), 1) if int(den) else 0
        return result
    except Exception as e:
        logger.error(f"获取视频信息失败: {e}")
        return {}


# ============================================================
#  图片处理
# ============================================================

from PIL import Image, ImageDraw, ImageFont


def _load_font(size: int) -> ImageFont.FreeTypeFont:
    """加载中文字体"""
    font_paths = [
        "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
        "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    for fp in font_paths:
        if os.path.exists(fp):
            return ImageFont.truetype(fp, size)
    return ImageFont.load_default()


def image_resize(input_path: str, width: int, height: int = 0, quality: int = 85) -> str | None:
    """图片缩放/裁剪

    Args:
        input_path: 输入图片路径
        width: 目标宽度（height=0 则等比缩放）
        height: 目标高度（0=自动）
        quality: JPEG 质量

    Returns:
        输出文件路径
    """
    try:
        img = Image.open(input_path)
        orig_w, orig_h = img.size

        if height == 0:
            # 等比缩放
            ratio = width / orig_w
            new_size = (width, int(orig_h * ratio))
        elif width == 0:
            ratio = height / orig_h
            new_size = (int(orig_w * ratio), height)
        else:
            new_size = (width, height)

        img = img.resize(new_size, Image.LANCZOS)

        # 保持原格式
        ext = os.path.splitext(input_path)[1].lower()
        if ext not in (".jpg", ".jpeg", ".png", ".webp", ".gif"):
            ext = ".jpg"

        output = _temp_path("resize", ext)
        save_kwargs = {"quality": quality, "optimize": True} if ext in (".jpg", ".jpeg") else {}
        if ext == ".png":
            save_kwargs = {"optimize": True}

        # RGBA → RGB for JPEG
        if ext in (".jpg", ".jpeg") and img.mode in ("RGBA", "P"):
            img = img.convert("RGB")

        img.save(output, **save_kwargs)
        logger.info(f"图片缩放: {orig_w}x{orig_h} → {new_size[0]}x{new_size[1]}")
        return output
    except Exception as e:
        logger.error(f"图片缩放失败: {e}")
        return None


def image_watermark(input_path: str, text: str, position: str = "bottom-right", font_size: int = 0) -> str | None:
    """给图片添加文字水印（纯文字，无背景色块）

    Args:
        input_path: 输入图片路径
        text: 水印文字
        position: 位置 top-left/top-right/bottom-left/bottom-right/top/bottom/center
        font_size: 字号 (0=自适应，按图片短边 5% 计算，最小 18)

    Returns:
        输出文件路径
    """
    try:
        img = Image.open(input_path).convert("RGBA")
        w, h = img.size

        # 水印图层
        overlay = Image.new("RGBA", img.size, (255, 255, 255, 0))
        draw = ImageDraw.Draw(overlay)

        if font_size <= 0:
            font_size = max(int(min(w, h) * 0.05), 18)
        font = _load_font(font_size)

        # 测量文字实际占用区域（textbbox 返回含偏移的精确边界）
        bbox = draw.textbbox((0, 0), text, font=font)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]

        # 边距按字体大小缩放
        margin = max(font_size // 2, 10)

        positions = {
            "top-left": (margin - bbox[0], margin - bbox[1]),
            "top-right": (w - tw - margin - bbox[0], margin - bbox[1]),
            "bottom-left": (margin - bbox[0], h - th - margin - bbox[1]),
            "bottom-right": (w - tw - margin - bbox[0], h - th - margin - bbox[1]),
            "top": ((w - tw) // 2 - bbox[0], margin - bbox[1]),
            "bottom": ((w - tw) // 2 - bbox[0], h - th - margin - bbox[1]),
            "center": ((w - tw) // 2 - bbox[0], (h - th) // 2 - bbox[1]),
        }
        x, y = positions.get(position, positions["bottom-right"])

        # 阴影（深色偏移 1px）增强可读性
        shadow_color = (0, 0, 0, 120)
        text_color = (255, 255, 255, 220)
        offset = max(font_size // 24, 1)
        draw.text((x + offset, y + offset), text, font=font, fill=shadow_color)
        draw.text((x, y), text, font=font, fill=text_color)

        result = Image.alpha_composite(img, overlay)

        ext = os.path.splitext(input_path)[1].lower()
        if ext not in (".png", ".webp"):
            ext = ".png"
        output = _temp_path("img_watermark", ext)
        result = result.convert("RGB") if ext == ".jpg" else result
        result.save(output, optimize=True)
        logger.info(f"图片水印添加完成: {output} (字号={font_size}, 位置={position})")
        return output
    except Exception as e:
        logger.error(f"图片加水印失败: {e}")
        return None


def image_compress(input_path: str, quality: int = 75, max_width: int = 1920) -> str | None:
    """图片压缩

    Args:
        input_path: 输入图片路径
        quality: JPEG 质量 (1-100, 越小越压缩)
        max_width: 最大宽度，超过等比缩小

    Returns:
        输出文件路径
    """
    try:
        img = Image.open(input_path)
        orig_w, orig_h = img.size
        orig_size = os.path.getsize(input_path) / 1024

        # 缩小大图
        if orig_w > max_width:
            ratio = max_width / orig_w
            img = img.resize((max_width, int(orig_h * ratio)), Image.LANCZOS)

        ext = os.path.splitext(input_path)[1].lower()
        if ext not in (".jpg", ".jpeg", ".png", ".webp"):
            ext = ".jpg"

        output = _temp_path("img_compress", ext)

        if img.mode in ("RGBA", "P") and ext in (".jpg", ".jpeg"):
            img = img.convert("RGB")

        img.save(output, quality=quality, optimize=True)
        new_size = os.path.getsize(output) / 1024
        ratio = 100 * (1 - new_size / orig_size)
        logger.info(f"图片压缩: {orig_size:.0f}KB → {new_size:.0f}KB (节省 {ratio:.0f}%)")
        return output
    except Exception as e:
        logger.error(f"图片压缩失败: {e}")
        return None
