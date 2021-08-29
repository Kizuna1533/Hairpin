# @Author: South
# @Date: 2021-08-18 10:51
import base64
import random
import re

import httpx
from nonebot import get_driver
from nonebot.adapters import Bot, Event
from nonebot.adapters.cqhttp import MessageSegment, GROUP_ADMIN, GROUP_OWNER
from nonebot.permission import SUPERUSER
from nonebot.plugin import on_regex, on_command
from nonebot.typing import T_State

from src.utils.database import Recipes
from src.utils.general import DailyNumberLimiter

global_config = get_driver().config
__PROJECT_ROOT__ = global_config.project_root

_day_limit = 3
_lmt = DailyNumberLimiter(_day_limit)

rx = r"^(今天|[早中午晚][上饭餐午]|夜宵|睡前)吃(什么|啥|点啥)"
eat_program_on = on_regex(rx, priority=3)


@eat_program_on.handle()
async def live_subscription(bot: Bot, event: Event, state: T_State):
    print("1" * 70)
    user_id = str(event.get_user_id())
    if not _lmt.check(user_id):
        await eat_program_on.finish(MessageSegment.at(event.get_user_id()) + "吃挺多啊你")
    else:
        _lmt.increase(user_id)
        res = re.match(rx, str(event.get_message()))
        time = res.group(1)
        recipes = await Recipes(name="", content="".encode()).select_all()
        if recipes.result:
            food = recipes.result[random.randint(0, len(recipes.result) - 1)]
            to_eat = f'{time}去吃{food.name}吧~\n'
            message = MessageSegment.at(event.get_user_id()) + to_eat + MessageSegment.image(
                f"base64://{food.content.decode()}")
            await eat_program_on.finish(message)


recipes_program = on_command("添加菜单", priority=3, permission=SUPERUSER | GROUP_ADMIN | GROUP_OWNER)


@recipes_program.handle()
async def eat_program_receive(bot: Bot, event: Event, state: T_State):
    args = str(event.get_message()).strip()
    if args:
        state["content"] = args


@recipes_program.got("content", prompt="输入：添加菜单 菜名 图片")
async def eat_program_got(bot: Bot, event: Event, state: T_State):
    name = str(state["content"]).split(' ')[0]
    message_image = re.findall(r'.*?file=(.*?\.image)', str(state["content"]).split(' ')[1])[0]
    url = await bot.get_image(file=message_image)
    content = httpx.get(url=url["url"]).content
    image = base64.b64encode(content)
    recipes = Recipes(name=name, content=image)
    result = await recipes.insert()
    if result.result == 1:
        await recipes_program.finish("添加成功")
