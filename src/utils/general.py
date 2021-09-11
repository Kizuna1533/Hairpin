from collections import defaultdict
from datetime import datetime, timedelta
from enum import unique, Enum

import nonebot
import pytz
from nonebot import logger
from nonebot.exception import ActionFailed


@unique
class send_id(Enum):
    private = "user_id"
    group = "group_id"


def is_number(x):
    try:
        x = int(x)
        return isinstance(x, int)
    except ValueError:
        return False


class DailyNumberLimiter:
    tz = pytz.timezone('Asia/Shanghai')

    def __init__(self, max_num):
        self.today = -1
        self.count = defaultdict(int)
        self.max = max_num

    def check(self, key) -> bool:
        now = datetime.now(self.tz)
        day = (now - timedelta(hours=5)).day
        if day != self.today:
            self.today = day
            self.count.clear()
        return bool(self.count[key] < self.max)

    def get_num(self, key):
        return self.count[key]

    def increase(self, key, num=1):
        self.count[key] += num

    def reset(self, key):
        self.count[key] = 0


async def bot_send(bot_id, target_id, send_type, message):
    try:
        bot = nonebot.get_bots()[str(bot_id)]
    except KeyError:
        logger.error(f"推送失败，Bot（{bot_id}）未连接")
        return
    try:
        await bot.call_api("send_" + send_type + "_msg", **{
            "message": message,
            send_id[send_type].value: target_id
        })
    except ActionFailed as e:
        print(e)
