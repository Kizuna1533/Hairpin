# @Author: South
# @Date: 2021-08-18 10:51
import json
import random
import re

from nonebot import get_driver
from nonebot.adapters import Bot, Event
from nonebot.adapters.cqhttp import MessageSegment
from nonebot.plugin import on_regex
from nonebot.typing import T_State

global_config = get_driver().config
__PROJECT_ROOT__ = global_config.project_root

_day_limit = 5

rx = r"^(今天|[早中午晚][上饭餐午]|夜宵|睡前" \
     r")吃(什么|啥|点啥)"
eat_program_on = on_regex(rx, priority=3)

eat_tmp = {}

food_list = json.loads(open("./src/plugins/eat/foods.json").read())


@eat_program_on.handle()
async def live_subscription(bot: Bot, event: Event, state: T_State):
    user_id = str(event.get_user_id())
    if user_id not in eat_tmp.keys():
        eat_tmp[user_id] = 1
    else:
        eat_tmp[user_id] += 1
    if eat_tmp[user_id] >= _day_limit:
        await eat_program_on.finish(MessageSegment.at(event.get_user_id()) + "吃挺多啊你")
    else:
        res = re.match(rx, str(event.get_message()))
        time = res.group(1)
        print(time)
        food_name = food_list[str(random.randint(0, len(food_list) - 1))]["name"]
        to_eat = f'{time}去吃{food_name}吧~'
        message = MessageSegment.at(event.get_user_id()) + to_eat + MessageSegment.image(
            f"file:///{__PROJECT_ROOT__}/Hairpin/src/plugins/eat/foods/{food_name}.jpg")
        await eat_program_on.finish(message)
