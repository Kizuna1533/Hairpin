# @Author: South
# @Date: 2021-08-14 10:56
import httpx
from pyppeteer import launch

dynamic_url = "https://t.bilibili.com/%s?tab=3"
space_history = "https://api.vc.bilibili.com/dynamic_svr/v1/dynamic_svr/space_history?visitor_uid=%s&host_uid=%s&offset_dynamic_id=%s&need_top=0"

space_headers = {"Origin": "https://space.bilibili.com", "Accept": "application/json, text/plain, */*",
                 "Connection": "close",
                 "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 11_0_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.88 Safari/537.36",
                 "Referer": "https://space.bilibili.com/", "Sec-Fetch-Site": "same-site", "Sec-Fetch-Dest": "empty",
                 "DNT": "1", "Accept-Encoding": "gzip, deflate", "Accept-Language": "zh-CN,zh;q=0.9",
                 "Sec-Fetch-Mode": "cors"}


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
    browser = await launch(args=["--no-sandbox"], waitUntil="networkidle0", timeout=10000, handleSIGINT=False,
                           handleSIGTERM=False, handleSIGHUP=False)
    page = await browser.newPage()
    for i in range(retry + 1):
        try:
            await page.goto(dynamic_url % dynamic_id)
            await page.waitForSelector("div[class=card-content]")
            await page.setViewport(viewport={"width": 2000, "height": 1080})
            card = await page.querySelector("div[class=detail-card]")
            assert card is not None
            clip = await card.boundingBox()
            image = await page.screenshot(clip=clip, encoding="base64")
            await browser.close()
            return image
        except Exception as e:
            if i >= retry:
                await browser.close()
                raise
