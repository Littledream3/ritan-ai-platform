# -*- coding: utf-8 -*-
"""Server-side PDF rendering for DFU auxiliary assessment records.

The report deliberately identifies itself as an auxiliary assessment. It is
not a pathology report, medical certificate, or physician-signed diagnosis.
"""
from __future__ import annotations

import io
import os
import re
from datetime import datetime
from html import escape
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas as pdfcanvas
from reportlab.platypus import (
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


INK = colors.HexColor("#263746")
MUTED = colors.HexColor("#6B747C")
ACCENT = colors.HexColor("#315F78")
ACCENT_SOFT = colors.HexColor("#EEF3F6")
PAPER = colors.white
LINE = colors.HexColor("#D8DEE3")
SOFT = colors.HexColor("#F5F7F8")
ALERT = colors.HexColor("#FFF7E6")
ALERT_LINE = colors.HexColor("#D99A23")
ALERT_INK = colors.HexColor("#6F4A12")

SEX_LABELS = {"male": "男", "female": "女", "other": "其他"}
DIABETES_LABELS = {"unknown": "未知", **{str(i): str(i) for i in range(6)}}
DIET_LABELS = {
    "balanced": "饮食规律、种类均衡",
    "refined_carbs": "主食或精制碳水偏多",
    "high_salt": "高盐、重口味",
    "high_fat": "高油、油炸食品较多",
    "high_sugar": "甜食或含糖饮料较多",
    "low_produce": "蔬菜水果摄入不足",
    "processed_food": "外卖或加工食品较多",
    "irregular_meals": "三餐不规律、夜宵较多",
}

DISCLAIMER = (
    "本报告由日坛 AI 糖尿病足溃疡智能辅助评估系统生成，仅供健康管理和临床辅助参考，"
    "不构成医疗机构出具的正式诊断、病理报告或治疗处方。最终诊断与治疗方案应由具备"
    "资质的医疗专业人员结合面诊、检查及病史作出。"
)


LATIN_REGULAR = "RitanReportLatin"
LATIN_BOLD = "RitanReportLatinBold"


def _font_paths() -> tuple[Path, Path]:
    """Choose embeddable CJK fonts supported by ReportLab's TTFont parser."""
    configured_regular = os.getenv("DFU_REPORT_FONT", "")
    configured_bold = os.getenv("DFU_REPORT_FONT_BOLD", "")
    pairs = [
        (configured_regular, configured_bold or configured_regular),
        ("C:/Windows/Fonts/msyh.ttc", "C:/Windows/Fonts/msyhbd.ttc"),
        ("C:/Windows/Fonts/simhei.ttf", "C:/Windows/Fonts/simhei.ttf"),
        (
            "/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf",
            "/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf",
        ),
    ]
    for regular, bold in pairs:
        if regular and Path(regular).is_file():
            bold_path = Path(bold) if bold and Path(bold).is_file() else Path(regular)
            return Path(regular), bold_path
    raise RuntimeError("未找到可用于生成中文报告的字体，请设置 DFU_REPORT_FONT")


def _latin_font_paths() -> tuple[Path, Path]:
    pairs = [
        (
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        ),
        ("C:/Windows/Fonts/arial.ttf", "C:/Windows/Fonts/arialbd.ttf"),
        ("C:/Windows/Fonts/msyh.ttc", "C:/Windows/Fonts/msyhbd.ttc"),
    ]
    for regular, bold in pairs:
        if Path(regular).is_file():
            bold_path = Path(bold) if Path(bold).is_file() else Path(regular)
            return Path(regular), bold_path
    raise RuntimeError("未找到可用于报告数字和英文的字体")


def _register_fonts() -> tuple[str, str]:
    regular = "RitanReportCJK"
    bold = "RitanReportCJKBold"
    if regular not in pdfmetrics.getRegisteredFontNames():
        regular_path, bold_path = _font_paths()
        pdfmetrics.registerFont(TTFont(regular, str(regular_path), subfontIndex=0))
        pdfmetrics.registerFont(TTFont(bold, str(bold_path), subfontIndex=0))
        latin_regular_path, latin_bold_path = _latin_font_paths()
        pdfmetrics.registerFont(TTFont(LATIN_REGULAR, str(latin_regular_path), subfontIndex=0))
        pdfmetrics.registerFont(TTFont(LATIN_BOLD, str(latin_bold_path), subfontIndex=0))
    return regular, bold


def _is_blank(value: object) -> bool:
    return value is None or (isinstance(value, str) and not value.strip())


def _clean(value: object, fallback: str = "未填写") -> str:
    if _is_blank(value):
        return fallback
    text = str(value)
    text = text.replace("—", "-").replace("–", "-")
    text = re.sub(r"[\U00010000-\U0010ffff]", "", text)
    text = re.sub(r"[\u2600-\u27bf]", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text or fallback


def _p(value: object, style: ParagraphStyle, fallback: str = "未填写") -> Paragraph:
    text = _clean(value, fallback)
    latin_font = LATIN_BOLD if style.fontName == "RitanReportCJKBold" else LATIN_REGULAR
    parts = []
    for part in re.split(r"([ -~]+)", text):
        if not part:
            continue
        escaped = escape(part)
        if re.fullmatch(r"[ -~]+", part):
            parts.append(f'<font name="{latin_font}">{escaped}</font>')
        else:
            parts.append(escaped)
    return Paragraph("".join(parts), style)


def _draw_segments(
    canvas,
    x: float,
    y: float,
    segments: list[tuple[str, str]],
    size: float,
    *,
    align: str = "left",
) -> None:
    widths = [pdfmetrics.stringWidth(segment, font_name, size) for font_name, segment in segments]
    total_width = sum(widths)
    if align == "center":
        x -= total_width / 2
    elif align == "right":
        x -= total_width
    for (font_name, segment), width in zip(segments, widths):
        canvas.setFont(font_name, size)
        canvas.drawString(x, y, segment)
        x += width


def _format_date(value: object, fallback: str = "-") -> str:
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d %H:%M")
    if _is_blank(value):
        return fallback
    text = _clean(value, fallback)
    match = re.match(r"^(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2})", text)
    return match.group(1) if match else text


def _with_unit(value: object, unit: str, fallback: str = "未填写") -> str:
    return fallback if _is_blank(value) else f"{_clean(value, fallback)} {unit}"


def _percentage(value: object, fallback: str = "-") -> str:
    if _is_blank(value):
        return fallback
    try:
        return f"{float(value):.1%}"
    except (TypeError, ValueError):
        return fallback


def _display_grade(value: object, fallback: str = "-") -> str:
    text = _clean(value, fallback)
    match = re.fullmatch(r"Grade\s*([0-5])", text, re.IGNORECASE)
    if match:
        return f"{match.group(1)} 级"
    if text.lower() == "normal":
        return "未见明确溃疡"
    return text


def _report_number(record: dict) -> str:
    created = str(record.get("created_at") or "")
    digits = re.sub(r"\D", "", created)[:8] or datetime.now().strftime("%Y%m%d")
    try:
        record_id = f"{int(record.get('id')):06d}"
    except (TypeError, ValueError):
        record_id = "000000"
    return f"RT-DFU-{digits}-{record_id}"


def _diet_text(patient: dict, encounter: dict | None) -> str:
    if encounter is not None:
        values = encounter.get("dietary_habits") or []
        labels = [DIET_LABELS.get(str(item), str(item)) for item in values]
    else:
        labels = patient.get("dietary_habit_labels") or []
        if not labels:
            labels = [
                DIET_LABELS.get(str(item), str(item))
                for item in patient.get("dietary_habits") or []
            ]
    cleaned = [_clean(item, "") for item in labels if _clean(item, "")]
    return "、".join(cleaned) or "未填写"


def _styles(font: str, bold: str) -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "brand": ParagraphStyle(
            "Brand", parent=base["Normal"], fontName=bold, fontSize=9,
            leading=12, textColor=ACCENT, spaceAfter=2,
        ),
        "title": ParagraphStyle(
            "Title", parent=base["Title"], fontName=bold, fontSize=21,
            leading=27, textColor=INK, alignment=TA_LEFT, spaceAfter=4,
        ),
        "subtitle": ParagraphStyle(
            "Subtitle", parent=base["Normal"], fontName=font, fontSize=8.5,
            leading=12, textColor=MUTED,
        ),
        "section": ParagraphStyle(
            "Section", parent=base["Heading2"], fontName=bold, fontSize=13.5,
            leading=18, textColor=INK,
        ),
        "section_number": ParagraphStyle(
            "SectionNumber", parent=base["Normal"], fontName=font, fontSize=8,
            leading=11, textColor=MUTED, alignment=TA_RIGHT,
        ),
        "label": ParagraphStyle(
            "Label", parent=base["Normal"], fontName=font, fontSize=8.7,
            leading=11.5, textColor=MUTED,
        ),
        "value": ParagraphStyle(
            "Value", parent=base["Normal"], fontName=bold, fontSize=10.7,
            leading=14.5, textColor=INK,
        ),
        "body": ParagraphStyle(
            "Body", parent=base["BodyText"], fontName=font, fontSize=9.7,
            leading=14.2, textColor=INK, alignment=TA_LEFT, wordWrap="CJK",
        ),
        "small": ParagraphStyle(
            "Small", parent=base["Normal"], fontName=font, fontSize=8.3,
            leading=12.2, textColor=MUTED, alignment=TA_LEFT, wordWrap="CJK",
        ),
        "meta_value": ParagraphStyle(
            "MetaValue", parent=base["Normal"], fontName=bold, fontSize=8.5,
            leading=12, textColor=INK, alignment=TA_RIGHT,
        ),
        "card_label": ParagraphStyle(
            "CardLabel", parent=base["Normal"], fontName=font, fontSize=8.7,
            leading=11, textColor=MUTED, alignment=TA_CENTER,
        ),
        "card_grade": ParagraphStyle(
            "CardGrade", parent=base["Title"], fontName=bold, fontSize=22,
            leading=27, textColor=INK, alignment=TA_CENTER,
        ),
        "card_metric": ParagraphStyle(
            "CardMetric", parent=base["Normal"], fontName=bold, fontSize=16,
            leading=20, textColor=INK, alignment=TA_CENTER,
        ),
        "rank": ParagraphStyle(
            "Rank", parent=base["Normal"], fontName=bold, fontSize=9,
            leading=12, textColor=ACCENT, alignment=TA_CENTER,
        ),
        "probability": ParagraphStyle(
            "Probability", parent=base["Normal"], fontName=bold, fontSize=9.2,
            leading=12, textColor=INK, alignment=TA_RIGHT,
        ),
        "alert_title": ParagraphStyle(
            "AlertTitle", parent=base["Normal"], fontName=bold, fontSize=9.3,
            leading=12.5, textColor=ALERT_INK,
        ),
        "alert": ParagraphStyle(
            "Alert", parent=base["BodyText"], fontName=font, fontSize=8.8,
            leading=13.2, textColor=ALERT_INK, alignment=TA_LEFT, wordWrap="CJK",
        ),
        "list_marker": ParagraphStyle(
            "ListMarker", parent=base["Normal"], fontName=bold, fontSize=9.3,
            leading=14, textColor=ACCENT, alignment=TA_CENTER,
        ),
        "footer": ParagraphStyle(
            "Footer", parent=base["Normal"], fontName=font, fontSize=7.5,
            leading=10, textColor=MUTED,
        ),
    }


def _section_title(number: str, title: str, styles: dict) -> Table:
    table = Table(
        [["", _p(title, styles["section"], ""), _p(f"SECTION {number}", styles["section_number"], "")]],
        colWidths=[2.5 * mm, 137.5 * mm, 34 * mm],
        rowHeights=[9 * mm],
    )
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, 0), ACCENT),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (0, 0), 0),
        ("RIGHTPADDING", (0, 0), (0, 0), 0),
        ("LEFTPADDING", (1, 0), (1, 0), 7),
        ("RIGHTPADDING", (1, 0), (1, 0), 0),
        ("LEFTPADDING", (2, 0), (2, 0), 0),
        ("RIGHTPADDING", (2, 0), (2, 0), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))
    return table


