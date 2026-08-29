"""AI 多模型辩论服务 — 编排多轮讨论

流程（3 轮）:
  第 1 轮 — 所有模型独立回答（并行），支持多模态附件
  第 2 轮 — 每个模型看到其他模型的回答后交叉点评（并行）
  第 3 轮 — 主模型综合所有讨论给出最终答案
"""

import asyncio
import json
from typing import AsyncGenerator

from loguru import logger

from app.adapters.registry import registry


async def run_discuss(
    question: str,
    models: list[str],
    rounds: int = 3,
    images: list[str] | None = None,
    videos: list[str] | None = None,
    thinking: bool = False,
    enable_search: bool = False,
    memory_context: str | None = None,
) -> AsyncGenerator[str, None]:
    """运行多模型讨论，yield SSE 事件字符串

    Args:
        question: 用户问题
        models: 参与讨论的模型 ID 列表
        rounds: 讨论轮数（2-3）
        images: base64 图片 data URLs
        videos: 视频 URLs
        thinking: 是否启用深度思考
        enable_search: 是否启用联网搜索
        memory_context: 记忆上下文（注入到讨论中）
    """
    # 获取所有适配器
    adapters = {}
    for mid in models:
        try:
            adapter = registry.get(mid)
            if not adapter.model_info.available:
                yield _sse("error", {"model": mid, "message": f"模型 '{mid}' 不可用"})
                return
            adapters[mid] = adapter
        except ValueError as e:
            yield _sse("error", {"model": mid, "message": str(e)})
            return

    model_names = {mid: a.model_info.display_name for mid, a in adapters.items()}
    primary_model = models[0]  # 主模型用于最终总结

    images = images or []
    videos = videos or []

    # 构建额外参数
    extra_params = {}
    if thinking:
        extra_params["thinking"] = True
    if enable_search:
        extra_params["enable_search"] = True

    yield _sse("start", {
        "question": question,
        "models": models,
        "model_names": model_names,
        "rounds": rounds,
        "has_images": bool(images),
        "has_videos": bool(videos),
        "image_count": len(images),
        "video_count": len(videos),
        "thinking": thinking,
        "enable_search": enable_search,
    })

    all_discussion: list[dict] = []  # 收集所有轮的讨论

    # 在问题中注入记忆上下文
    effective_question = question
    if memory_context:
        effective_question = (
            f"[以下是之前讨论的要点，供你参考上下文]\n{memory_context}\n\n"
            f"[当前问题]\n{question}"
        )

    # ================================================================
    # 第 1 轮 — 独立回答（支持多模态附件）
    # ================================================================
    yield _sse("round_start", {"round": 1, "label": "独立回答"})
    round1 = await _round_parallel(
        adapters, models, effective_question,
        prompt_template="请回答以下问题，给出你的分析和观点：\n\n{question}",
        images=images,
        videos=videos,
        include_media=True,
        round_num=1,
        extra_params=extra_params,
        yield_event=lambda mid, content, reasoning=None: _sse("round_result", {
            "round": 1, "model": mid, "model_name": model_names[mid],
            "content": content, "reasoning_content": reasoning,
        }),
    )
    all_discussion.append({"round": 1, "label": "独立回答", "responses": {mid: c for mid, c, _ in round1}})

    # ================================================================
    # 第 2 轮 — 交叉点评
    # ================================================================
    yield _sse("round_start", {"round": 2, "label": "交叉点评"})

    # 为每个模型构建上下文：展示其他模型的第 1 轮回答
    other_answers = "\n\n".join([
        f"【{model_names[mid]}】的答案：\n{content}"
        for mid, content, _ in round1
    ])

    round2 = await _round_parallel(
        adapters, models, question,
        prompt_template=(
            "原始问题是：{question}\n\n"
            "以下是其他模型对同一问题的回答：\n"
            + other_answers + "\n\n"
            "请你作为批判性思考者，对以上各模型的回答进行点评：\n"
            "1. 指出各模型回答中的优点和不足\n"
            "2. 补充被遗漏的重要观点\n"
            "3. 如果有不同意见，请提出并论证\n"
            "请具体、有理有据地分析。"
        ),
        images=images,
        videos=videos,
        include_media=False,  # 第 2 轮不再重复附件，已在讨论上下文中
        round_num=2,
        extra_params=extra_params,
        yield_event=lambda mid, content, reasoning=None: _sse("round_result", {
            "round": 2, "model": mid, "model_name": model_names[mid],
            "content": content, "reasoning_content": reasoning,
        }),
    )
    all_discussion.append({"round": 2, "label": "交叉点评", "responses": {mid: c for mid, c, _ in round2}})

    # ================================================================
    # 第 3 轮 — 最终总结
    # ================================================================
    yield _sse("round_start", {"round": 3, "label": "最终总结"})

    # 构建完整讨论历史
    discussion_text = _format_discussion(question, all_discussion, model_names)
    final_prompt = (
        f"{discussion_text}\n\n"
        f"请你作为主裁判，综合以上所有模型的讨论，给出一个全面、平衡、有深度的最终答案。"
        f"要求：\n"
        f"1. 涵盖各模型的核心观点\n"
        f"2. 明确指出争议点和共识\n"
        f"3. 给出你的最终结论和建议\n"
        f"4. 引用具体模型的贡献（如需要）"
    )

    try:
        adapter = adapters[primary_model]
        response = await adapter.chat(
            messages=[{"role": "user", "content": final_prompt}],
            max_tokens=4096,
            **extra_params,
        )
        final_text = response.get("choices", [{}])[0].get("message", {}).get("content", "")
        final_reasoning = response.get("choices", [{}])[0].get("message", {}).get("reasoning_content", "")
        yield _sse("final", {
            "model": primary_model,
            "model_name": model_names[primary_model],
            "content": final_text,
            "reasoning_content": final_reasoning or None,
        })
    except Exception as e:
        yield _sse("error", {"model": primary_model, "message": f"最终总结失败: {e}"})
        return

    yield _sse("done", {})


