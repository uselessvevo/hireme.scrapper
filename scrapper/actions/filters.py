import typing
import random
import asyncio
from contextlib import suppress

from pyppeteer.page import Page

from core.database import DatabaseAsync
from core.redis import publish_user_message

from scrapper.structs import User
from scrapper.loader import logger
from scrapper.actions.vacancies import open_vacancy_page


async def open_filter_page(page: Page, user: User) -> None:
    """
    Open filter page
    """
    await page.goto(
        "https://hh.ru/search/vacancy?%s"
        "&from=suggest_post"
        "&ored_clusters=true"
        "&enable_snippets=true"
        "&page=0" % user.resume_url
    )
    for page_number in range(await get_pages_count(page)):
        # No vacancies were found
        with suppress(Exception):
            not_found_xpath = await page.waitForXPath(
                '//*[@id="HH-React-Root"]/div/div[4]/div[1]/div/div[1]/div/h1',
                visible=True, timeout=1000
            )
            not_found_xpath = await page.evaluate("(element) => element.innerText", not_found_xpath)
            if "ничего не найдено" in not_found_xpath:
                continue

        await get_vacancies_items(page, user)
        await page.goto("https://hh.ru/search/vacancy?%s&page=%s" % (user.resume_url, page_number))

    fullname = " ".join(getattr(user, i) for i in ("middlename", "firstname", "patronymic"))
    await publish_user_message(user, "Закончил рассылку по %s" % fullname)


async def get_pages_count(page: Page) -> typing.Union[int, None]:
    """
    Get pages count/amount
    """
    await page.evaluate("{window.scrollBy(0, document.body.scrollHeight);}")
    try:
        selector: str = "(//span[@class='pager-item-not-in-short-range']//a//span//text())[3]"
        pager_selector = await page.waitForXPath(
            selector, visible=True, timeout=3000
        )
        pages_count = await page.evaluate("(element) => element.textContent", pager_selector)
        if pages_count.isdigit():
            return int(pages_count)

    except Exception:
        return 1


async def get_vacancies_items(page: Page, user: User) -> None:
    """
    Get items/vacancies list
    """
    for item in range(1, 50):
        try:
            item_xpath = await page.waitForXPath("(//div[@class='serp-item'])[%s]" % item)
            if item_xpath:
                vacancy_url_xpath = await page.waitForXPath(
                    "(//a[@class='serp-item__title'])[%s]" % item
                )
                vacancy_url_xpath = await page.evaluate("(element) => element.href", vacancy_url_xpath)
                if vacancy_url_xpath:
                    async with DatabaseAsync() as conn:
                        vacancy_checked = await conn.fetchval(
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
                    await asyncio.sleep(random.randrange(60, 85))

        except Exception as e:
            logger.critical("Something went wrong in `parse_vacancies_items`. %s" % e)
