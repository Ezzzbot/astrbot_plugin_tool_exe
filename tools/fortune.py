"""今日运势：纯本地计算，不联网、不调用任何接口。

原理只有一句话：拿「用户 ID + 日期」做哈希，再用哈希值去各个词库里取词。
同一个人的同一天，结果永远一样；换个人或换一天，结果就完全不同。

词库放在文件顶部，想改文案直接改列表就行，不用动下面的代码。
"""

from __future__ import annotations

import hashlib
from datetime import datetime

# ---------------------------------------------------------------- 词库

# 运势等级，重复出现的次数就是出现概率：大吉和大凶各 1 份，小吉和平各 3 份
LEVELS = [
    "大吉",
    "中吉", "中吉",
    "小吉", "小吉", "小吉",
    "平", "平", "平",
    "小凶", "小凶",
    "大凶",
]

# 每个等级对应的分数区间，让分数和等级对得上，不会出现「大凶 98 分」
SCORE_RANGE = {
    "大吉": (90, 99),
    "中吉": (82, 89),
    "小吉": (74, 81),
    "平": (65, 73),
    "小凶": (55, 64),
    "大凶": (40, 54),
}

STARS = {"大吉": 5, "中吉": 4, "小吉": 3, "平": 2, "小凶": 1, "大凶": 1}

NUMBERS = [str(n) for n in range(1, 10)]

COLORS = [
    "石榴红", "落日橙", "蜜蜡黄", "苔藓绿", "雾霾蓝", "紫罗兰", "墨黑",
    "素白", "焦糖棕", "樱花粉", "抹茶绿", "深海蓝", "燕麦色", "月光白",
]

HOURS = ["清晨", "上午", "午后", "傍晚", "深夜"]

GOOD = [
    "早睡早起", "清理桌面", "给自己泡杯茶", "把拖了三天的事做掉", "整理相册",
    "和很久没联系的朋友说句话", "把手机调成静音", "吃点好的", "出门走走",
    "删掉一个没用的群", "认真吃早饭", "夸别人一句", "把待办写下来",
    "听一张完整的专辑", "给绿植浇水", "提前十分钟出门", "拒绝一个不想去的局",
    "看完一部老电影", "把 Plan B 想好", "收拾衣柜", "洗个热水澡",
    "给自己买朵花", "发一条不设置分组的动态", "在窗边晒十分钟太阳",
]

BAD = [
    "半夜立 flag", "跟领导讲道理", "把话说太满", "凌晨看购物车",
    "用「随便」回答吃什么", "翻前任朋友圈", "在群里发长语音", "空腹喝冰美式",
    "临时改需求", "借钱给同事", "深夜发消息", "赌气做决定",
    "把密码设成生日", "边走路边看手机", "相信「最后一单」", "在评论区争论",
    "把希望寄托在别人身上", "答应临时加塞的事", "连续刷三小时短视频", "抄底",
]

TIPS = [
    "今天的运气藏在别人懒得做的事里",
    "你比你以为的更能扛",
    "慢一点没关系，方向对了就行",
    "会有人悄悄记住你的好",
    "别急着证明自己",
    "把手头这一件做漂亮就够了",
    "情绪上头的时候先别开口",
    "该来的都在路上",
    "今天适合当个普通人",
    "你担心的那件事，有八成像不会发生",
    "累就歇，别硬撑",
    "别人怎么看你不影响你吃饭",
    "有些答案要等风来",
    "把注意力放回自己身上",
    "你已经比上个月熟练了",
    "开心不需要理由，也不需要许可",
    "走在路上记得抬头看看天",
    "不回复也是一种回复",
    "能做到的事别拖到明天",
    "今天的饭要好好吃",
]

WEEKDAYS = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]


# ---------------------------------------------------------------- 计算


def _index(seed: str, salt: str, size: int) -> int:
    """把 seed 和用途拼起来做哈希，再对词库长度取模，得到一个下标。

    加盐（salt）是为了让「等级」「分数」这些维度互不干扰，
    否则同一个哈希值取模会在所有维度上产生关联。
    """
    digest = hashlib.md5(f"{seed}:{salt}".encode("utf-8")).hexdigest()
    return int(digest[:8], 16) % size


def get_fortune(user_id: str, name: str = "", date: str | None = None) -> str:
    """算出某个用户某天的运势，返回排好版的文本。

    user_id 用平台返回的发送者 ID（QQ 号等），date 不传就用今天。
    同一个 (user_id, date) 永远得到同一份结果。
    """
    if date is None:
        date = datetime.now().strftime("%Y-%m-%d")

    # 种子只跟「谁」和「哪天」有关，所以换群、换设备结果都不变
    seed = f"{user_id}:{date}"

    level = LEVELS[_index(seed, "level", len(LEVELS))]
    low, high = SCORE_RANGE[level]
    score = low + _index(seed, "score", high - low + 1)

    number = NUMBERS[_index(seed, "number", len(NUMBERS))]
    color = COLORS[_index(seed, "color", len(COLORS))]
    hour = HOURS[_index(seed, "hour", len(HOURS))]
    tip = TIPS[_index(seed, "tip", len(TIPS))]

    good = GOOD[_index(seed, "good", len(GOOD))]
    bad = BAD[_index(seed, "bad", len(BAD))]
    if bad == good:  # 理论上两个词库不重叠，这里只是保险
        bad = BAD[(_index(seed, "bad", len(BAD)) + 1) % len(BAD)]

    # ------------------------------------------------------------ 排版
    weekday = WEEKDAYS[datetime.strptime(date, "%Y-%m-%d").weekday()]
    lines = [f"🔮 今日运势 · {date} {weekday}", ""]

    if name.strip():
        lines.append(f"  {name.strip()}")

    lines.extend([
        f"  ⭐ {level} · {score} 分  {'★' * STARS[level]}{'☆' * (5 - STARS[level])}",
        "",
        f"  🔢 幸运数字  {number}",
        f"  🎨 幸运颜色  {color}",
        f"  🕐 幸运时段  {hour}",
        "",
        f"  ✅ 宜  {good}",
        f"  ❌ 忌  {bad}",
        "",
        f"  💬 {tip}",
        "",
        "  · 仅供娱乐 ·",
    ])
    return "\n".join(lines)