# ---- 内部函数 ----

def _build_multimodal_content(
    adapter,
    text_prompt: str,
    images: list[str],
    videos: list[str],
    include_media: bool,
) -> str | list[dict]:
    """根据模型能力构建消息 content（纯文本字符串 或 多模态 content 数组）

    对于支持 vision 的模型 + include_media=True 时，构建多模态数组；
    否则返回纯文本（附带附件说明）。
    """
    caps = adapter.model_info.capabilities
    has_vision = "vision" in caps if caps else False

    if include_media and has_vision and (images or videos):
        content: list[dict] = [{"type": "text", "text": text_prompt}]
        for img in images:
            content.append({"type": "image_url", "image_url": {"url": img}})
        for vid in videos:
            # 构建完整视频 URL
            video_url = vid if vid.startswith("http") else vid
            content.append({"type": "video_url", "video_url": {"url": video_url}})
        return content
    else:
        # 纯文本 — 对不支持视觉的模型附加说明
        result = text_prompt
        if images and include_media:
            result += f"\n\n[注：用户附带了 {len(images)} 张图片，但当前模型不支持直接查看图片内容。请基于问题中的文字描述进行分析讨论。]"
        if videos and include_media:
            result += f"\n\n[注：用户附带了 {len(videos)} 个视频（{', '.join(videos)}），但当前模型不支持直接查看视频内容。]"
        return result


async def _round_parallel(
    adapters: dict,
    models: list[str],
    question: str,
    prompt_template: str,
    images: list[str],
    videos: list[str],
    include_media: bool,
    round_num: int,
    extra_params: dict,
    yield_event,
) -> list[tuple[str, str, str | None]]:
    """并行执行一轮讨论，返回 [(model_id, response_content, reasoning_content)]"""
    results: list[tuple[str, str, str | None]] = []

    async def ask_one(mid: str) -> tuple[str, str | None, str | None]:
        try:
            prompt = prompt_template.format(question=question)
            content = _build_multimodal_content(
                adapters[mid], prompt, images, videos, include_media,
            )
            logger.info(f"[discuss] R{round_num} {mid} 开始 (thinking={extra_params.get('thinking')})...")
            response = await adapters[mid].chat(
                messages=[{"role": "user", "content": content}],
                max_tokens=2048,
                **extra_params,
            )
            text = response.get("choices", [{}])[0].get("message", {}).get("content", "")
            reasoning = response.get("choices", [{}])[0].get("message", {}).get("reasoning_content", "")
            logger.info(f"[discuss] R{round_num} {mid} 完成 ({len(text)} 字, reasoning={len(reasoning or '')} 字)")
            yield_event(mid, text, reasoning or None)
            return (mid, text, reasoning or None)
        except Exception as e:
            logger.error(f"[discuss] R{round_num} {mid} 失败: {e}")
            yield_event(mid, f"❌ 调用失败: {e}", None)
            return (mid, None, None)

    tasks = [ask_one(mid) for mid in models]
    gathered = await asyncio.gather(*tasks)

    for mid, content, reasoning in gathered:
        if content is not None:
            results.append((mid, content, reasoning))

    return results


def _format_discussion(question: str, discussion: list[dict], model_names: dict) -> str:
    """格式化讨论历史为文本"""
    lines = [f"## 原始问题\n{question}\n"]
    for round_data in discussion:
        lines.append(f"## 第 {round_data['round']} 轮：{round_data['label']}")
        for mid, content in round_data["responses"].items():
            lines.append(f"### {model_names.get(mid, mid)}")
            lines.append(content)
            lines.append("")
    return "\n".join(lines)


def _sse(event_type: str, data: dict) -> str:
    """构建 SSE 事件字符串"""
    payload = {"type": event_type, **data}
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
