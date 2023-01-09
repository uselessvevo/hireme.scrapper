import re
import typing
from contextlib import suppress

from pyppeteer.page import Page

from scrapper.structs import User
from scrapper.loader import logger
from core.database import DatabaseAsync
from core.redis import publish_user_message


async def open_vacancy_page(page: Page, user: User, vacancy_url: str) -> None:
    """
    Open vacancy page and parse it
    """
    methods = (
        parse_vacancy_basic_page,
        parse_vacancy_stylized_page_v1,
        parse_vacancy_stylized_page_v2,
    )

    new_page = await page.browser.newPage()
    await new_page.setViewport({"width": 1920, "height": 1280})
    await new_page.goto(vacancy_url)

    for method in methods:
        try:
            result = await method(new_page)
            if result:
                await send_letter(new_page, user)
                async with DatabaseAsync() as conn:
                    await conn.execute(
                        """
                        INSERT INTO 
                            vacancies (id, user_id, url, vacancy_id, content, percentage, title, salary, parsed)
                        VALUES 
                            (default, $1, $2, $3, $4, $5, $6, $7, $8)
                        """,
                        user.id,
                        vacancy_url,
                        int(re.findall(r"\d+", vacancy_url)[0]),
                        result.get("content"),
                        result.get("percentage"),
                        result.get("title"),
                        result.get("salary"),
                        True
                    )
                logger.info("Successfully parsed URL: %s by `%s` method" % (vacancy_url, method.__qualname__))
                break

        except Exception as e:
            async with DatabaseAsync() as conn:
                await conn.execute(
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
            continue


async def get_popup_error_message(page: Page) -> bool:
    error_message_selector = await page.waitForSelector(
        "/html/body/div[10]/div/div/div/div[2]/div[1]/div",
        visible=True, timeout=9999999999
    )
    error_message_selector = await page.evaluate("(element) => element.innerText", error_message_selector)
    return "ошибка" in error_message_selector


async def parse_vacancy_basic_page(page: Page) -> typing.Union[dict, None]:
    """
    Parse page that has really basic layout
    """
    with suppress(Exception):
        already_clicked_xpath = await page.waitForXPath(
            "//a[contains(@class,'bloko-button bloko-button_kind-success')]",
            visible=True, timeout=1000
        )
        already_clicked_xpath = await page.evaluate("(element) => element.innerText", already_clicked_xpath)
        if already_clicked_xpath in ("Смотреть отклик", "Смотреть приглашение"):
            raise ValueError

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


async def parse_vacancy_stylized_page_v1(page: Page) -> typing.Union[dict, None]:
    with suppress(Exception):
        already_clicked_xpath = await page.waitForXPath(
            "//a[contains(@class,'bloko-button bloko-button_kind-success')]",
            visible=True, timeout=1000
        )
        already_clicked_xpath = await page.evaluate("(element) => element.innerText", already_clicked_xpath)
        if already_clicked_xpath in ("Смотреть отклик", "Смотреть приглашение"):
            raise ValueError

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


async def parse_vacancy_stylized_page_v2(page: Page) -> typing.Union[dict, None]:
    with suppress(Exception):
        already_clicked_xpath = await page.waitForXPath(
            "//a[contains(@class,'bloko-button bloko-button_kind-success')]",
            visible=True, timeout=1000
        )
        already_clicked_xpath = await page.evaluate("(element) => element.innerText", already_clicked_xpath)
        if already_clicked_xpath in ("Смотреть отклик", "Смотреть приглашение"):
            raise ValueError

    vacancy_title_xpath = await page.waitForXPath(
        "//h1[@data-qa='vacancy-title']//span[1]",
        visible=True, timeout=1000
    )
    vacancy_title_content = await page.evaluate("(element) => element.innerText", vacancy_title_xpath)

    vacancy_salary_xpath = await page.waitForSelector(
        "#a11y-main-content > div:nth-child(4) > span",
        visible=True, timeout=1000
    )
    vacancy_salary_content = await page.evaluate("(element) => element.innerText", vacancy_salary_xpath)

    vacancy_content_selector = await page.waitForSelector(
        "#HH-React-Root > div > div.HH-MainContent.HH-Supernova-MainContent > "
        "div.main-content > div:nth-child(2) > div:nth-child(1) > div > "
        "div.bloko-column.bloko-column_xs-4.bloko-column_s-8.bloko-column_m-12.bloko-column_l-16 > "
        "div > div > div > div > div > div > div > div.l-paddings.b-vacancy-desc > div",
        visible=True, timeout=1000
    )
    vacancy_content = await page.evaluate("(element) => element.innerText", vacancy_content_selector)
    return {
        "percentage": 0.0,
        "salary": vacancy_salary_content,
        "title": vacancy_title_content,
        "content": vacancy_content
    }


async def send_letter(page: Page, user: User) -> None:
    try:
        submit_button_xpath = await page.waitForXPath(
            "//a[contains(@class,'bloko-button bloko-button_kind-success')]",
            visible=True, timeout=2000
        )
    except Exception:
        submit_button_xpath = await page.waitForXPath(
            "(//a[contains(@class,'bloko-button bloko-button_kind-success')])[2]",
            visible=True, timeout=2000
        )
    await submit_button_xpath.focus()
    await submit_button_xpath.click()

    send_letter_button_xpath = await page.waitForXPath(
        '//*[@id="HH-React-Root"]/div/div[4]/div[1]/div/div/'
        'div/div/div[1]/div[4]/div/div[3]/div/div[1]/div/div/div[10]/button',
        visible=True, timeout=2000
    )
    await send_letter_button_xpath.focus()
    await send_letter_button_xpath.click()

    with suppress(Exception):
        send_additional_info_xpath = await page.waitForXPath(
            '//*[@id="HH-React-Root"]/div/div[4]/div[1]/div/div/div[1]/h1',
            visible=True, timeout=2000
        )
        send_additional_info_xpath = await page.evaluate("(element) => element.innerText", send_additional_info_xpath)
        if "отправить отклик на вакансию" in send_additional_info_xpath.lower():
            return

    letter_form_xpath = await page.waitForXPath(
        "//textarea[@name='text']",
        visible=True, timeout=1000
    )
    await letter_form_xpath.focus()
    async with DatabaseAsync() as conn:
        letter_content = await conn.fetchval(
            """
            SELECT content FROM letters WHERE user_id = $1
            """,
            user.id
        )
    if letter_content:
        await page.keyboard.type(letter_content)

    submit_button_xpath = await page.waitForXPath(
        "//span[text()='Отправить']",
        visible=True, timeout=5000
    )
    await submit_button_xpath.focus()
    await submit_button_xpath.click()

    if await get_popup_error_message(page):
        return

    await publish_user_message(user, 1, "count_vacancies")
