import base64
import re

import httpx
from nonebot import get_driver
from nonebot.adapters import Bot, Event
from nonebot.adapters.cqhttp import GROUP_ADMIN, GROUP_OWNER, MessageSegment
from nonebot.permission import SUPERUSER
from nonebot.plugin import on_regex
from nonebot.typing import T_State

from src.utils.database import Alert
from src.utils.general import is_number

global_config = get_driver().config

alert_program = on_regex(r"^(警告)(.*)", priority=3, permission=SUPERUSER | GROUP_ADMIN | GROUP_OWNER)


@alert_program.handle()
async def eat_program_receive(bot: Bot, event: Event, state: T_State):
    args = str(event.get_message()).strip()
    if args:
        state["content"] = args


@alert_program.got("content", prompt="输入：警告 @qq 内容截图")
async def eat_program_got(bot: Bot, event: Event, state: T_State):
    alert_id = ""
    image = ""
    raw_image = ""
    try:
        alert_id = str(state["content"]).split(' ')[1]
        alert_id = re.findall(r'\d+', alert_id)[0]
        if not is_number(alert_id):
            await alert_program.reject("qq号格式错误")
        raw_image = str(state["content"]).split(' ')[2]
        image = re.findall(r'.*?file=(.*?\.image)', raw_image)[0]
        url = await bot.get_image(file=image)
        content = httpx.get(url=url["url"]).content
        image = base64.b64encode(content)
    except Exception as e:
        print(e)
        await alert_program.reject("格式错误，输入：警告 @qq 内容截图")
    print(alert_id, raw_image)
    alert = Alert(alert_id=alert_id, content=image)
    insert_result = await alert.insert()
    select_all_result = await alert.select_all()
    print(select_all_result.result)
    if len(select_all_result.result) >= 3:
        await alert_program.finish("可以踢了")
    elif insert_result.result == 1:
        await alert_program.finish(f"已收录，qq：{alert_id}，原因：" + MessageSegment.image(
            f"base64://{image.decode()}"))