def _info_table(rows: list[list[tuple[str, object]]], styles: dict) -> Table:
    data = []
    for row in rows:
        cells = []
        for label, value in row:
            cells.append(Table(
                [[_p(label, styles["label"], "")], [_p(value, styles["value"]) ]],
                colWidths=[57 * mm],
                style=[
                    ("LEFTPADDING", (0, 0), (-1, -1), 0),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                    ("TOPPADDING", (0, 0), (-1, -1), 0),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
                ],
            ))
        while len(cells) < 3:
            cells.append("")
        data.append(cells)
    table = Table(data, colWidths=[58 * mm, 58 * mm, 58 * mm], rowHeights=[15 * mm] * len(data))
    table.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 0.7, LINE),
        ("INNERGRID", (0, 0), (-1, -1), 0.45, LINE),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 7),
        ("RIGHTPADDING", (0, 0), (-1, -1), 7),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("BACKGROUND", (0, 0), (-1, -1), PAPER),
    ]))
    return table


def _field_strip(label: str, value: object, styles: dict) -> Table:
    table = Table(
        [[[_p(label, styles["label"], ""), Spacer(1, 1.5 * mm), _p(value, styles["value"])]]],
        colWidths=[174 * mm],
    )
    table.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 0.7, LINE),
        ("BACKGROUND", (0, 0), (-1, -1), PAPER),
        ("LEFTPADDING", (0, 0), (-1, -1), 7),
        ("RIGHTPADDING", (0, 0), (-1, -1), 7),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    return table


