"""大头的工具箱 · 插件入口。

这里只有三类东西：
    1. 指令触发（@filter.command）
    2. LLM 触发（@filter.llm_tool）
    3. 上面两者共用的取数据方法

真正的业务逻辑都在 tools/ 目录里的功能模块中（比如 tools/news.py），
这一层只负责读配置、调函数、发消息。
"""

from __future__ import annotations

import os

import yaml

import astrbot.api.message_components as Comp
from astrbot.api import logger
from astrbot.api.event import AstrMessageEvent, filter
from astrbot.api.star import Context, Star, register

from .tools import news, utils

# 开发者配置文件，和 main.py 放在同一层
CONFIG_FILE = os.path.join(os.path.dirname(__file__), "config.yaml")

# 指令名和别名写在常量里，改名字只改这里
NEWS_CMD = "今日新闻"
NEWS_ALIASES = {"60s", "新闻60秒", "看世界"}

# /工具箱 的内容，新增功能时在这里补一行
HELP_TEXT = """🧰 工具箱
· /今日新闻 [条数]
  60 秒读懂世界每日新闻速览（别名：60s、新闻60秒、看世界）"""


def load_dev_config() -> dict:
    """读 config.yaml（面向开发者的配置）。文件缺失或写错都不影响插件启动。"""
    try:
        with open(CONFIG_FILE, encoding="utf-8") as file:
            data = yaml.safe_load(file) or {}
    except FileNotFoundError:
        return {}
    except Exception:
        logger.exception("[tool_exe] config.yaml 读取失败，已忽略，使用默认值")
        return {}
    return data if isinstance(data, dict) else {}


@register(
    "astrbot_plugin_tool_exe",
    "大头",
    "综合性工具箱：以模块化方式接入各类实用功能，目前包含每日新闻速览。",
    "1.0.0",
)
class ToolBoxPlugin(Star):
    def __init__(self, context: Context, config: dict | None = None):
        super().__init__(context)
        # WebUI 里改的配置（_conf_schema.json 定义的那三项）
        self.config = config or {}
        # config.yaml 里的开发者配置
        self.dev_config = load_dev_config()

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
    async def llm_news(self, event: AstrMessageEvent, count: int = 0):
        """获取今天的热点新闻速览。当用户问「今天有什么新闻」「最近发生了什么大事」时调用。

        Args:
            count(number): 返回的新闻条数，默认 0 表示全部返回
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
        """合成一个配置字典交给 tools/ 里的函数。

        来源有三层，后面的覆盖前面的：
            config.yaml 的 network 段  →  config.yaml 的该功能段  →  WebUI 里的该功能段
        """
        network = self.dev_config.get("network") or {}
        dev_feature = self.dev_config.get(name) or {}
        web_feature = self.config.get(name) or {}
        return {**network, **dev_feature, **web_feature}

    @staticmethod
    def _read_number(message: str) -> int | None:
        """从消息里取条数，例如 /今日新闻 5、60s 3；取不到就返回 None，表示全部返回。"""
        words = message.replace("/", " ").split()
        if words and words[-1].isdigit():
            return int(words[-1])
        return None
