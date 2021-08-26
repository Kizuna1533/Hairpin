# @Author: South
# @Date: 2021-08-14 10:56
from datetime import datetime

import nonebot
from sqlalchemy import Column, Integer, String, BLOB, DATETIME, select, distinct, func, Boolean, Text
from sqlalchemy.exc import NoResultFound, MultipleResultsFound
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from src.utils.result import Result

global_config = nonebot.get_driver().config
__PROJECT_ROOT__ = global_config.project_root
try:
    engine = create_async_engine(f"sqlite+aiosqlite:///{__PROJECT_ROOT__}/Hairpin.db", encoding="utf8",
                                 pool_recycle=3600, pool_pre_ping=True, echo=False, future=True)
except Exception as exp:
    import sys

    nonebot.logger.opt(colors=True).critical(f"<r>创建数据库连接失败</r>, error: {repr(exp)}")
    sys.exit("创建数据库连接失败")


async def database_init():
    try:
        # 初始化数据库结构
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        nonebot.logger.opt(colors=True).debug(f"<lc>初始化数据库...</lc><lg>完成</lg>")
    except Exception as e:
        import sys
        nonebot.logger.opt(colors=True).critical(f"<r>数据库初始化失败</r>, error: {repr(e)}")
        sys.exit("数据库初始化失败")


# 初始化化数据库
nonebot.get_driver().on_startup(database_init)
Base = declarative_base(engine)


class DB(object):
    def __init__(self):
        # expire_on_commit=False will prevent attributes from being expired
        # after commit.
        self.__async_session = sessionmaker(
            engine, expire_on_commit=False, class_=AsyncSession
        )

    def get_async_session(self):
        # 创建DBSession对象
        return self.__async_session


class Dynamic_Record(Base):
    __tablename__ = "Dynamic_Record"
    id = Column(Integer, nullable=False, primary_key=True, index=True, autoincrement=True)
    uid = Column(String(25), nullable=False, primary_key=False)
    dynamic_id = Column(String(25), nullable=False, primary_key=False)
    content = Column(BLOB, nullable=False, primary_key=False)
    time = Column(DATETIME, nullable=False, primary_key=False, default=datetime.now)

    def __init__(self, uid: str):
        self.uid = uid

    async def insert(self, dynamic_id: str, content: bytes, time=datetime.now()):
        self.dynamic_id = dynamic_id
        self.content = content
        self.time = time
        async_session = DB().get_async_session()
        async with async_session() as session:
            try:
                async with session.begin():
                    try:
                        result = await self.select(dynamic_id)
                        if not result.error and result.result == 1:
                            session.add(self)
                            result = Result.IntResult(error=False, info="Insert_Success", result=1)
                    except Exception as e:
                        result = Result.IntResult(error=True, info=repr(e), result=-1)
                await session.commit()
            except MultipleResultsFound:
                result = Result.IntResult(error=True, info="Multiple_Results_Found", result=-1)
            except Exception as e:
                result = Result.IntResult(error=True, info=repr(e), result=-1)
        return result

    async def select(self, dynamic_id: str):
        async_session = DB().get_async_session()
        async with async_session() as session:
            try:
                async with session.begin():
                    try:
                        session_result = await session.execute(select(Dynamic_Record).where(
                            Dynamic_Record.dynamic_id == dynamic_id))
                        record = session_result.scalar_one()
                        result = Result.IntResult(error=False, info="Exist", result=record)
                    except NoResultFound:
                        result = Result.IntResult(error=False, info="Select_No_Result", result=1)
            except MultipleResultsFound:
                result = Result.IntResult(error=True, info="Multiple_Results_Found", result=-1)
            except Exception as e:
                result = Result.IntResult(error=True, info=repr(e), result=-1)
        return result

    async def select_last_dynamic_id(self):
        async_session = DB().get_async_session()
        async with async_session() as session:
            try:
                async with session.begin():
                    try:
                        session_result = await session.execute(select(func.max(Dynamic_Record.dynamic_id)).where(
                            Dynamic_Record.uid == self.uid))
                        record = session_result.scalar_one()
                        if record:
                            result = Result.IntResult(error=False, info="Exist", result=record)
                        else:
                            result = Result.IntResult(error=False, info="Select_No_Result", result=1)
                    except NoResultFound:
                        result = Result.IntResult(error=False, info="Select_No_Result", result=1)
            except MultipleResultsFound:
                result = Result.IntResult(error=True, info="Multiple_Results_Found", result=-1)
            except Exception as e:
                result = Result.IntResult(error=True, info=repr(e), result=-1)
        return result


