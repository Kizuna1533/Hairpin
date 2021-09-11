import asyncio
import threading

from bilibili_api import live
from nonebot import get_driver

from src.utils.general import bot_send
from .config import Config

global_config = get_driver().config
config = Config(**global_config.dict())
__BOT_ID = str(global_config.bot_id)
__CAPTAIN_GROUP_ID = str(global_config.captain_group_id)

room = live.LiveDanmaku(4611671)


@room.on("GUARD_BUY")
async def on_all(event):
    data = event["data"]["data"]
    message = "感谢 uid 为 %s 的 %s 老板的 %s 个月 %s ！\n 老板大气老板身体健康老板坐牢必减刑绝症有医保火化必爆舍利子！" % (
        data["uid"], data["num"], data["username"], data["gift_name"])
    print(message)
    await bot_send(__BOT_ID, __CAPTAIN_GROUP_ID, "group", message)


async def room_connect():
    await room.connect()


t = threading.Thread(target=asyncio.run, args=(room_connect(),))
t.start()
