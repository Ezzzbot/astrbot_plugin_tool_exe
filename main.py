"""大头的工具箱 · 插件入口。

每个功能一个方法：读配置 → 调 tools/ 里的函数 → 把结果发出去。
真正的业务逻辑都在 tools/ 目录里的功能模块中（比如 tools/news.py）。
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
        """获取今日新闻。用法：/今日新闻"""
        options = self._options("news60s")
        if not options.get("enabled", True):
            yield event.plain_result("⚠️ 「今日新闻」已在插件配置里关闭。")
            return

        try:
            text, image = await news.get_daily_news(options)
        except Exception as exc:  # 网络或接口问题，只回一句提示，不让插件崩
            logger.exception("[tool_exe] 今日新闻获取失败")
            yield event.plain_result(f"📰 今日新闻获取失败：{exc}")
            return

        mode = str(options.get("send_mode", "text")).lower()
        if mode == "image" and image:
            yield event.image_result(image)
        elif mode == "both" and image:
            yield event.chain_result([Comp.Plain(text), Comp.Image.fromURL(image)])
        else:
            yield event.plain_result(text)

    def _options(self, name: str) -> dict:
        """合成一个配置字典交给 tools/ 里的函数。

        来源有三层，后面的覆盖前面的：
            config.yaml 的 network 段  →  config.yaml 的该功能段  →  WebUI 里的该功能段
        """
        network = self.dev_config.get("network") or {}
        dev_feature = self.dev_config.get(name) or {}
        web_feature = self.config.get(name) or {}
        return {**network, **dev_feature, **web_feature}