class Dynamic_Subscription(Base):
    __tablename__ = "Dynamic_Subscription"
    id = Column(Integer, nullable=False, primary_key=True, index=True, autoincrement=True)
    bot_id = Column(String(16), nullable=False, comment="Bot_id")
    uid = Column(String(16), nullable=False, comment="B站UID")
    subscriber_id = Column(String(16), nullable=False, comment="QQ/群号")
    send_type = Column(String(10), nullable=False, comment="私聊/群")

    def __init__(self, bot_id: str, uid: str, subscriber_id: str, send_type: str):
        self.bot_id = bot_id
        self.uid = uid
        self.subscriber_id = subscriber_id
        self.send_type = send_type

    async def insert(self):
        async_session = DB().get_async_session()
        async with async_session() as session:
            try:
                async with session.begin():
                    try:
                        result = await self.select()
                        if not result.error and result.result == 1:
                            session.add(self)
                            result = Result.IntResult(error=False, info="Insert_Success", result=1)
                    except Exception as e:
                        result = Result.IntResult(error=True, info=repr(e), result=-1)
                await session.commit()
            except MultipleResultsFound:
                result = Result.IntResult(error=True, info="Multiple_Results_Found", result=-1)
            except Exception as e:
                result = Result.IntResult(error=True, info=repr(e), result=-1)
        return result

    async def delete(self):
        async_session = DB().get_async_session()
        async with async_session() as session:
            try:
                async with session.begin():
                    try:
                        result = await self.select()
                        if not result.error and isinstance(result.result, Dynamic_Subscription):
                            await session.delete(result.result)
                            result = Result.IntResult(error=False, info="Delete_Success", result=1)
                    except Exception as e:
                        result = Result.IntResult(error=True, info=repr(e), result=-1)
                await session.commit()
            except MultipleResultsFound:
                result = Result.IntResult(error=True, info="Multiple_Results_Found", result=-1)
            except Exception as e:
                result = Result.IntResult(error=True, info=repr(e), result=-1)
        return result

    async def select(self):
        async_session = DB().get_async_session()
        async with async_session() as session:
            try:
                async with session.begin():
                    try:
                        session_result = await session.execute(select(Dynamic_Subscription).where(
                            Dynamic_Subscription.uid == self.uid).where(
                            Dynamic_Subscription.subscriber_id == self.subscriber_id))
                        subscription = session_result.scalar_one()
                        result = Result.IntResult(error=False, info="Exist", result=subscription)
                    except NoResultFound:
                        result = Result.IntResult(error=False, info="Select_No_Result", result=1)
            except MultipleResultsFound:
                result = Result.IntResult(error=True, info="Multiple_Results_Found", result=-1)
            except Exception as e:
                result = Result.IntResult(error=True, info=repr(e), result=-1)
        return result

    async def select_subscribers(self):
        async_session = DB().get_async_session()
        async with async_session() as session:
            try:
                async with session.begin():
                    try:
                        session_result = await session.execute(select(Dynamic_Subscription).where(
                            Dynamic_Subscription.uid == self.uid))
                        result = Result.ListResult(error=False, info="Exist", result=session_result.scalars().all())
                    except NoResultFound:
                        result = Result.ListResult(error=False, info="Select_No_Result", result=[])
            except MultipleResultsFound:
                result = Result.ListResult(error=True, info="Multiple_Results_Found", result=[])
            except Exception as e:
                result = Result.ListResult(error=True, info=repr(e), result=[])
        return result

    async def select_uids(self):
        async_session = DB().get_async_session()
        async with async_session() as session:
            try:
                async with session.begin():
                    try:
                        session_result = await session.execute(select(distinct(Dynamic_Subscription.uid)))
                        result = Result.ListResult(error=False, info="Exist", result=session_result.scalars().all())
                    except NoResultFound:
                        result = Result.ListResult(error=False, info="Select_No_Result", result=[])
            except MultipleResultsFound:
                result = Result.ListResult(error=True, info="Multiple_Results_Found", result=[])
            except Exception as e:
                result = Result.ListResult(error=True, info=repr(e), result=[])
        return result


