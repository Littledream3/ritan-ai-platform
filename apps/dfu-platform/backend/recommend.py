# -*- coding: utf-8 -*-
"""
DFU 分级 → 建议 规则引擎
根据预测级别生成医学建议和患者生活建议。
参考 PLAN.md 中的临床知识库。
"""

# ── 分级建议知识库 ──────────────────────────────
RECOMMENDATIONS = {
    "Normal": {
        "level_desc": "未见明确开放性溃疡特征，但单张图像不能排除神经病变、缺血或其他高危因素",
        "medical": [
            "如存在麻木、疼痛、皮温改变或足部变形，建议进行专业足部检查",
            "按医生建议定期评估周围神经、足背动脉和皮肤完整性",
            "若近期出现破损、红肿、渗液或颜色改变，应及时复诊",
        ],
        "lifestyle": [
            "每日检查双足和趾缝，避免赤脚行走",
            "保持足部清洁干燥，选择合脚鞋袜",
            "持续进行血糖、血压和血脂管理",
        ],
        "urgency": "日常预防",
    },
    "Grade 0": {
        "level_desc": "Wagner 0级 — 当前未见开放性溃疡，但可能存在高危足、胼胝、畸形或既往溃疡风险",
        "medical": [
            "建议完成10克单丝、振动觉和下肢血供评估",
            "评估胼胝、足部畸形、鞋内压力点及既往溃疡史",
            "由专业人员处理胼胝和趾甲问题，避免自行削剪",
        ],
        "lifestyle": [
            "每日检查双足，发现水疱、破损或颜色改变及时就医",
            "使用合适的减压鞋具，避免赤脚和长时间局部受压",
            "保持稳定血糖并按计划复查糖尿病足风险",
        ],
        "urgency": "定期评估",
    },
    "Grade 1": {
        "level_desc": "轻度 — 表浅溃疡，仅累及表皮/真皮，无感染征象",
        "medical": [
            "进行局部清创和消毒处理",
            "使用减压鞋具或减压垫，缓解足底压力",
            "门诊随访，建议 1–2 周复查一次",
            "评估周围神经病变和血管状态",
        ],
        "lifestyle": [
            "每日用温水和温和肥皂清洗双足，仔细擦干（尤其是趾缝间）",
            "每日检查足部有无红肿、破损、水疱等异常",
            "穿合适的糖尿病专用鞋袜，避免赤脚行走",
            "修剪趾甲时应平剪，勿过深以免损伤甲沟",
            "保持血糖稳定（空腹 < 7.0 mmol/L，餐后 < 10.0 mmol/L）",
        ],
        "urgency": "常规",
    },
    "Grade 2": {
        "level_desc": "中度 — 溃疡深及皮下组织，可能伴有轻度感染",
        "medical": [
            "建议进行深度清创处理，清除坏死组织",
            "根据分泌物培养结果，使用敏感抗生素治疗",
            "使用合适的伤口敷料（如水胶体/藻酸盐敷料），定期更换",
            "建议转诊至足病专科或创面修复门诊",
            "评估是否需要影像学检查排除深部感染",
        ],
        "lifestyle": [
            "严格避免患足负重，必要时使用拐杖或轮椅辅助",
            "严格控制血糖，加强自我监测（建议每日测 4 次）",
            "戒烟限酒 — 吸烟会严重损害末梢血液循环",
            "每日检查足部，发现渗液增多、红肿扩大、发热等异常立即就医",
            "饮食中增加优质蛋白（鱼、蛋、豆制品）摄入，促进伤口愈合",
        ],
        "urgency": "尽快就诊",
    },
    "Grade 3": {
        "level_desc": "重度 — 溃疡深达骨骼/肌腱，伴有明显感染（骨髓炎可能）",
        "medical": [
            "紧急进行清创引流手术，清除感染坏死组织",
            "静脉抗生素治疗（根据药敏结果选用）",
            "多学科会诊：骨科 + 感染科 + 血管外科 + 内分泌科",
            "影像学检查（X线/MRI）排除骨髓炎",
            "评估下肢血管供血情况（ABI/血管超声）",
        ],
        "lifestyle": [
            "卧床休息，抬高患肢以减轻水肿",
            "立即就医，不可自行处理伤口或使用偏方",
            "家属协助患者完成日常护理，防止跌倒和二次损伤",
            "注意心理状态 — 重度 DFU 患者常伴有焦虑抑郁情绪，必要时寻求心理疏导",
            "严格控制血糖和血压，为手术创造良好条件",
        ],
        "urgency": "紧急就诊",
    },
    "Grade 4": {
        "level_desc": "Wagner 4级 — 足部局部坏疽，存在严重缺血、感染扩散和截肢风险",
        "medical": [
            "立即急诊住院治疗！",
            "血管外科紧急评估下肢血运重建可能性",
            "全身抗感染治疗 + 支持治疗",
            "评估局部清创或有限截肢的必要性",
            "术后康复 + 假肢适配评估",
        ],
        "lifestyle": [
            "❗ 立即前往最近的有血管外科/骨科急诊的医院，不可延误！",
            "通知家属或紧急联系人，做好住院准备",
            "准备身份证、医保卡、既往病历等住院材料",
            "术后积极配合康复训练和血糖管理",
            "家属应充分了解病情，参与治疗决策",
        ],
        "urgency": "立即急诊",
    },
    "Grade 5": {
        "level_desc": "Wagner 5级 — 全足或广泛坏疽，可能危及肢体和生命",
        "medical": [
            "立即进入具备血管外科、骨科和重症支持能力的医院急诊",
            "紧急评估感染、脓毒症、肢体血供和全身循环状态",
            "由多学科团队评估血运重建、清创和截肢范围",
            "同步进行抗感染、血糖控制和器官功能支持",
        ],
        "lifestyle": [
            "不要自行处理坏死组织或在患足负重",
            "立即通知家属并携带既往病历、用药清单和检查资料就医",
            "若出现发热、意识变化、呼吸急促或血压下降，应立即呼叫急救",
        ],
        "urgency": "紧急抢救",
    },
}