def _metric_card(label: str, value: str, width: float, styles: dict, *, primary: bool = False) -> Table:
    value_style = styles["card_grade"] if primary else styles["card_metric"]
    table = Table(
        [[_p(label, styles["card_label"], "")], [_p(value, value_style, "-")]],
        colWidths=[width],
        rowHeights=[9 * mm, 18 * mm],
    )
    table.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 0.7, LINE),
        ("BACKGROUND", (0, 0), (-1, -1), ACCENT_SOFT if primary else PAPER),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
    ]))
    return table


def _result_cards(grade: str, confidence: str, urgency: str, styles: dict) -> Table:
    first_width, second_width, third_width = 68 * mm, 43 * mm, 57 * mm
    table = Table([[ 
        _metric_card("本次评估分级", grade, first_width, styles, primary=True),
        "",
        _metric_card("评估置信度", confidence, second_width, styles),
        "",
        _metric_card("建议就医时效", urgency, third_width, styles),
    ]], colWidths=[first_width, 3 * mm, second_width, 3 * mm, third_width])
    table.setStyle(TableStyle([
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    return table


def _top_probabilities(record: dict) -> list[tuple[str, float]]:
    values = record.get("probabilities") or []
    if not isinstance(values, list) or not values:
        return []
    labels = (
        ["Normal", "Grade 0", "Grade 1", "Grade 2", "Grade 3", "Grade 4", "Grade 5"]
        if len(values) == 7 else
        ["Grade 1", "Grade 2", "Grade 3", "Grade 4"]
    )
    pairs = []
    for label, value in zip(labels, values):
        try:
            pairs.append((label, max(0.0, min(1.0, float(value)))))
        except (TypeError, ValueError):
            continue
    return sorted(pairs, key=lambda item: item[1], reverse=True)[:2]


def _progress_bar(probability: float, width: float = 100 * mm) -> Table:
    minimum = 0.4 * mm
    filled = max(minimum, min(width - minimum, width * probability))
    remaining = width - filled
    table = Table([["", ""]], colWidths=[filled, remaining], rowHeights=[3.2 * mm])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, 0), ACCENT),
        ("BACKGROUND", (1, 0), (1, 0), LINE),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))
    return table