class Live_Subscription(Base):
    __tablename__ = "Live_Subscription"
    id = Column(Integer, nullable=False, primary_key=True, index=True, autoincrement=True)
    bot_id = Column(String(16), nullable=False, comment="Bot_id")
    uid = Column(String(16), nullable=False, comment="B站UID")
    subscriber_id = Column(String(16), nullable=False, comment="QQ/群号")
    send_type = Column(String(10), nullable=False, comment="1：QQ 2：群")

    def __init__(self, bot_id: str, uid: str, subscriber_id: str, send_type: str):
        self.bot_id = bot_id
        self.uid = uid
        self.subscriber_id = subscriber_id
        self.send_type = send_type

    async def insert(self):
        async_session = DB().get_async_session()
        async with async_session() as session:
            try:
                async with session.begin():
                    try:
                        result = await self.select()
                        if not result.error and result.result == 1:
                            session.add(self)
                            result = Result.IntResult(error=False, info="Insert_Success", result=1)
                    except Exception as e:
                        result = Result.IntResult(error=True, info=repr(e), result=-1)
                await session.commit()
            except MultipleResultsFound:
                result = Result.IntResult(error=True, info="Multiple_Results_Found", result=-1)
            except Exception as e:
                result = Result.IntResult(error=True, info=repr(e), result=-1)
        return result

    async def delete(self):
        async_session = DB().get_async_session()
        async with async_session() as session:
            try:
                async with session.begin():
                    try:
                        result = await self.select()
                        if not result.error and isinstance(result.result, Live_Subscription):
                            await session.delete(result.result)
                            result = Result.IntResult(error=False, info="Delete_Success", result=1)
                    except Exception as e:
                        result = Result.IntResult(error=True, info=repr(e), result=-1)
                await session.commit()
            except MultipleResultsFound:
                result = Result.IntResult(error=True, info="Multiple_Results_Found", result=-1)
            except Exception as e:
                result = Result.IntResult(error=True, info=repr(e), result=-1)
        return result

    async def select(self):
        async_session = DB().get_async_session()
        async with async_session() as session:
            try:
                async with session.begin():
                    try:
                        session_result = await session.execute(select(Live_Subscription).where(
                            Live_Subscription.uid == self.uid).where(
                            Live_Subscription.subscriber_id == self.subscriber_id))
                        subscription = session_result.scalar_one()
                        result = Result.IntResult(error=False, info="Exist", result=subscription)
                    except NoResultFound:
                        result = Result.IntResult(error=False, info="Select_No_Result", result=1)
            except MultipleResultsFound:
                result = Result.IntResult(error=True, info="Multiple_Results_Found", result=-1)
            except Exception as e:
                result = Result.IntResult(error=True, info=repr(e), result=-1)
        return result

    async def select_subscribers(self):
        async_session = DB().get_async_session()
        async with async_session() as session:
            try:
                async with session.begin():
                    try:
                        session_result = await session.execute(select(Live_Subscription).where(
                            Live_Subscription.uid == self.uid))
                        result = Result.ListResult(error=False, info="Exist", result=session_result.scalars().all())
                    except NoResultFound:
                        result = Result.ListResult(error=False, info="Select_No_Result", result=[])
            except MultipleResultsFound:
                result = Result.ListResult(error=True, info="Multiple_Results_Found", result=[])
            except Exception as e:
                result = Result.ListResult(error=True, info=repr(e), result=[])
        return result

    async def select_uids(self):
        async_session = DB().get_async_session()
        async with async_session() as session:
            try:
                async with session.begin():
                    try:
                        session_result = await session.execute(select(distinct(Live_Subscription.uid)))
                        result = Result.ListResult(error=False, info="Exist", result=session_result.scalars().all())
                    except NoResultFound:
                        result = Result.ListResult(error=False, info="Select_No_Result", result=[])
            except MultipleResultsFound:
                result = Result.ListResult(error=True, info="Multiple_Results_Found", result=[])
            except Exception as e:
                result = Result.ListResult(error=True, info=repr(e), result=[])
        return result


