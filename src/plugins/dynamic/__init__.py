# @Author: South
# @Date: 2021-08-14 10:56
import nonebot
from nonebot import get_driver, on_command
from nonebot.adapters import Bot, Event
from nonebot.typing import T_State
from nonebot_plugin_apscheduler import scheduler

from src.plugins.dynamic.data_source import get_dynamic_list, get_dynamics_screenshot, dynamic_url
from .config import Config
from .model import Dynamic_Subscription, Dynamic_Record

global_config = get_driver().config
config = Config(**global_config.dict())
__BOT_ID = str(global_config.bot_id)

dynamic_program_on = on_command("开启动态推送", priority=3)
test = on_command("test", priority=3)


@test.handle()
async def test(bot: Bot, event: Event, state: T_State):
    args = str(event.get_message()).strip()


@dynamic_program_on.handle()
async def dynamic_receive(bot: Bot, event: Event, state: T_State):
    args = str(event.get_message()).strip()
    if args:
        state["uid"] = args


@dynamic_program_on.got("uid", prompt="请输入要订阅的B站用户的UID")
async def dynamic_subscription(bot: Bot, event: Event, state: T_State):
    if event.message_type == "group":
        dynamic_subscription = Dynamic_Subscription(uid=state["uid"], subscriber_id=event.group_id, mold=2)
        result = await dynamic_subscription.insert()
        await dynamic_program_on.finish(str(result.info))
    elif event.message_type == "private":
        dynamic_subscription = Dynamic_Subscription(uid=state["uid"], subscriber_id=event.user_id, mold=1)
        result = await dynamic_subscription.insert()
        await dynamic_program_on.finish(str(result.info))


async def dynamic_push(subscribers, dynamic_id, image):
    bot = nonebot.get_bots()[__BOT_ID]
    # message = f"https://t.bilibili.com/{dynamic_id}?tab=2 \n" + MessageSegment.image(f"base64://{image}")
    # message = MessageSegment.image(f"base64://{image}")
    message = "1"
    for subscriber in subscribers:
        if subscriber.mold == 1:
            send_type = "private"
            send_id = "user_id"
        else:
            send_type = "group"
            send_id = "group_id"
        print(send_id, send_type, subscriber.subscriber_id)
        print(type(send_id), type(send_type), type(subscriber.subscriber_id))
        # try:
        #     return await bot.call_api("send_" + send_type + "_msg", **{
        #         "message": subscriber.subscriber_id,
        #         "group_id": subscriber.subscriber_id
        #     })
        # except ActionFailed as e:
        #     print(e)


@scheduler.scheduled_job("interval", seconds=10, id="dynamic_push")
async def dynamic_spider():
    # 初始化实例
    dynamic_subscription = Dynamic_Subscription(uid="0", subscriber_id="0", mold=0)
    # 数据库取全部uids
    uids = await dynamic_subscription.select_uids()
    # 遍历uids
    if len(uids.result) > 0:
        for uid in uids.result:
            # 取实例赋值uid
            dynamic_subscription.uid = uid
            # 依据已有uid从数据库取订阅用户
            subscribers = await dynamic_subscription.select_subscribers()
            # 根据uid实例化动态记录表
            dynamic_record = Dynamic_Record(uid)
            # 取当前uid的最后一条动态id
            db_last_dynamic_result = await dynamic_record.select_last_dynamic_id()
            print(uid, db_last_dynamic_result)
            # 爬虫获取动态
            dynamic_result = await get_dynamic_list(uid)
            # 当动态有内容
            if len(dynamic_result["dynamic_list"]) > 0:
                # 选第一条
                last_dynamic_id = str(dynamic_result["dynamic_list"][0])
                # 当数据库中没有动态时
                if not db_last_dynamic_result.error and db_last_dynamic_result.result == 1:
                    # 获取图片
                    image = await get_dynamics_screenshot(last_dynamic_id)
                    # 插入数据库
                    await dynamic_record.insert(last_dynamic_id, image.encode())
                    # 发送
                    await dynamic_push(subscribers.result, last_dynamic_id, image)
                elif not db_last_dynamic_result.error and db_last_dynamic_result.result != last_dynamic_id:
                    # 动态临时组
                    tmp = []
                    flag = True
                    while flag:
                        # 遍历动态到数据库中存在的那条为止
                        for dynamic_id in dynamic_result["dynamic_list"]:
                            print(db_last_dynamic_result.result, dynamic_id,
                                  db_last_dynamic_result.result == dynamic_id,
                                  flag)
                            if db_last_dynamic_result.result == str(dynamic_id):
                                flag = False
                                break
                            else:
                                tmp.append(dynamic_id)
                            if flag:
                                dynamic_result = await get_dynamic_list(uid, dynamic_result["next_offset"])
                    # 遍历临时组中的动态
                    for dynamic_id in tmp:
                        image = await get_dynamics_screenshot(dynamic_id)
                        await dynamic_record.insert(dynamic_id, image.encode())
                        await dynamic_push(subscribers.result, dynamic_id, image)
