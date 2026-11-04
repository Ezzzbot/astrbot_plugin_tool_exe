# 大头的工具箱

一个 AstrBot 工具箱插件。`main.py` 管入口，`tools/` 下一个文件一个功能，`_conf_schema.json` 管配置。
指令触发和 LLM 触发都调用同一批函数，加功能只要新建一个文件。

## 功能

| 指令 | 别名 | 说明 |
| --- | --- | --- |
| `/今日新闻 [条数]` | `60s`、`新闻60秒`、`看世界` | 60 秒读懂世界每日新闻速览 |
| `/工具箱` | `toolbox`、`功能列表` | 列出当前可用功能 |

```
/今日新闻        # 输出当天全部新闻
/今日新闻 5      # 只看前 5 条
60s 3           # 别名 + 条数
```

除了指令，直接对 Bot 说「今天有什么新闻」也行，LLM 会调用 `get_daily_news` 工具，走的是同一套逻辑。

## 效果

```
/今日新闻

📰 今日新闻 | 2026-11-04 · 星期三
丙午年九月廿六

1. 中国气象局确认：最强厄尔尼诺将明显影响我国……
2. 央行宣布 11 月 15 日起上调金融机构外汇存款准备金率……
3. A 股融资余额降至 2.30 万亿元……

💡 生活总有起落得失，稳住内心的节奏，向阳而行自有光亮
🔗 https://mp.weixin.qq.com/s?...
```

发送形式可切换：纯文本（默认）、当日长图、文字配图。

## 安装

1. AstrBot WebUI → 插件 → 安装插件，填入本仓库地址；
2. 依赖 `aiohttp` 会按 `requirements.txt` 自动安装；
3. 装好后在插件配置页按需调整参数（不配也能直接用）。

手动安装：把整个目录放进 `AstrBot/data/plugins/`，重启 AstrBot 或点插件页的重载按钮。

## 文件结构

```
astrbot_plugin_tool_exe/
├── main.py                 # 插件入口：指令触发 + LLM 触发 + 发消息
├── tools/                  # 功能模块，一个文件一个功能
│   ├── news.py             # 今日新闻
│   ├── utils.py            # 公共小工具（网络请求、缓存、连接池关闭）
│   └── __init__.py
├── _conf_schema.json       # WebUI 配置（面向用户，只有三项）
├── config.yaml             # 开发者配置（网络参数、展示细节）
├── metadata.yaml           # 插件信息
└── requirements.txt        # 第三方依赖（aiohttp、PyYAML）
```

分工只有两条：

- `tools/xxx.py`：普通函数，收参数、干活、返回结果，不碰 AstrBot 的类；
- `main.py`：用装饰器声明触发方式，读配置、调 `tools/` 里的函数、把结果发出去。

以后要加图片、日志之类的功能，就在 `tools/` 里新建 `image.py`、`log.py`，写法照 `news.py`。

## 配置

配置分两层，各管各的。

**WebUI 插件配置页**（`_conf_schema.json`，面向普通用户，只有三项）：

| 配置项 | 说明 |
| --- | --- |
| 启用该功能 | 今日新闻的开关 |
| 接口地址 | 默认 60s API，一般不用改 |
| 发送形式 | 纯文本 / 长图 / 图文一起发 |

**根目录 `config.yaml`**（面向开发者，改完在插件页点重载即可生效）：

| 配置项 | 默认值 | 说明 |
| --- | --- | --- |
| `network.timeout` | 10 | 单次请求超时（秒），所有功能共用 |
| `network.retries` | 2 | 失败重试次数，只有网络错误和超时才重试 |
| `network.proxy` | 空 | HTTP 代理，如 `http://127.0.0.1:7890` |
| `news60s.cache_seconds` | 600 | 数据缓存时长（秒），0 表示不缓存 |
| `news60s.show_meta` | true | 显示日期 / 星期 / 农历 |
| `news60s.show_tip` | true | 显示每日微语 |
| `news60s.show_link` | true | 显示原文链接 |
| `news60s.footer` | 空 | 自定义落款 |

合并顺序是：`config.yaml` 的 `network` → `config.yaml` 的功能段 → WebUI 里的功能段，后面的覆盖前面的。所以两处都有的配置项以 WebUI 为准，而 WebUI 里没有的项由 `config.yaml` 提供，文件删了也能跑（代码里有兜底默认值）。

## 新增一个功能

**第一步**，在 `tools/` 下新建文件，写函数：

```python
# tools/ip.py
from .utils import fetch_json


async def get_ip_info(options: dict) -> str:
    data = await fetch_json(options.get("api"), options)
    return f"当前出口 IP：{data.get('ip')}"
```

**第二步**，在 `main.py` 里加一个方法把它调起来：

```python
from .tools import ip

@filter.command("查IP")
async def cmd_ip(self, event: AstrMessageEvent):
    """查询出口 IP"""
    try:
        yield event.plain_result(await ip.get_ip_info(self._options("ipinfo")))
    except Exception as exc:
        yield event.plain_result(f"查询失败：{exc}")
```

想让 LLM 也能调用，就再加一个方法，调同一个函数：

```python
@filter.llm_tool(name="get_ip_info")
async def llm_ip(self, event: AstrMessageEvent):
    """查询出口 IP 地址。当用户问「我的 IP 是多少」时调用。"""
    yield event.plain_result(await ip.get_ip_info(self._options("ipinfo")))
```

**第三步**（可选），要新配置项时按面向谁来决定放哪：
- 普通用户需要改的 → 加在 `_conf_schema.json` 的功能段里；
- 只有开发者调的（网络参数、缓存、排版开关）→ 加在 `config.yaml` 的同名段里。

两处都读得到，`main.py` 里统一用 `self._options("段名")` 取，不用关心它来自哪个文件。

## 常见问题

**提示「接口限流了（HTTP 429）」**
新闻接口对短时间内的重复请求有限制。插件默认缓存 10 分钟，一般不会触发；如果碰到，等几分钟或把配置里的缓存时长调大。

**群里一直没反应**
先确认插件的「今日新闻」开关是开的（`/工具箱` 能看到就说明功能已启用），再看 AstrBot 日志里有没有 `[tool_exe]` 开头的报错。

**图片发不出去**
部分平台对超长图支持不好，把发送形式改回「纯文本」即可。

**访问接口慢或失败**
在配置里填 HTTP 代理，形如 `http://127.0.0.1:7890`，插件的所有请求都会走它。

## 数据来源

- 每日新闻：[60s API](https://github.com/vikiboss/60s)（作者 vikiboss）

## License

MIT，详见 [LICENSE](./LICENSE)。