class Welcome_Subscription(Base):
    __tablename__ = "Welcome_Subscription"
    id = Column(Integer, nullable=False, primary_key=True, index=True, autoincrement=True)
    subscriber_id = Column(String(16), nullable=False, comment="群号")
    status = Column(Boolean, nullable=False, comment="状态")
    content = Column(Text, nullable=False, comment="内容")

    def __init__(self, subscriber_id: str, status: bool, content: str):
        self.subscriber_id = subscriber_id
        self.status = status
        self.content = content

    async def insert(self):
        async_session = DB().get_async_session()
        async with async_session() as session:
            try:
                async with session.begin():
                    try:
                        result = await self.select()
                        if not result.error and result.result == 1:
                            session.add(self)
                            result = Result.IntResult(error=False, info="Insert_Success", result=1)
                    except Exception as e:
                        result = Result.IntResult(error=True, info=repr(e), result=-1)
                await session.commit()
            except MultipleResultsFound:
                result = Result.IntResult(error=True, info="Multiple_Results_Found", result=-1)
            except Exception as e:
                result = Result.IntResult(error=True, info=repr(e), result=-1)
        return result

    async def delete(self):
        async_session = DB().get_async_session()
        async with async_session() as session:
            try:
                async with session.begin():
                    try:
                        result = await self.select()
                        if not result.error and isinstance(result.result, Welcome_Subscription):
                            await session.delete(result.result)
                            result = Result.IntResult(error=False, info="Delete_Success", result=1)
                    except Exception as e:
                        result = Result.IntResult(error=True, info=repr(e), result=-1)
                await session.commit()
            except MultipleResultsFound:
                result = Result.IntResult(error=True, info="Multiple_Results_Found", result=-1)
            except Exception as e:
                result = Result.IntResult(error=True, info=repr(e), result=-1)
        return result

    async def select(self):
        async_session = DB().get_async_session()
        async with async_session() as session:
            try:
                async with session.begin():
                    try:
                        session_result = await session.execute(select(Welcome_Subscription).where(
                            Welcome_Subscription.subscriber_id == self.subscriber_id))
                        subscription = session_result.scalar_one()
                        result = Result.IntResult(error=False, info="Exist", result=subscription)
                    except NoResultFound:
                        result = Result.IntResult(error=False, info="Select_No_Result", result=1)
            except MultipleResultsFound:
                result = Result.IntResult(error=True, info="Multiple_Results_Found", result=-1)
            except Exception as e:
                result = Result.IntResult(error=True, info=repr(e), result=-1)
        return result

    async def select_subscribers(self):
        async_session = DB().get_async_session()
        async with async_session() as session:
            try:
                async with session.begin():
                    try:
                        session_result = await session.execute(
                            select(Welcome_Subscription).where(Welcome_Subscription.status == self.status))
                        result = Result.ListResult(error=False, info="Exist", result=session_result.scalars().all())
                    except NoResultFound:
                        result = Result.ListResult(error=False, info="Select_No_Result", result=[])
            except MultipleResultsFound:
                result = Result.ListResult(error=True, info="Multiple_Results_Found", result=[])
            except Exception as e:
                result = Result.ListResult(error=True, info=repr(e), result=[])
        return result


