from pyppeteer.page import Page

from core.redis import get_redis
from scrapper.structs import User
from scrapper.loader import logger, db
from scrapper.actions.vacancies import open_vacancy_page


async def open_filter_page(page: Page, user: User, *args, **kwargs) -> None:
    await page.goto("https://hh.ru/search/vacancy?%s&page=0" % user.resume_url)
    for page_number in range(await get_pages_count(page)):
        await get_vacancies_items(page, user)
        await page.goto("https://hh.ru/search/vacancy?%s&page=%s" % (user.resume_url, page_number))

    redis = await get_redis()
    fullname = " ".join(getattr(user, i) for i in ("middlename", "firstname", "patronymic"))
    await redis.publish("%s:%s" % (user.curator_id, user.id), "Закончил рассылку по %s" % fullname)


async def get_pages_count(page: Page, *args, **kwargs) -> int:
    await page.evaluate("{window.scrollBy(0, document.body.scrollHeight);}")
    selector: str = "(//span[@class='pager-item-not-in-short-range']//a//span//text())[3]"
    pager_selector = await page.waitForXPath(
        selector, visible=True, timeout=3000
    )
    if pager_selector:
        pages_count = await page.evaluate("(element) => element.textContent", pager_selector)
        if pages_count.isdigit():
            return int(pages_count)
        else:
            return 0


async def get_vacancies_items(page: Page, user: User, page_number: int = 0, *args, **kwargs) -> None:
    for item in range(1, 50):
        try:
            item_xpath = await page.waitForXPath("(//div[@class='serp-item'])[%s]" % item)
            if item_xpath:
                vacancy_url_xpath = await page.waitForXPath(
                    "(//a[@class='serp-item__title'])[%s]" % item
                )
                vacancy_url_xpath = await page.evaluate("(element) => element.href", vacancy_url_xpath)
                if vacancy_url_xpath:
                    vacancy_checked = await db.pool.fetchval(
                        """
                        SELECT 
                            count(id)
                        FROM 
                            vacancies 
                        WHERE 
                            user_id = $1 
                            AND url = $2
                            AND parsed = TRUE
                        """,
                        user.id,
                        vacancy_url_xpath
                    )
                    if vacancy_checked:
                        # TODO: Ask about it
                        continue

                    await open_vacancy_page(page, user, vacancy_url_xpath)

        except Exception as e:
            logger.critical("Something went wrong in `parse_vacancies_items`. %s" % e)