def get_recommendations(prediction_result: dict) -> dict:
    """
    根据模型预测结果，返回结构化的分级建议。

    参数:
        prediction_result: model.predict / predict_from_pil 的返回值

    返回:
        {
            "grade": "Grade 2",
            "confidence": 0.923,
            "is_borderline": False,
            "level_desc": "中度 — 溃疡深及皮下组织...",
            "urgency": "尽快就诊",
            "medical": [...],
            "lifestyle": [...],
            "secondary": { ... } or None,   # 边界情况时给出次选级别的建议
            "disclaimer": "本报告为AI辅助评估...",
        }
    """
    grade = prediction_result["grade"]
    info = RECOMMENDATIONS.get(grade, RECOMMENDATIONS["Normal"])

    result = {
        "grade": grade,
        "confidence": prediction_result["confidence"],
        "is_borderline": prediction_result["is_borderline"],
        "level_desc": info["level_desc"],
        "urgency": info["urgency"],
        "medical": info["medical"],
        "lifestyle": info["lifestyle"],
        "secondary": None,
        "disclaimer": (
            "⚠️ 本报告为 AI 辅助评估，仅供参考，"
            "不能替代专业医疗诊断。最终诊断和治疗方案请务必遵医嘱。"
        ),
    }

    # 边界情况：同时给出次选级别的建议
    if prediction_result["is_borderline"] and prediction_result["secondary_grade"]:
        sec_grade = prediction_result["secondary_grade"]
        sec_info = RECOMMENDATIONS.get(sec_grade, {})
        result["secondary"] = {
            "grade": sec_grade,
            "confidence": prediction_result["secondary_confidence"],
            "level_desc": sec_info.get("level_desc", ""),
            "urgency": sec_info.get("urgency", ""),
            "medical": sec_info.get("medical", []),
            "lifestyle": sec_info.get("lifestyle", []),
        }
        result["borderline_note"] = (
            f"模型判断您的情况处于 {grade} 和 {sec_grade} 的边界。"
            f"以上为 {grade} 的建议，同时下方列出了 {sec_grade} 的建议供参考。"
            f"建议临床医生进一步评估确认。"
        )

    return result


def format_report(recommendations: dict) -> str:
    """
    将建议格式化为可展示的 HTML 报告文本。

    返回 HTML 片段字符串。
    """
    lines = []
    grade = recommendations["grade"]
    conf  = recommendations["confidence"]
    is_border = recommendations["is_borderline"]

    # 分级结果
    lines.append(f'<div class="result-grade">{grade}</div>')
    lines.append(f'<div class="result-confidence">置信度：{conf:.1%}</div>')

    if is_border and recommendations.get("borderline_note"):
        lines.append(
            f'<div class="result-borderline">'
            f'{recommendations["borderline_note"]}'
            f'</div>'
        )

    # 严重程度描述
    lines.append(f'<div class="result-section">')
    lines.append(f'<div class="section-title">📋 严重程度</div>')
    lines.append(f'<div class="section-body">{recommendations["level_desc"]}</div>')
    lines.append(f'<div class="urgency-tag urgency-{recommendations["urgency"]}">'
                 f'就医建议：{recommendations["urgency"]}</div>')
    lines.append(f'</div>')

    # 医学建议
    lines.append(f'<div class="result-section">')
    lines.append(f'<div class="section-title">🩺 医学建议</div>')
    lines.append(f'<ul class="advice-list">')
    for item in recommendations["medical"]:
        lines.append(f'<li>{item}</li>')
    lines.append(f'</ul>')
    lines.append(f'</div>')

    # 生活建议
    lines.append(f'<div class="result-section">')
    lines.append(f'<div class="section-title">🏠 生活建议</div>')
    lines.append(f'<ul class="advice-list">')
    for item in recommendations["lifestyle"]:
        lines.append(f'<li>{item}</li>')
    lines.append(f'</ul>')
    lines.append(f'</div>')

    # 次选级别建议（边界情况）
    if recommendations.get("secondary"):
        sec = recommendations["secondary"]
        lines.append(f'<div class="result-section secondary-section">')
        lines.append(f'<div class="section-title">'
                     f'⚠️ 次选可能：{sec["grade"]}（置信度 {sec["confidence"]:.1%}）</div>')
        lines.append(f'<div class="section-body">{sec["level_desc"]}</div>')
        lines.append(f'<div class="section-subtitle">🩺 医学建议</div>')
        lines.append(f'<ul class="advice-list">')
        for item in sec["medical"]:
            lines.append(f'<li>{item}</li>')
        lines.append(f'</ul>')
        lines.append(f'<div class="section-subtitle">🏠 生活建议</div>')
        lines.append(f'<ul class="advice-list">')
        for item in sec["lifestyle"]:
            lines.append(f'<li>{item}</li>')
        lines.append(f'</ul>')
        lines.append(f'</div>')

    # 免责声明
    lines.append(f'<div class="disclaimer">{recommendations["disclaimer"]}</div>')

    return "\n".join(lines)
