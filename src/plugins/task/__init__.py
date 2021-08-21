import time

import nonebot
from nonebot import get_driver, on_command, logger
from nonebot.adapters import Bot, Event
from nonebot.adapters.cqhttp import GroupMessageEvent, PrivateMessageEvent
from nonebot.exception import ActionFailed
from nonebot.permission import SUPERUSER
from nonebot.typing import T_State
from nonebot_plugin_apscheduler import scheduler

from src.utils.database import Task_Subscription
from src.utils.general import is_number
from .config import Config

global_config = get_driver().config
config = Config(**global_config.dict())
__BOT_ID__ = global_config.bot_id

task_program_on = on_command("开启任务提醒", priority=3, permission=SUPERUSER)


@task_program_on.handle()
async def task_program_receive(bot: Bot, event: Event, state: T_State):
    args = str(event.get_message()).strip()
    if args:
        state["content"] = args


@task_program_on.got("content", prompt="请输入提醒内容，格式为间隔时间 内容，两者以空格隔开")
async def task_program_got(bot: Bot, event: GroupMessageEvent, state: T_State):
    res = str(state["content"]).split(' ')
    print(res)
    if is_number(res[0]):
        interval_time = int(res[0])
        content = res[1]
        task_subscription = Task_Subscription(bot_id=bot.self_id, subscriber_id=str(event.group_id),
                                              interval_time=interval_time, content=content,
                                              send_type=event.message_type)
        result = await task_subscription.insert()
        await task_program_on.finish(str(result.info))
    else:
        await task_program_on.finish("请检查格式正确与否！")


@task_program_on.got("content", prompt="请输入提醒内容，格式为间隔时间 内容，两者以空格隔开")
async def task_program_got(bot: Bot, event: PrivateMessageEvent, state: T_State):
    res = str(state["content"]).split(' ')
    if is_number(res[0]):
        interval_time = int(res[0])
        content = res[1]
        task_subscription = Task_Subscription(bot_id=bot.self_id, subscriber_id=str(event.user_id),
                                              interval_time=interval_time, content=content,
                                              send_type=event.message_type)
        result = await task_subscription.insert()
        await task_program_on.finish(str(result.info))
    else:
        await task_program_on.finish("请检查格式正确与否！")


task_program_off = on_command("删除任务提醒", priority=3, permission=SUPERUSER)


@task_program_off.handle()
async def task_program_receive(bot: Bot, event: Event, state: T_State):
    task_subscription = Task_Subscription(bot_id=bot.self_id, subscriber_id=event.group_id, interval_time=0,
                                          content="", send_type="")
    task_result = await task_subscription.select_all_by_self()
    task_tmp = ""
    for task in task_result.result:
        task_tmp += "\nid: %s interval_time: %s  content:%s" % (task.id, task.interval_time, task.content)
    args = str(event.get_message()).strip()
    if args:
        task_id = str(args)
        print(task_id, type(task_id))
        if is_number(task_id):
            task_subscription.id = task_id
            delete_result = await task_subscription.delete()
            await task_program_on.finish(str(delete_result.result))
        else:
            await task_program_on.reject("请检查格式正确与否！")
    else:
        await task_program_off.reject("请输入：删除任务提醒 要删除的任务id" + str(task_tmp))


@scheduler.scheduled_job("interval", seconds=1, id="task_push")
async def task_push():
    print(1)
    task_subscription = Task_Subscription(bot_id="", subscriber_id="", interval_time=0, content="", send_type="")
    task_all = await task_subscription.select_all()
    for task in task_all.result:
        print("-" * 90)
        print(task.content, task.interval_time, int(time.time() % task.interval_time))
        if int(time.time() % task.interval_time) == 0:
            try:
                bot = nonebot.get_bots()[str(task.bot_id)]
            except KeyError:
                logger.error(f"推送失败，Bot（{task.bot_id}）未连接")
                return
            if task.send_type == "private":
                send_id = "user_id"
            else:
                send_id = "group_id"
            try:
                await bot.call_api("send_" + task.send_type + "_msg", **{
                    "message": task.content,
                    send_id: task.subscriber_id
                })
            except ActionFailed as e:
                print(e)