def _probability_block(top: list[tuple[str, float]], styles: dict) -> Table:
    if not top:
        table = Table(
            [[_p("概率较高的两个分级", styles["label"], ""), _p("暂无可展示的概率结果", styles["body"], "-")]],
            colWidths=[50 * mm, 124 * mm],
            rowHeights=[12 * mm],
        )
        table.setStyle(TableStyle([
            ("BOX", (0, 0), (-1, -1), 0.7, LINE),
            ("BACKGROUND", (0, 0), (-1, -1), SOFT),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ]))
        return table

    rows = [[_p("概率较高的两个分级", styles["value"], ""), "", "", ""]]
    for index, (grade, probability) in enumerate(top, start=1):
        rows.append([
            _p(str(index), styles["rank"], ""),
            _p(_display_grade(grade), styles["value"], "-"),
            _p(_percentage(probability), styles["probability"], "-"),
            _progress_bar(probability),
        ])
    table = Table(rows, colWidths=[10 * mm, 36 * mm, 22 * mm, 106 * mm], rowHeights=[9 * mm] + [8 * mm] * len(top))
    table.setStyle(TableStyle([
        ("SPAN", (0, 0), (-1, 0)),
        ("BOX", (0, 0), (-1, -1), 0.7, LINE),
        ("LINEBELOW", (0, 0), (-1, 0), 0.45, LINE),
        ("BACKGROUND", (0, 0), (-1, -1), SOFT),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
    ]))
    return table


