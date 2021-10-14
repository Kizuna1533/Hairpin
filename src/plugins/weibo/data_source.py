# @Author: South
# @Date: 2021-08-14 10:56
import asyncio
import base64
from typing import Optional

import httpx
from playwright.async_api import Browser, async_playwright

weibo_url = "https://m.weibo.cn/detail/%s"
space_history = "https://m.weibo.cn/api/container/getIndex?type=uid&value=%s&containerid=1076037713357552"

space_headers = {"Origin": "https://weibo.com",
                 "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
                 "Connection": "close",
                 "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 11_0_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.88 Safari/537.36",
                 "Referer": "https://weibo.com/", "Sec-Fetch-Site": "none", "Sec-Fetch-Dest": "document",
                 "DNT": "1", "Accept-Encoding": "gzip, deflate, br",
                 "Accept-Language": "zh-TW,zh-CN;q=0.9,zh;q=0.8,en;q=0.7",
                 "Sec-Fetch-Mode": "navigate"}

_browser: Optional[Browser] = None


async def init(**kwargs) -> Browser:
    global _browser
    browser = await async_playwright().start()
    _browser = await browser.chromium.launch(**kwargs)
    return _browser


async def get_browser(**kwargs) -> Browser:
    return _browser or await init(**kwargs)


async def get_weibo_list(uid, offset_weibo_id=0):
    """
        爬取主播B站空间动态。
        Args:
            offset_weibo_id (int, optional): 每页动态id索引，默认为第一页：0
        Returns:
            list[list,int].第一个值为动态id列表;第二个值为下一页索引，没有下一页则为-1.
    """
    async with httpx.AsyncClient() as client:
        result = {}
        try:
            data = (await client.get(headers=space_headers, url=space_history % uid)).json()[
                "data"]
            print(space_history % uid)
            weibo_list = []
            for card in data["cards"]:
                weibo_list.append(card["mblog"]["id"])
            result["weibo_list"] = weibo_list
            # if data["has_more"] == 1:
            #     result["next_offset"] = data["next_offset"]
            # else:
            result["next_offset"] = -1
        except httpx.ConnectTimeout:
            await client.aclose()
            return {"weibo": [], "next_offset": -1}
        return result


async def get_weibo_screenshot(weibo_id, retry=3):
    """
        截图B站空间动态主要内容。
        Args:
            weibo_id (int, optional): 动态id
            retry    (int, optional): 重连次数，默认为3
        Returns:
            void.
    """
    browser = await get_browser()
    page = None
    for i in range(retry + 1):
        try:
            page = await browser.new_page()
            await page.goto(weibo_url % weibo_id, wait_until='networkidle', timeout=10000)
            await page.set_viewport_size({"width": 1980, "height": 2160})
            main = await page.query_selector(".main")
            assert main is not None
            main_clip = await main.bounding_box()
            assert main_clip is not None
            wrap = await page.query_selector(".wrap")
            assert wrap is not None
            wrap_clip = await wrap.bounding_box()
            assert wrap_clip is not None
            main_clip['height'] = wrap_clip['y'] - main_clip['y']
            image = await page.screenshot(clip=main_clip)
            # image = await page.screenshot(clip=main_clip, path="./test.png")
            await page.close()
            return base64.b64encode(image).decode()
        except Exception:
            if page:
                await page.close()
            raise

#
# asyncio.run(get_weibo_list(7713357552))
# asyncio.run(get_weibo_screenshot(4692282445660371))
