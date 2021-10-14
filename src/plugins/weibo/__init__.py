# @Author: South
# @Date: 2021-10-14 20:12
import nonebot
from nonebot import get_driver, on_command, logger
from nonebot.adapters import Bot, Event
from nonebot.adapters.cqhttp import MessageSegment, PrivateMessageEvent, GroupMessageEvent
from nonebot.exception import ActionFailed
from nonebot.permission import SUPERUSER
from nonebot.typing import T_State
from nonebot_plugin_apscheduler import scheduler

from src.utils.database import Weibo_Subscription, Weibo_Record
from .config import Config
from .data_source import get_weibo_list, get_weibo_screenshot, weibo_url

global_config = get_driver().config
config = Config(**global_config.dict())
__BOT_ID = str(global_config.bot_id)

weibo_program_on = on_command("开启微博推送", priority=3, permission=SUPERUSER)


@weibo_program_on.handle()
async def weibo_program_receive(bot: Bot, event: Event, state: T_State):
    args = str(event.get_message()).strip()
    print(args)
    if args:
        state["uid"] = args


@weibo_program_on.got("uid", prompt="请输入要订阅的微博的UID")
async def weibo_program_got(bot: Bot, event: GroupMessageEvent, state: T_State):
    weibo_subscription = Weibo_Subscription(bot_id=bot.self_id, uid=state["uid"], subscriber_id=str(event.group_id),
                                            send_type=event.message_type)
    result = await weibo_subscription.insert()
    await weibo_program_on.finish(str(result.info))


@weibo_program_on.got("uid", prompt="请输入要订阅的微博的UID")
async def weibo_program_got(bot: Bot, event: PrivateMessageEvent, state: T_State):
    weibo_subscription = Weibo_Subscription(bot_id=bot.self_id, uid=state["uid"], subscriber_id=str(event.user_id),
                                            send_type=event.message_type)
    result = await weibo_subscription.insert()
    await weibo_program_on.finish(str(result.info))


weibo_program_off = on_command("关闭微博推送", priority=3, permission=SUPERUSER)


@weibo_program_off.handle()
async def weibo_program_receive(bot: Bot, event: Event, state: T_State):
    args = str(event.get_message()).strip()
    print(args)
    if args:
        state["uid"] = args


@weibo_program_off.got("uid", prompt="请输入要关闭订阅的微博的UID")
async def weibo_program_got(bot: Bot, event: GroupMessageEvent, state: T_State):
    weibo_subscription = Weibo_Subscription(bot_id=bot.self_id, uid=state["uid"], subscriber_id=str(event.group_id),
                                            send_type=event.message_type)
    result = await weibo_subscription.delete()
    await weibo_program_off.finish(str(result.info))


@weibo_program_off.got("uid", prompt="请输入要关闭订阅的微博的UID")
async def weibo_program_got(bot: Bot, event: PrivateMessageEvent, state: T_State):
    weibo_subscription = Weibo_Subscription(bot_id=bot.self_id, uid=state["uid"], subscriber_id=str(event.user_id),
                                            send_type=event.message_type)
    result = await weibo_subscription.delete()
    await weibo_program_off.finish(str(result.info))


async def weibo_push(subscribers, weibo_id, image):
    for subscriber in subscribers:
        message = f"https://weibo.com/{subscriber.uid}/{weibo_id} \n" + MessageSegment.image(f"base64://{image}")
        try:
            bot = nonebot.get_bots()[str(subscriber.bot_id)]
        except KeyError:
            logger.error(f"推送失败，Bot（{subscriber.bot_id}）未连接")
            return
        if subscriber.send_type == "private":
            send_id = "user_id"
        else:
            send_id = "group_id"
        try:
            await bot.call_api("send_" + subscriber.send_type + "_msg", **{
                "message": message,
                send_id: subscriber.subscriber_id
            })
        except ActionFailed as e:
            print(e)


@scheduler.scheduled_job("interval", seconds=10, id="weibo_push", max_instances=3)
async def weibo_spider():
    # 初始化实例
    weibo_subscription = Weibo_Subscription(bot_id="0", uid="0", subscriber_id="0", send_type="")
    # 数据库取全部uids
    uids = await weibo_subscription.select_uids()
    # 遍历uids
    if len(uids.result) > 0:
        for uid in uids.result:
            # 取实例赋值uid
            weibo_subscription.uid = uid
            # 根据uid实例化微博记录表
            weibo_record = Weibo_Record(uid)
            # 取当前uid的最后一条微博id
            db_last_weibo_result = await weibo_record.select_last_weibo_id()
            # 爬虫获取微博
            weibo_result = await get_weibo_list(uid)
            # 当微博有内容
            if len(weibo_result["weibo_list"]) > 0:
                # 选第一条
                last_weibo_id = str(weibo_result["weibo_list"][0])

                if not db_last_weibo_result.error:
                    # 依据已有uid从数据库取订阅用户
                    subscribers = await weibo_subscription.select_subscribers()
                    # 当数据库中没有微博时
                    if db_last_weibo_result.result == 1:
                        # 获取图片
                        image = await get_weibo_screenshot(last_weibo_id)
                        # 插入数据库
                        await weibo_record.insert(last_weibo_id, image.encode())
                        # 发送
                        await weibo_push(subscribers.result, last_weibo_id, image)
                    elif db_last_weibo_result.result < last_weibo_id:
                        # 微博临时组
                        tmp = []
                        flag = True
                        while flag:
                            # 遍历微博到数据库中存在的那条为止
                            for weibo_id in weibo_result["weibo_list"]:
                                print(db_last_weibo_result.result, weibo_id,
                                      db_last_weibo_result.result == weibo_id,
                                      flag)
                                if db_last_weibo_result.result >= str(weibo_id):
                                    flag = False
                                    break
                                else:
                                    tmp.append(weibo_id)
                                if flag:
                                    weibo_result = await get_weibo_list(uid, weibo_result["next_offset"])
                        # 遍历临时组中的微博
                        tmp.sort()
                        for weibo_id in tmp:
                            image = await get_weibo_screenshot(weibo_id)
                            await weibo_record.insert(weibo_id, image.encode())
                            await weibo_push(subscribers.result, weibo_id, image)
