"""今日新闻：接入 60s 看世界 API（https://github.com/vikiboss/60s）。

接口返回：{ "code": 200, "data": { "date", "day_of_week", "lunar_date",
                                   "news": [...], "tip", "image", "link" } }
"""

from __future__ import annotations

from .utils import fetch_json


async def get_daily_news(options: dict) -> tuple[str, str]:
    """获取今日新闻，返回 (文本, 图片地址)。

    options 里会读取：api、cache_seconds、show_meta、show_tip、show_link、footer
    """
    api = options.get("api") or "https://60s.viki.moe/v2/60s"
    payload = await fetch_json(api, options)

    if not isinstance(payload, dict):
        raise RuntimeError("接口返回格式异常")
    if str(payload.get("code")) != "200":
        raise RuntimeError(str(payload.get("message") or "接口返回异常"))

    data = payload.get("data") or {}
    news = [str(item).strip() for item in data.get("news") or [] if str(item).strip()]
    if not news:
        raise RuntimeError("接口暂时没有返回内容，可能还没更新")

    return format_news(data, news, options=options), str(data.get("image") or "")


def format_news(data: dict, news: list[str], options: dict) -> str:
    """把接口数据拼成一条好读的文本。想改排版只动这一个函数即可。"""
    lines = ["📰 今日新闻"]

    if options.get("show_meta", True):
        date = str(data.get("date") or "")
        week = str(data.get("day_of_week") or "")
        lunar = str(data.get("lunar_date") or "")
        meta = " · ".join(part for part in (date, week) if part)
        if meta:
            lines[0] += f" | {meta}"
        if lunar:
            lines.append(lunar)

    lines.append("")
    lines.extend(f"{index}. {item}" for index, item in enumerate(news, 1))

    tip = str(data.get("tip") or "")
    if options.get("show_tip", True) and tip:
        lines.extend(["", f"💡 {tip}"])

    link = str(data.get("link") or "")
    if options.get("show_link", True) and link:
        lines.extend(["", f"🔗 {link}"])

    footer = str(options.get("footer") or "").strip()
    if footer:
        lines.extend(["", footer])

    return "\n".join(lines)