class Task_Subscription(Base):
    __tablename__ = "Task_Subscription"
    id = Column(Integer, nullable=False, primary_key=True, index=True, autoincrement=True)
    bot_id = Column(String(16), nullable=False, comment="Bot_id")
    subscriber_id = Column(String(16), nullable=False, comment="qq/群号")
    interval_time = Column(Integer, nullable=False, comment="间隔时间")
    content = Column(Text, nullable=False, comment="内容")
    send_type = Column(String(10), nullable=False, comment="私聊/群")

    def __init__(self, bot_id: str, subscriber_id: str, interval_time: int, content: str, send_type: str):
        self.bot_id = bot_id
        self.subscriber_id = subscriber_id
        self.interval_time = interval_time
        self.content = content
        self.send_type = send_type

    async def insert(self):
        async_session = DB().get_async_session()
        async with async_session() as session:
            try:
                async with session.begin():
                    try:
                        result = await self.select()
                        if not result.error and result.result == 1:
                            session.add(self)
                            result = Result.IntResult(error=False, info="Insert_Success", result=1)
                    except Exception as e:
                        result = Result.IntResult(error=True, info=repr(e), result=-1)
                await session.commit()
            except MultipleResultsFound:
                result = Result.IntResult(error=True, info="Multiple_Results_Found", result=-1)
            except Exception as e:
                result = Result.IntResult(error=True, info=repr(e), result=-1)
        return result

    async def delete(self):
        async_session = DB().get_async_session()
        async with async_session() as session:
            try:
                async with session.begin():
                    try:
                        result = await self.select_by_self()
                        if not result.error and isinstance(result.result, Task_Subscription):
                            await session.delete(result.result)
                            result = Result.IntResult(error=False, info="Delete_Success", result=1)
                    except Exception as e:
                        result = Result.IntResult(error=True, info=repr(e), result=-1)
                await session.commit()
            except MultipleResultsFound:
                result = Result.IntResult(error=True, info="Multiple_Results_Found", result=-1)
            except Exception as e:
                result = Result.IntResult(error=True, info=repr(e), result=-1)
        return result

    async def select(self):
        async_session = DB().get_async_session()
        async with async_session() as session:
            try:
                async with session.begin():
                    try:
                        session_result = await session.execute(select(Task_Subscription).where(
                            Task_Subscription.id == self.id))
                        subscription = session_result.scalar_one()
                        result = Result.IntResult(error=False, info="Exist", result=subscription)
                    except NoResultFound:
                        result = Result.IntResult(error=False, info="Select_No_Result", result=1)
            except MultipleResultsFound:
                result = Result.IntResult(error=True, info="Multiple_Results_Found", result=-1)
            except Exception as e:
                result = Result.IntResult(error=True, info=repr(e), result=-1)
        return result

    async def select_all(self):
        async_session = DB().get_async_session()
        async with async_session() as session:
            try:
                async with session.begin():
                    try:
                        session_result = await session.execute(select(Task_Subscription))
                        result = Result.ListResult(error=False, info="Exist", result=session_result.scalars().all())
                    except NoResultFound:
                        result = Result.ListResult(error=False, info="Select_No_Result", result=[])
            except MultipleResultsFound:
                result = Result.ListResult(error=True, info="Multiple_Results_Found", result=[])
            except Exception as e:
                result = Result.ListResult(error=True, info=repr(e), result=[])
        return result

    async def select_by_self(self):
        async_session = DB().get_async_session()
        async with async_session() as session:
            try:
                async with session.begin():
                    try:
                        session_result = await session.execute(
                            select(Task_Subscription).where(
                                Task_Subscription.subscriber_id == self.subscriber_id).where(
                                Task_Subscription.bot_id == self.bot_id).where(Task_Subscription.id == self.id))
                        subscription = session_result.scalar_one()
                        result = Result.ListResult(error=False, info="Exist", result=subscription)
                    except NoResultFound:
                        result = Result.ListResult(error=False, info="Select_No_Result", result=["啥也没有"])
            except MultipleResultsFound:
                result = Result.ListResult(error=True, info="Multiple_Results_Found", result=[])
            except Exception as e:
                result = Result.ListResult(error=True, info=repr(e), result=[])
        return result

    async def select_all_by_self(self):
        async_session = DB().get_async_session()
        async with async_session() as session:
            try:
                async with session.begin():
                    try:
                        session_result = await session.execute(
                            select(Task_Subscription).where(
                                Task_Subscription.subscriber_id == self.subscriber_id).where(
                                Task_Subscription.bot_id == self.bot_id))
                        result = Result.ListResult(error=False, info="Exist", result=session_result.scalars().all())
                    except NoResultFound:
                        result = Result.ListResult(error=False, info="Select_No_Result", result=[])
            except MultipleResultsFound:
                result = Result.ListResult(error=True, info="Multiple_Results_Found", result=[])
            except Exception as e:
                result = Result.ListResult(error=True, info=repr(e), result=[])
        return result