def _description_block(description: object, styles: dict) -> Table:
    table = Table(
        [[[_p("评估说明", styles["label"], ""), Spacer(1, 1.5 * mm), _p(description, styles["body"], "-")]]],
        colWidths=[174 * mm],
    )
    table.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 0.6, LINE),
        ("BACKGROUND", (0, 0), (-1, -1), PAPER),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    return table


def _borderline_block(record: dict, styles: dict) -> Table:
    secondary = None if _is_blank(record.get("secondary_grade")) else _display_grade(record.get("secondary_grade"))
    secondary_confidence = None if _is_blank(record.get("secondary_confidence")) else _percentage(record.get("secondary_confidence"))
    details = "本次结果接近相邻分级。"
    if secondary and secondary_confidence:
        details += f"次选为 {secondary}（{secondary_confidence}）。"
    elif secondary:
        details += f"次选为 {secondary}。"
    details += "请由专业医生结合临床表现进一步确认。"
    table = Table(
        [[[_p("边界结果提示", styles["alert_title"], ""), Spacer(1, 1.2 * mm), _p(details, styles["alert"], "-")]]],
        colWidths=[174 * mm],
    )
    table.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 0.55, ALERT_LINE),
        ("LINEBEFORE", (0, 0), (0, 0), 3, ALERT_LINE),
        ("BACKGROUND", (0, 0), (-1, -1), ALERT),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    return table


def _advice_block(title: str, items: list, styles: dict, *, ordered: bool) -> KeepTogether:
    rows = [[_p(title, styles["value"], ""), ""]]
    if items:
        for index, item in enumerate(items, start=1):
            marker = f"{index}." if ordered else "•"
            rows.append([
                _p(marker, styles["list_marker"], ""),
                _p(item, styles["body"], "-"),
            ])
    else:
        rows.append([_p("-", styles["list_marker"], ""), _p("暂无记录", styles["body"], "-")])
    table = Table(rows, colWidths=[9 * mm, 159 * mm])
    table.setStyle(TableStyle([
        ("SPAN", (0, 0), (-1, 0)),
        ("BACKGROUND", (0, 0), (-1, -1), SOFT),
        ("LINEBELOW", (0, 0), (-1, 0), 0.6, LINE),
        ("BOX", (0, 0), (-1, -1), 0.45, LINE),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, 0), 7),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 7),
        ("TOPPADDING", (0, 1), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 1), (-1, -1), 4),
    ]))
    return KeepTogether([table, Spacer(1, 3 * mm)])


