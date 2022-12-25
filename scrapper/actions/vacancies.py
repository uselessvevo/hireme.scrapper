import asyncio
import random

from pyppeteer.page import Page

from core.redis import get_redis
from scrapper.loader import logger, db
from scrapper.structs import User


async def open_vacancy_page(page: Page, user: User, vacancy_url: str) -> None:
    methods = (
        parse_vacancy_basic_page,
        parse_vacancy_stylized_page,
    )

    new_page = await page.browser.newPage()
    await new_page.setViewport({"width": 1920, "height": 1280})
    await new_page.goto(vacancy_url)

    for method in methods:
        try:
            result = await method(new_page)
            if result:
                await send_letter(new_page, user, vacancy_url)
                await db.pool.execute(
                    """
                    INSERT INTO 
                        vacancies (id, user_id, url, content, percentage, title, salary, parsed)
                    VALUES 
                        (default, $1, $2, $3, $4, $5, $6, $7)
                    """,
                    user.id,
                    vacancy_url,
                    result.get("content"),
                    result.get("percentage"),
                    result.get("title"),
                    result.get("salary"),
                    True
                )
                logger.info("Successfully parsed URL: %s by `%s` method" % (vacancy_url, method.__qualname__))
                # await asyncio.sleep(1 * 60000 + random.randrange(2000, 3000))
                # await asyncio.sleep(random.randrange(3000, 10000))
                break

        except Exception as e:
            await db.pool.execute(
                """
                UPDATE 
                    vacancies
                SET 
                    parsed = FALSE 
                WHERE 
                    user_id = $1 
                    AND url = $2
                    AND parsed = FALSE
                """,
                user.id,
                vacancy_url,
            )
            logger.critical("Can't parse URL: %s by `%s` method" % (vacancy_url, method.__qualname__))
            logger.critical(str(e))


async def parse_vacancy_basic_page(page: Page) -> dict:
    """
    Parse page that has really basic layout
    """
    vacancy_title_xpath = await page.waitForXPath(
        "//h1[@data-qa='vacancy-title']//span[1]",
        visible=True, timeout=1000
    )
    vacancy_title_content = await page.evaluate("(element) => element.innerText", vacancy_title_xpath)

    vacancy_salary_xpath = await page.waitForXPath(
        "//span[@class='bloko-header-section-2 bloko-header-section-2_lite']",
        visible=True, timeout=1000
    )
    vacancy_salary_content = await page.evaluate("(element) => element.innerText", vacancy_salary_xpath)

    vacancy_content_selector = await page.waitForSelector(
        "#HH-React-Root > div > div.HH-MainContent."
        "HH-Supernova-MainContent > div.main-content "
        "> div > div > div > div > div.bloko-column."
        "bloko-column_container.bloko-column_xs-4.bloko"
        "-column_s-8.bloko-column_m-12.bloko-column_l-10 "
        "> div:nth-child(3) > div > div > div:nth-child(1)",
        visible=True, timeout=3000
    )
    vacancy_content = await page.evaluate("(element) => element.innerText", vacancy_content_selector)
    return {
        "percentage": 0.0,
        "salary": vacancy_salary_content,
        "title": vacancy_title_content,
        "content": vacancy_content
    }


async def parse_vacancy_stylized_page(page: Page) -> dict:
    vacancy_title_xpath = await page.waitForXPath(
        "//h1[@data-qa='vacancy-title']//span[1]"
    )
    vacancy_title_content = await page.evaluate("(element) => element.innerText", vacancy_title_xpath)

    vacancy_salary_xpath = await page.waitForXPath(
        "//span[@class='bloko-header-section-2 bloko-header-section-2_lite']",
        visible=True, timeout=1000
    )
    vacancy_salary_content = await page.evaluate("(element) => element.innerText", vacancy_salary_xpath)

    vacancy_content_selector = await page.waitForSelector(
        "#HH-React-Root > div > div.HH-MainContent."
        "HH-Supernova-MainContent > div.main-content > "
        "div > div > div > div > div.bloko-column."
        "bloko-column_container.bloko-column_xs-4.bloko"
        "-column_s-8.bloko-column_m-12.bloko-column_l-10 > "
        "div.vacancy-description > div.bloko-column."
        "bloko-column_xs-4.bloko-column_s-8.bloko-column_m-9"
        ".bloko-column_l-9 > div > div > div > div > div > div "
        "> div.tmpl_hh_content > div > div"
    )
    vacancy_content = await page.evaluate("(element) => element.innerText", vacancy_content_selector)
    return {
        "percentage": 0.0,
        "salary": vacancy_salary_content,
        "title": vacancy_title_content,
        "content": vacancy_content
    }


async def send_letter(page: Page, user: User, vacancy_url: str) -> None:
    submit_button_xpath = await page.waitForXPath(
        "(//a[contains(@class,'bloko-button bloko-button_kind-success')])[2]",
        visible=True, timeout=2000
    )
    await submit_button_xpath.focus()
    await submit_button_xpath.click()

    send_letter_button_xpath = await page.waitForXPath(
        "//span[text()='Написать сопроводительное']",
        visible=True, timeout=5000
    )
    await send_letter_button_xpath.focus()
    await send_letter_button_xpath.click()

    letter_form_xpath = await page.waitForXPath(
        "//textarea[@name='text']",
        visible=True, timeout=1000
    )
    await letter_form_xpath.focus()
    letter_content = await db.pool.fetchval(
        """
        SELECT content FROM letters WHERE user_id = $1
        """,
        user.id
    )
    await page.keyboard.type(letter_content)
    submit_button_xpath = await page.waitForXPath(
        "//span[text()='Отправить']",
        visible=True, timeout=5000
    )
    await submit_button_xpath.focus()
    await submit_button_xpath.click()

    # redis = await get_redis()
    # fullname = " ".join(getattr(user, i) for i in ("middlename", "firstname", "patronymic"))
    # await redis.publish("%s:%s" % (user.curator_id, user.id), "Сделал отклик для %s. URL: %s" % (fullname, vacancy_url))
