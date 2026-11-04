"""大头的工具箱 · 插件入口。

这里只有三类东西：
    1. 指令触发（@filter.command）
    2. LLM 触发（@filter.llm_tool）
    3. 上面两者共用的取数据方法

真正的业务逻辑都在 tools/ 目录里的功能模块中（比如 tools/news.py），
这一层只负责读配置、调函数、发消息。
"""

from __future__ import annotations

import astrbot.api.message_components as Comp
from astrbot.api import logger
from astrbot.api.event import AstrMessageEvent, filter
from astrbot.api.star import Context, Star, register

from .tools import news, utils

# 指令名和别名写在常量里，改名字只改这里
NEWS_CMD = "今日新闻"
NEWS_ALIASES = {"60s", "新闻60秒", "看世界"}

# /工具箱 的内容，新增功能时在这里补一行
HELP_TEXT = """🧰 工具箱
· /今日新闻 [条数]
  60 秒读懂世界每日新闻速览（别名：60s、新闻60秒、看世界）"""


@register(
    "astrbot_plugin_tool_exe",
    "大头",
    "综合性工具箱：以模块化方式接入各类实用功能，目前包含每日新闻速览。",
    "1.0.0",
)
class ToolBoxPlugin(Star):
    def __init__(self, context: Context, config: dict | None = None):
        super().__init__(context)
        self.config = config or {}

    async def initialize(self) -> None:
        logger.info("[tool_exe] 插件已加载")

    async def terminate(self) -> None:
        await utils.close()
        logger.info("[tool_exe] 插件已卸载")

    # ------------------------------------------------------------ 指令触发

    @filter.command(NEWS_CMD, alias=NEWS_ALIASES)
    async def cmd_news(self, event: AstrMessageEvent):
        """获取今日新闻。用法：/今日新闻 [条数]"""
        limit = self._read_number(event.message_str)
        yield await self._reply_news(event, limit)

    @filter.command("工具箱", alias={"toolbox", "功能列表"})
    async def cmd_help(self, event: AstrMessageEvent):
        """查看工具箱里有哪些功能"""
        yield event.plain_result(HELP_TEXT)

    # ------------------------------------------------------------ LLM 触发

    @filter.llm_tool(name="get_daily_news")
    async def llm_news(self, event: AstrMessageEvent, count: int = 10):
        """获取今天的热点新闻速览。当用户问「今天有什么新闻」「最近发生了什么大事」时调用。

        Args:
            count(number): 返回的新闻条数，默认 10
        """
        yield await self._reply_news(event, int(count) if count else None)

    # ------------------------------------------------------------ 两者共用

    async def _reply_news(self, event: AstrMessageEvent, limit: int | None):
        """指令和 LLM 工具都走这里：读配置 → 调 tools 里的函数 → 组装成消息。"""
        options = self._options("news60s")
        if not options.get("enabled", True):
            return event.plain_result("⚠️ 「今日新闻」已在插件配置里关闭。")

        try:
            text, image = await news.get_daily_news(options, limit)
        except Exception as exc:  # 网络或接口问题，只回一句提示，不让插件崩
            logger.exception("[tool_exe] 今日新闻获取失败")
            return event.plain_result(f"📰 今日新闻获取失败：{exc}")

        mode = str(options.get("send_mode", "text")).lower()
        if mode == "image" and image:
            return event.image_result(image)
        if mode == "both" and image:
            return event.chain_result([Comp.Plain(text), Comp.Image.fromURL(image)])
        return event.plain_result(text)

    def _options(self, name: str) -> dict:
        """把公共的网络配置和这个功能的配置合成一个字典，交给 tools.py 里的函数。"""
        network = self.config.get("network") or {}
        feature = self.config.get(name) or {}
        return {**network, **feature}

    @staticmethod
    def _read_number(message: str) -> int | None:
        """从消息里取条数，例如 /今日新闻 5、60s 3；取不到就返回 None 用配置里的默认值。"""
        words = message.replace("/", " ").split()
        if words and words[-1].isdigit():
            return int(words[-1])
        return None
