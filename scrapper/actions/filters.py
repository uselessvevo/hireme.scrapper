import uuid
from pyppeteer.page import Page
from scrapper.structs import User
from core.redis import get_redis, publish_user_message


async def filter_page(page: Page, user: User, *args, **kwargs) -> None:
    await page.goto("https://hh.ru/search/vacancy?%s&page=0" % user.resumeFilter)
    await publish_user_message(user, "Hello??")

    # for page_number in range(await get_pages_count(page)):
    #     await get_vacancies(page, page_number)


async def get_pages_count(page: Page, *args, **kwargs) -> int:
    await page.evaluate("{window.scrollBy(0, document.body.scrollHeight);}")
    selector: str = "(//span[@class='pager-item-not-in-short-range']//a//span//text())[3]"
    pager_selector = await page.waitForXPath(
        selector, visible=True, timeout=100
    )
    if pager_selector:
        pages_count = await page.evaluate("(element) => element.textContent", pager_selector)
        if pages_count.isdigit():
            return int(pages_count)
        else:
            return 0


async def get_vacancies(page: Page, page_number: int, *args, **kwargs) -> None:
    pass