def _continuation_header(number: str, styles: dict) -> Table:
    table = Table([
        [_p("糖尿病足溃疡智能辅助评估报告", styles["small"], ""), _p(f"报告编号：{number}", styles["meta_value"], "-")],
    ], colWidths=[104 * mm, 70 * mm])
    table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LINEBELOW", (0, 0), (-1, -1), 0.8, LINE),
    ]))
    return table


def _report_canvas_factory(number: str, font: str, latin_font: str):
    class NumberedReportCanvas(pdfcanvas.Canvas):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self._saved_page_states = []

        def showPage(self):
            self._saved_page_states.append(dict(self.__dict__))
            self._startPage()

        def save(self):
            total_pages = len(self._saved_page_states)
            for page_number, state in enumerate(self._saved_page_states, start=1):
                self.__dict__.update(state)
                self.setFillColor(MUTED)
                _draw_segments(
                    self,
                    105 * mm,
                    10.5 * mm,
                    [
                        (font, "第 "),
                        (latin_font, str(page_number)),
                        (font, " 页 "),
                        (latin_font, "/"),
                        (font, " 共 "),
                        (latin_font, str(total_pages)),
                        (font, " 页"),
                    ],
                    7.5,
                    align="center",
                )
                pdfcanvas.Canvas.showPage(self)
            pdfcanvas.Canvas.save(self)

    return NumberedReportCanvas


