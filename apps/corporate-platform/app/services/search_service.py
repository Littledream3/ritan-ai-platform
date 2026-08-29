"""Web 搜索服务 — DuckDuckGo 免费搜索 + wttr.in 天气（无需 API Key）"""

import asyncio

import httpx
from ddgs import DDGS
from loguru import logger


# ---- 天气 ----

_WEATHER_KEYWORDS = (
    "天气", "气温", "温度", "多少度", "热不热", "冷不冷",
    "下雨", "刮风", "风力", "湿度", "紫外线", "雾霾",
    "晴", "阴", "多云", "降水", "暴风雨", "台风",
)


def is_weather_query(text: str) -> bool:
    """判断查询是否与天气相关"""
    return any(kw in text for kw in _WEATHER_KEYWORDS)


# 天气描述英 → 中翻译表
_WEATHER_TRANS = {
    "sunny": "晴",
    "clear": "晴",
    "partly cloudy": "多云",
    "partly cloudy ": "多云",
    "cloudy": "阴",
    "overcast": "阴",
    "mist": "薄雾",
    "fog": "雾",
    "smoky haze": "霾",
    "haze": "霾",
    "freezing fog": "冻雾",
    "patchy rain nearby": "局部阵雨",
    "patchy rain possible": "局部阵雨",
    "patchy light rain": "局部小雨",
    "light rain": "小雨",
    "moderate rain": "中雨",
    "moderate rain at times": "间歇中雨",
    "heavy rain": "大雨",
    "heavy rain at times": "间歇大雨",
    "torrential rain": "暴雨",
    "light drizzle": "毛毛雨",
    "drizzle": "毛毛雨",
    "thunderstorm": "雷暴",
    "thunderstorm with rain": "雷阵雨",
    "thunder": "雷",
    "snow": "雪",
    "light snow": "小雪",
    "moderate snow": "中雪",
    "heavy snow": "大雪",
    "blizzard": "暴风雪",
    "blowing snow": "吹雪",
    "sleet": "雨夹雪",
    "ice pellets": "冰粒",
    "freezing rain": "冻雨",
    "light rain shower": "小阵雨",
    "moderate or heavy rain shower": "大阵雨",
    "patchy sleet nearby": "局部雨夹雪",
    "patchy snow nearby": "局部雪",
    "patchy freezing drizzle nearby": "局部冻毛毛雨",
    "light freezing rain": "小冻雨",
    "moderate or heavy freezing rain": "大冻雨",
}

# 风向缩写 → 中文
_WIND_DIR = {
    "N": "北", "NNE": "北东北", "NE": "东北", "ENE": "东东北",
    "E": "东", "ESE": "东东南", "SE": "东南", "SSE": "南东南",
    "S": "南", "SSW": "南西南", "SW": "西南", "WSW": "西西南",
    "W": "西", "WNW": "西西北", "NW": "西北", "NNW": "北西北",
}


def _translate_weather(desc: str) -> str:
    """翻译天气描述，支持模糊匹配"""
    desc_lower = desc.lower().strip()
    if desc_lower in _WEATHER_TRANS:
        return _WEATHER_TRANS[desc_lower]
    # 模糊匹配
    for en, zh in _WEATHER_TRANS.items():
        if en in desc_lower:
            return zh
    return desc


async def get_weather(city: str = "北京") -> str | None:
    """
    通过 wttr.in 获取实时天气（免费，无需 API Key）

    Args:
        city: 城市名（中文或英文）

    Returns:
        格式化的天气文本，失败返回 None
    """
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(f"https://wttr.in/{city}?format=j1")
            resp.raise_for_status()
            data = resp.json()
    except Exception as e:
        logger.error(f"天气查询失败 ({city}): {e}")
        return None

    try:
        current = data["current_condition"][0]
        # 使用传入的中文城市名，API 返回的通常是英文
        city_cn = city if any('一' <= c <= '鿿' for c in city) else city

        weather_zh = _translate_weather(current['weatherDesc'][0]['value'])
        wind_dir = _WIND_DIR.get(current['winddir16Point'], current['winddir16Point'])

        lines = [
            f"📍 {city_cn} 实时天气",
            f"🌡 温度: {current['temp_C']}°C（体感 {current['FeelsLikeC']}°C）",
            f"☁ 天气: {weather_zh}",
            f"💧 湿度: {current['humidity']}%",
            f"🌬 风速: {current['windspeedKmph']} km/h {wind_dir}风",
            f"👁 能见度: {current['visibility']} km",
        ]

        uv = current.get('uvIndex', '')
        if uv:
            uv_label = "低" if int(uv) <= 2 else ("中" if int(uv) <= 5 else ("高" if int(uv) <= 7 else "极高"))
            lines.append(f"☀ 紫外线: {uv}（{uv_label}）")

        # 天气预报
        weather_list = data.get("weather", [])
        if weather_list:
            lines.append("\n📅 三日预报:")
            for day in weather_list[:3]:
                hourly = day.get("hourly", [])
                desc = hourly[4]["weatherDesc"][0]["value"] if len(hourly) > 4 else (
                    hourly[0]["weatherDesc"][0]["value"] if hourly else "未知"
                )
                desc_zh = _translate_weather(desc)
                d = f"  {day['date']}: {desc_zh}，{day['mintempC']}~{day['maxtempC']}°C"
                lines.append(d)

        result = "\n".join(lines)
        logger.info(f"天气查询成功: {city_cn}")
        return result
    except Exception as e:
        logger.error(f"天气数据解析失败: {e}")
        return None


# ---- 网页搜索 ----


async def search_web(query: str, max_results: int = 5) -> list[dict]:
    """
    搜索网页，返回结构化结果

    Args:
        query: 搜索关键词
        max_results: 最大返回条数

    Returns:
        [{"title": "...", "url": "...", "snippet": "..."}, ...]
    """
    try:
        results = await asyncio.to_thread(_sync_search, query, max_results)
        logger.info(f"搜索完成: query={query[:50]}, results={len(results)}")
        return results
    except Exception as e:
        logger.error(f"搜索失败: {e}")
        return []


def _sync_search(query: str, max_results: int) -> list[dict]:
    """同步搜索（在 asyncio.to_thread 中运行）

    默认使用 Bing 后端 — 在中国大陆网络环境下最稳定。
    auto 模式会尝试 Brave/Google/DuckDuckGo 等被封的后端导致超时。
    """
    with DDGS() as ddgs:
        raw = list(ddgs.text(query, backend="bing", max_results=max_results))
        return [
            {
                "title": r.get("title", ""),
                "url": r.get("href", ""),
                "snippet": r.get("body", ""),
            }
            for r in raw
        ]
