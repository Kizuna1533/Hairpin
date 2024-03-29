from random import randint

from nonebot import get_driver
from nonebot.adapters.cqhttp import Event, Bot
from nonebot.plugin import on_regex
from nonebot.typing import T_State

from .config import Config

global_config = get_driver().config
config = Config(**global_config.dict())
PROJECT_ROOT = global_config.project_root
AMF_ID = global_config.amf_id

listen_other = on_regex(r".*?", priority=5)

tmp = ""
count = 0


@listen_other.handle()
async def listen_receive(bot: Bot, event: Event, state: T_State):
    global tmp
    global count
    flag = False
    # if event.get_user_id() == str(AMF_ID) and randint(0, 100) <= 0:
    #     message = MessageSegment.reply(int(event.message_id)) + MessageSegment.image(f"file:///{PROJECT_ROOT}/WhereCard.png")
    #     await listen_other.send(message)
    if randint(0, 200) <= 1:
        flag = True
    if event.get_message() == tmp:
        count += 1
    else:
        tmp = event.get_message()

    if count == 4:
        flag = True

    if flag:
        await listen_other.send(event.get_message())
