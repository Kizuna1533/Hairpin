# @Author: South
# @Date: 2021-08-17 15:51
import nonebot
from nonebot import get_driver, on_command
from nonebot.adapters import Bot, Event
from nonebot.adapters.cqhttp import MessageSegment, ActionFailed
from nonebot.permission import SUPERUSER
from nonebot.typing import T_State
from nonebot_plugin_apscheduler import scheduler

from src.utils.database import Live_Subscription
from .config import Config
from .data_source import get_live_status_list

global_config = get_driver().config
config = Config(**global_config.dict())
__BOT_ID = str(global_config.bot_id)

live_program_on = on_command("开启直播推送", priority=3, permission=SUPERUSER)


@live_program_on.handle()
async def dynamic_receive(bot: Bot, event: Event, state: T_State):
    args = str(event.get_message()).strip()
    print(args)
    if args:
        state["uid"] = args


@live_program_on.got("uid", prompt="请输入要订阅的B站用户的UID")
async def dynamic_subscription(bot: Bot, event: Event, state: T_State):
    dynamic_subscription = Live_Subscription(uid=state["uid"], subscriber_id=event.group_id,
                                             send_type=event.message_type)
    result = await dynamic_subscription.insert()
    await live_program_on.finish(str(result.info))


async def live_push(subscribers, live_message):
    bot = nonebot.get_bots()[__BOT_ID]
    for subscriber in subscribers:
        if subscriber.send_type == "private":
            send_id = "user_id"
        else:
            send_id = "group_id"
        print('*' * 30)
        print(send_id, subscriber.send_type, subscriber.subscriber_id)
        print('*' * 30)
        try:
            await bot.call_api("send_" + subscriber.send_type + "_msg", **{
                "message": live_message,
                "group_id": subscriber.subscriber_id
            })
        except ActionFailed as e:
            print(e)


tmp_live_status = {}


@scheduler.scheduled_job("interval", seconds=10, id="live_push")
async def live_spider():
    # 初始化实例
    live_subscription = Live_Subscription(uid="0", subscriber_id="0", send_type="")
    # 数据库取全部uids
    uids = await live_subscription.select_uids()
    new_live_status_list = await get_live_status_list(uids.result)
    if not new_live_status_list:
        return
    for uid, info in new_live_status_list.items():
        print(uid, info['live_status'], tmp_live_status)
        new_status = 0 if info['live_status'] == 2 else info['live_status']
        if uid not in tmp_live_status:
            tmp_live_status[uid] = 0
            # continue
        old_status = tmp_live_status[uid]
        if new_status != old_status and new_status:  # 判断是否推送过
            room_id = info['short_id'] if info['short_id'] else info['room_id']
            url = 'https://live.bilibili.com/' + str(room_id)
            name = info['uname']
            title = info['title']
            cover = (info['cover_from_user'] if info['cover_from_user'] else info['keyframe'])
            live_message = (f"{name} 正在直播：\n{title}\n" + MessageSegment.image(cover) + f"\n{url}")
            live_subscription.uid = uid
            subscribers = await live_subscription.select_subscribers()
            print('-' * 60)
            print(subscribers.result)
            await live_push(subscribers.result, live_message)
        tmp_live_status[uid] = new_status
