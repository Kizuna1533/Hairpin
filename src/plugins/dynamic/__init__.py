# @Author: South
# @Date: 2021-08-14 10:56
import nonebot
from nonebot import get_driver, on_command, logger
from nonebot.adapters import Bot, Event
from nonebot.adapters.cqhttp import MessageSegment, PrivateMessageEvent, GroupMessageEvent
from nonebot.exception import ActionFailed
from nonebot.permission import SUPERUSER
from nonebot.typing import T_State
from nonebot_plugin_apscheduler import scheduler

from src.utils.database import Dynamic_Subscription, Dynamic_Record
from .config import Config
from .data_source import get_dynamic_list, get_dynamics_screenshot, dynamic_url

global_config = get_driver().config
config = Config(**global_config.dict())
__BOT_ID = str(global_config.bot_id)

dynamic_program_on = on_command("开启动态推送", priority=3, permission=SUPERUSER)


@dynamic_program_on.handle()
async def dynamic_program_receive(bot: Bot, event: Event, state: T_State):
    args = str(event.get_message()).strip()
    print(args)
    if args:
        state["uid"] = args


@dynamic_program_on.got("uid", prompt="请输入要订阅的B站用户的UID")
async def dynamic_program_got(bot: Bot, event: GroupMessageEvent, state: T_State):
    dynamic_subscription = Dynamic_Subscription(bot_id=bot.self_id, uid=state["uid"], subscriber_id=str(event.group_id),
                                                send_type=event.message_type)
    result = await dynamic_subscription.insert()
    await dynamic_program_on.finish(str(result.info))


@dynamic_program_on.got("uid", prompt="请输入要订阅的B站用户的UID")
async def dynamic_program_got(bot: Bot, event: PrivateMessageEvent, state: T_State):
    dynamic_subscription = Dynamic_Subscription(bot_id=bot.self_id, uid=state["uid"], subscriber_id=str(event.user_id),
                                                send_type=event.message_type)
    result = await dynamic_subscription.insert()
    await dynamic_program_on.finish(str(result.info))


dynamic_program_off = on_command("关闭动态推送", priority=3, permission=SUPERUSER)


@dynamic_program_off.handle()
async def dynamic_program_receive(bot: Bot, event: Event, state: T_State):
    args = str(event.get_message()).strip()
    print(args)
    if args:
        state["uid"] = args


@dynamic_program_off.got("uid", prompt="请输入要关闭订阅的B站用户的UID")
async def dynamic_program_got(bot: Bot, event: GroupMessageEvent, state: T_State):
    dynamic_subscription = Dynamic_Subscription(bot_id=bot.self_id, uid=state["uid"], subscriber_id=str(event.group_id),
                                                send_type=event.message_type)
    result = await dynamic_subscription.delete()
    await dynamic_program_off.finish(str(result.info))


@dynamic_program_off.got("uid", prompt="请输入要关闭订阅的B站用户的UID")
async def dynamic_program_got(bot: Bot, event: PrivateMessageEvent, state: T_State):
    dynamic_subscription = Dynamic_Subscription(bot_id=bot.self_id, uid=state["uid"], subscriber_id=str(event.user_id),
                                                send_type=event.message_type)
    result = await dynamic_subscription.delete()
    await dynamic_program_off.finish(str(result.info))


async def dynamic_push(subscribers, dynamic_id, image):
    message = f"https://t.bilibili.com/{dynamic_id}?tab=2 \n" + MessageSegment.image(f"base64://{image}")
    for subscriber in subscribers:
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


@scheduler.scheduled_job("interval", seconds=10, id="dynamic_push", max_instances=3)
async def dynamic_spider():
    # 初始化实例
    dynamic_subscription = Dynamic_Subscription(bot_id="0", uid="0", subscriber_id="0", send_type="")
    # 数据库取全部uids
    uids = await dynamic_subscription.select_uids()
    # 遍历uids
    if len(uids.result) > 0:
        for uid in uids.result:
            # 取实例赋值uid
            dynamic_subscription.uid = uid
            # 根据uid实例化动态记录表
            dynamic_record = Dynamic_Record(uid)
            # 取当前uid的最后一条动态id
            db_last_dynamic_result = await dynamic_record.select_last_dynamic_id()
            # 爬虫获取动态
            dynamic_result = await get_dynamic_list(uid)
            # 当动态有内容
            if len(dynamic_result["dynamic_list"]) > 0:
                # 选第一条
                last_dynamic_id = str(dynamic_result["dynamic_list"][0])

                if not db_last_dynamic_result.error:
                    # 依据已有uid从数据库取订阅用户
                    subscribers = await dynamic_subscription.select_subscribers()
                    # 当数据库中没有动态时
                    if db_last_dynamic_result.result == 1:
                        # 获取图片
                        image = await get_dynamics_screenshot(last_dynamic_id)
                        # 插入数据库
                        await dynamic_record.insert(last_dynamic_id, image.encode())
                        # 发送
                        await dynamic_push(subscribers.result, last_dynamic_id, image)
                    elif db_last_dynamic_result.result < last_dynamic_id:
                        # 动态临时组
                        tmp = []
                        flag = True
                        while flag:
                            # 遍历动态到数据库中存在的那条为止
                            for dynamic_id in dynamic_result["dynamic_list"]:
                                print(db_last_dynamic_result.result, dynamic_id,
                                      db_last_dynamic_result.result == dynamic_id,
                                      flag)
                                if db_last_dynamic_result.result >= str(dynamic_id):
                                    flag = False
                                    break
                                else:
                                    tmp.append(dynamic_id)
                                if flag:
                                    dynamic_result = await get_dynamic_list(uid, dynamic_result["next_offset"])
                        # 遍历临时组中的动态
                        tmp.sort()
                        for dynamic_id in tmp:
                            image = await get_dynamics_screenshot(dynamic_id)
                            await dynamic_record.insert(dynamic_id, image.encode())
                            await dynamic_push(subscribers.result, dynamic_id, image)
