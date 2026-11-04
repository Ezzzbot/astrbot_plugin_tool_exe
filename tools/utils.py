"""公共小工具：网络请求、连接池关闭。

不是框架，就是几个普通函数，功能模块直接 import 来用。
"""

from __future__ import annotations

import asyncio
import inspect
import time
from typing import Any

import aiohttp

from astrbot.api import logger

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 AstrBot-ToolBox"
)

# 简单的内存缓存：{接口地址: (过期时间戳, 数据)}，防止群里连续刷指令时反复请求
CACHE: dict[str, tuple[float, Any]] = {}

_session: aiohttp.ClientSession | None = None


async def _get_session() -> aiohttp.ClientSession:
    """全局复用一个连接池，第一次用到时才创建。"""
    global _session
    if _session is None or _session.closed:
        _session = aiohttp.ClientSession(headers={"User-Agent": USER_AGENT})
    return _session


async def close() -> None:
    """插件停用 / 卸载时释放连接，由 main.py 的 terminate 调用。"""
    global _session
    session, _session = _session, None
    if session is not None and not session.closed:
        result = session.close()
        if inspect.isawaitable(result):
            await result


async def fetch_json(url: str, options: dict) -> Any:
    """请求一个 JSON 接口，带超时、重试和缓存。失败抛 RuntimeError，消息可直接给用户看。

    options 里会读取：timeout（秒）、retries（次数）、proxy（代理）、cache_seconds（缓存时长）
    """
    timeout = float(options.get("timeout", 10))
    retries = max(1, int(options.get("retries", 2)))
    proxy = options.get("proxy") or None
    cache_seconds = float(options.get("cache_seconds", 600) or 0)

    if cache_seconds > 0:
        cached = CACHE.get(url)
        if cached and cached[0] > time.time():
            return cached[1]

    last_error = "未知错误"
    for attempt in range(1, retries + 1):
        try:
            session = await _get_session()
            async with session.get(
                url, proxy=proxy, timeout=aiohttp.ClientTimeout(total=timeout)
            ) as response:
                if response.status == 429:
                    raise RuntimeError("接口限流了（HTTP 429），过几分钟再试")
                if response.status == 404:
                    raise RuntimeError("接口地址不存在（HTTP 404），请检查配置里的 api")
                if response.status != 200:
                    raise RuntimeError(f"接口返回 HTTP {response.status}")
                data = await response.json(content_type=None)

            if cache_seconds > 0:
                CACHE[url] = (time.time() + cache_seconds, data)
            return data

        except asyncio.TimeoutError:
            last_error = f"请求超时（{timeout:.0f} 秒）"
        except aiohttp.ClientError as exc:
            last_error = f"网络请求失败：{exc}"
        except ValueError as exc:
            last_error = f"接口返回内容无法解析：{exc}"

        logger.warning("[tool_exe] 请求 %s 第 %s/%s 次失败：%s", url, attempt, retries, last_error)
        if attempt < retries:
            await asyncio.sleep(0.8 * attempt)

    raise RuntimeError(last_error)