def build_assessment_report(
    record: dict,
    patient: dict,
    encounter: dict | None,
    operator: dict | None,
    recommendations: dict,
) -> tuple[bytes, str]:
    """Return a complete A4 PDF and a deterministic, safe filename."""
    font, bold = _register_fonts()
    styles = _styles(font, bold)
    output = io.BytesIO()
    number = _report_number(record)
    generated_at = datetime.now()

    def on_page(canvas, doc):
        canvas.saveState()
        canvas.setStrokeColor(LINE)
        canvas.setLineWidth(0.5)
        canvas.line(18 * mm, 16 * mm, 192 * mm, 16 * mm)
        canvas.setFillColor(MUTED)
        _draw_segments(
            canvas,
            18 * mm,
            10.5 * mm,
            [(font, "报告编号："), (LATIN_REGULAR, number)],
            7.5,
        )
        canvas.setFont(font, 7.5)
        canvas.drawRightString(192 * mm, 10.5 * mm, "智能辅助评估｜非正式医疗诊断")
        canvas.restoreState()

    doc = SimpleDocTemplate(
        output,
        pagesize=A4,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=16 * mm,
        bottomMargin=22 * mm,
        title="糖尿病足溃疡智能辅助评估报告",
        author="日坛 AI",
        subject="糖尿病足溃疡智能辅助评估",
    )

    created_at = _format_date(record.get("created_at"))
    header_left = [
        _p("日坛 AI · 临床辅助评估", styles["brand"], ""),
        _p("糖尿病足溃疡智能辅助评估报告", styles["title"], ""),
        _p("智能辅助评估｜非正式医疗诊断", styles["subtitle"], ""),
    ]
    header_right = [
        _p("报告编号", styles["label"], ""),
        _p(number, styles["meta_value"], "-"),
        Spacer(1, 2 * mm),
        _p("评估时间", styles["label"], ""),
        _p(created_at, styles["meta_value"], "-"),
    ]
    header = Table([[header_left, header_right]], colWidths=[112 * mm, 62 * mm])
    header.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ALIGN", (1, 0), (1, 0), "RIGHT"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("LINEBELOW", (0, 0), (-1, -1), 0.9, INK),
    ]))

    source = encounter or patient
    sex_raw = source.get("sex")
    sex = "未填写" if _is_blank(sex_raw) else SEX_LABELS.get(str(sex_raw), _clean(sex_raw))
    if encounter:
        diabetes_raw = source.get("diabetes_grade")
        diabetes = "未填写" if _is_blank(diabetes_raw) else DIABETES_LABELS.get(str(diabetes_raw), _clean(diabetes_raw))
        diabetes_label = "糖尿病等级"
        admission_id = encounter.get("admission_id") or "未填写"
        encounter_code = encounter.get("encounter_code") or "-"
    else:
        diabetes = _display_grade(record.get("grade"))
        diabetes_label = "本次检测等级"
        admission_id = "不适用"
        encounter_code = "不适用"

    info_rows = [
        [
            ("姓名", source.get("name")),
            ("性别", sex),
            ("年龄", _with_unit(source.get("age"), "岁")),
        ],
        [
            ("患者编号", patient.get("patient_code") or "-"),
            ("手机号", source.get("phone") or patient.get("phone")),
            (diabetes_label, diabetes),
        ],
        [
            ("住院 ID", admission_id),
            ("采集记录编号", encounter_code),
            ("居住地", source.get("residence")),
        ],
    ]

    top = _top_probabilities(record)
    grade = _display_grade(record.get("grade"))
    confidence = _percentage(record.get("confidence"))
    urgency = _clean(recommendations.get("urgency"), "-")

    operator_name = "患者本人"
    operator_org = "不适用"
    if operator:
        operator_name = operator.get("real_name") or operator.get("username") or "未填写"
        operator_org = " / ".join(
            filter(None, [operator.get("institution"), operator.get("department")])
        ) or "未填写"

    images = record.get("images")
    if isinstance(images, list) and images:
        image_count = len(images)
    elif record.get("image_name"):
        image_count = 1
    else:
        image_count = None

    story = [
        header,
        Spacer(1, 6 * mm),
        _section_title("01", "患者与采集信息", styles),
        Spacer(1, 3 * mm),
        _info_table(info_rows, styles),
        _field_strip("饮食习惯", _diet_text(patient, encounter), styles),
        Spacer(1, 6 * mm),
        _section_title("02", "智能辅助评估结果", styles),
        Spacer(1, 3 * mm),
        _result_cards(grade, confidence, urgency, styles),
        Spacer(1, 3 * mm),
        _probability_block(top, styles),
        Spacer(1, 3 * mm),
        _description_block(recommendations.get("level_desc"), styles),
    ]

    if record.get("is_borderline"):
        story.extend([Spacer(1, 3 * mm), _borderline_block(record, styles)])

    story.extend([
        PageBreak(),
        _continuation_header(number, styles),
        Spacer(1, 6 * mm),
        _section_title("03", "建议与注意事项", styles),
        Spacer(1, 3 * mm),
        _advice_block(
            "医疗建议",
            record.get("medical") or recommendations.get("medical") or [],
            styles,
            ordered=True,
        ),
        _advice_block(
            "日常管理建议",
            record.get("lifestyle") or recommendations.get("lifestyle") or [],
            styles,
            ordered=False,
        ),
        Spacer(1, 3 * mm),
        _section_title("04", "报告信息", styles),
        Spacer(1, 3 * mm),
        _info_table([
            [
                ("评估来源", "医生端采集" if operator else "患者端自主评估"),
                ("操作人员", operator_name),
                ("机构 / 科室", operator_org),
            ],
            [
                ("报告生成时间", generated_at.strftime("%Y-%m-%d %H:%M")),
                ("影像数量", _with_unit(image_count, "张", "-")),
                ("报告状态", "智能辅助评估"),
            ],
        ], styles),
        Spacer(1, 5 * mm),
        Table(
            [[[_p("重要说明", styles["value"], ""), Spacer(1, 1.5 * mm), _p(DISCLAIMER, styles["small"], "-")]]],
            colWidths=[174 * mm],
            style=[
                ("BOX", (0, 0), (-1, -1), 0.55, LINE),
                ("BACKGROUND", (0, 0), (-1, -1), SOFT),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                ("TOPPADDING", (0, 0), (-1, -1), 9),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 9),
            ],
        ),
    ])

    doc.build(
        story,
        onFirstPage=on_page,
        onLaterPages=on_page,
        canvasmaker=_report_canvas_factory(number, font, LATIN_REGULAR),
    )
    filename = f"ritan-dfu-assessment-{number}.pdf"
    return output.getvalue(), filename