class Recipes(Base):
    __tablename__ = "Recipes"
    id = Column(Integer, nullable=False, primary_key=True, index=True, autoincrement=True)
    name = Column(String(16), nullable=False, comment="菜名")
    content = Column(BLOB, nullable=False, primary_key=False, comment="图片")

    def __init__(self, name: str, content: bytes):
        self.name = name
        self.content = content

    async def insert(self):
        async_session = DB().get_async_session()
        async with async_session() as session:
            try:
                async with session.begin():
                    try:
                        result = await self.select()
                        if not result.error and result.result == 1:
                            session.add(self)
                            result = Result.IntResult(error=False, info="Insert_Success", result=1)
                    except Exception as e:
                        result = Result.IntResult(error=True, info=repr(e), result=-1)
                await session.commit()
            except MultipleResultsFound:
                result = Result.IntResult(error=True, info="Multiple_Results_Found", result=-1)
            except Exception as e:
                result = Result.IntResult(error=True, info=repr(e), result=-1)
        return result

    async def delete(self):
        async_session = DB().get_async_session()
        async with async_session() as session:
            try:
                async with session.begin():
                    try:
                        result = await self.select()
                        if not result.error and isinstance(result.result, Recipes):
                            await session.delete(result.result)
                            result = Result.IntResult(error=False, info="Delete_Success", result=1)
                    except Exception as e:
                        result = Result.IntResult(error=True, info=repr(e), result=-1)
                await session.commit()
            except MultipleResultsFound:
                result = Result.IntResult(error=True, info="Multiple_Results_Found", result=-1)
            except Exception as e:
                result = Result.IntResult(error=True, info=repr(e), result=-1)
        return result

    async def select(self):
        async_session = DB().get_async_session()
        async with async_session() as session:
            try:
                async with session.begin():
                    try:
                        session_result = await session.execute(select(Recipes).where(
                            Recipes.name == self.name))
                        subscription = session_result.scalar_one()
                        result = Result.IntResult(error=False, info="Exist", result=subscription)
                    except NoResultFound:
                        result = Result.IntResult(error=False, info="Select_No_Result", result=1)
            except MultipleResultsFound:
                result = Result.IntResult(error=True, info="Multiple_Results_Found", result=-1)
            except Exception as e:
                result = Result.IntResult(error=True, info=repr(e), result=-1)
        return result

    async def select_all(self):
        async_session = DB().get_async_session()
        async with async_session() as session:
            try:
                async with session.begin():
                    try:
                        session_result = await session.execute(select(Recipes))
                        result = Result.ListResult(error=False, info="Exist", result=session_result.scalars().all())
                    except NoResultFound:
                        result = Result.ListResult(error=False, info="Select_No_Result", result=[])
            except MultipleResultsFound:
                result = Result.ListResult(error=True, info="Multiple_Results_Found", result=[])
            except Exception as e:
                result = Result.ListResult(error=True, info=repr(e), result=[])
        return result
