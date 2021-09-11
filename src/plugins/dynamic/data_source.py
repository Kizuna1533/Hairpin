# @Author: South
# @Date: 2021-08-14 10:56
import base64
from typing import Optional

import httpx
from playwright.async_api import Browser, async_playwright

dynamic_url = "https://t.bilibili.com/%s?tab=3"
space_history = "https://api.vc.bilibili.com/dynamic_svr/v1/dynamic_svr/space_history?visitor_uid=%s&host_uid=%s&offset_dynamic_id=%s&need_top=0"

space_headers = {"Origin": "https://space.bilibili.com", "Accept": "application/json, text/plain, */*",
                 "Connection": "close",
                 "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 11_0_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.88 Safari/537.36",
                 "Referer": "https://space.bilibili.com/", "Sec-Fetch-Site": "same-site", "Sec-Fetch-Dest": "empty",
                 "DNT": "1", "Accept-Encoding": "gzip, deflate", "Accept-Language": "zh-CN,zh;q=0.9",
                 "Sec-Fetch-Mode": "cors"}

_browser: Optional[Browser] = None


async def init(**kwargs) -> Browser:
    global _browser
    browser = await async_playwright().start()
    _browser = await browser.chromium.launch(**kwargs)
    return _browser


async def get_browser(**kwargs) -> Browser:
    return _browser or await init(**kwargs)


async def get_dynamic_list(uid, offset_dynamic_id=0):
    """
        爬取主播B站空间动态。
        Args:
            offset_dynamic_id (int, optional): 每页动态id索引，默认为第一页：0
        Returns:
            list[list,int].第一个值为动态id列表;第二个值为下一页索引，没有下一页则为-1.
    """
    async with httpx.AsyncClient() as client:
        result = {}
        try:
            data = (await client.get(headers=space_headers, url=space_history % (uid, uid, offset_dynamic_id))).json()[
                "data"]
            print(space_history % (uid, uid, offset_dynamic_id))
            dynamic_list = []
            for card in data["cards"]:
                dynamic_list.append(card["desc"]["dynamic_id"])
            result["dynamic_list"] = dynamic_list
            if data["has_more"] == 1:
                result["next_offset"] = data["next_offset"]
            else:
                result["next_offset"] = -1
        except httpx.ConnectTimeout:
            await client.aclose()
            return {"dynamic": [], "next_offset": -1}
        return result


async def get_dynamics_screenshot(dynamic_id, retry=3):
    """
        截图B站空间动态主要内容。
        Args:
            dynamic_id (int, optional): 动态id
            retry    (int, optional): 重连次数，默认为3
        Returns:
            void.
    """
    browser = await get_browser()
    page = None
    for i in range(retry + 1):
        try:
            page = await browser.new_page()
            await page.goto(dynamic_url % dynamic_id, wait_until='networkidle', timeout=10000)
            await page.set_viewport_size({"width": 1980, "height": 1080})
            card = await page.query_selector(".detail-card")
            assert card is not None
            clip = await card.bounding_box()
            assert clip is not None
            image = await page.screenshot(clip=clip)
            await page.close()
            return base64.b64encode(image).decode()
        except Exception:
            if page:
                await page.close()
            raise
