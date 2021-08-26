# @Author: South
# @Date: 2021-08-14 10:56
import nonebot
from nonebot import get_driver, on_command, on_notice
from nonebot.adapters import Bot, Event
from nonebot.adapters.cqhttp import GroupMessageEvent, MessageSegment, GroupIncreaseNoticeEvent
from nonebot.permission import SUPERUSER
from nonebot.typing import T_State

from src.utils.database import Welcome_Subscription

global_config = get_driver().config

welcome_dict = {}

welcome_program_on = on_command("开启入群欢迎", priority=3, permission=SUPERUSER)


@welcome_program_on.handle()
async def welcome_receive(bot: Bot, event: GroupMessageEvent, state: T_State):
    args = str(event.get_message()).strip()
    if args:
        state["content"] = args


@welcome_program_on.got("content", prompt="请输入欢迎内容")
async def welcome_subscription(bot: Bot, event: Event, state: T_State):
    dynamic_subscription = Welcome_Subscription(subscriber_id=event.group_id, status=True, content=state["content"])
    welcome_dict[event.group_id] = state["content"]
    result = await dynamic_subscription.insert()
    await welcome_program_on.finish(str(result.info))


welcome_program_notice = on_notice()


@welcome_program_notice.handle()
async def welcome_notice(bot: Bot, event: GroupIncreaseNoticeEvent, state: T_State):
    if event.notice_type == "group_increase" and str(event.group_id) in welcome_dict.keys():
        message = MessageSegment.at(event.get_user_id()) + welcome_dict[str(event.group_id)]
        await welcome_program_notice.send(message)


async def welcome_init():
    welcome_subscription = Welcome_Subscription(subscriber_id="", status=True, content="")
    welcome_subscribers = await welcome_subscription.select_subscribers()
    for welcome_subscriber in welcome_subscribers.result:
        welcome_dict[welcome_subscriber.subscriber_id] = welcome_subscriber.content


nonebot.get_driver().on_startup(welcome_init)
