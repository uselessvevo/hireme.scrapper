import uuid
from pyppeteer.page import Page

from scrapper.loader import logger
from scrapper.structs import User
from core.redis import get_redis, publish_user_message
from scrapper.actions.filters import filter_page
from scrapper.utils import remove_user_session_folder


async def check_is_authorized(page: Page, user: User) -> None:
    """
    Go to the filter page if user is authorized, else authorize again
    """
    await page.goto("https://hh.ru/search/vacancy")
    try:
        login_button_selector = await page.waitForXPath(
            "//a[@data-page-analytics-event='login_button_header.desktop']",
            visible=True, timeout=1000
        )
    except Exception:
        login_button_selector = await page.waitForSelector(
            "#HH-React-Root > div > div.supernova-navi-search-wrapper > "
            "div.supernova-navi-wrapper > div > div > div > div:nth-child(11) > "
            "div.supernova-dropdown-anchor > div > button > span",
            visible=True,
            timeout=1000
        )
    if login_button_selector:
        login_button_text = await page.evaluate("(element) => element.textContent", login_button_selector)
        if login_button_text == "Войти":
            await login_page(page, user)
            await remove_user_session_folder(user.id)
        else:
            await filter_page(page, user)


async def login_page(page: Page, user: User) -> None:
    await page.goto("https://hh.ru/account/login?backurl=%2F&hhtmFrom=main")

    login_type_xpath = "(//button[@class='bloko-link bloko-link_pseudo'])[2]"
    login_type_selector = await page.waitForXPath(
        login_type_xpath, visible=True, timeout=1000
    )
    if login_type_selector:
        await login_by_email(page, login_type_selector, user)
    else:
        await catch_captcha(page, user)


async def login_by_email(page: Page, selector: object, user: User) -> None:
    await selector.focus()
    await selector.click()

    username_input_selector = await page.waitForXPath(
        "(//input[@name='username'])[2]", visible=True, timeout=1000
    )
    if username_input_selector:
        # Input username
        await username_input_selector.focus()
        await page.keyboard.type(user.email)

    password_input_selector = await page.waitForXPath(
        "//input[@data-qa='login-input-password']", visible=True, timeout=1000
    )
    if password_input_selector:
        await password_input_selector.focus()
        await page.keyboard.type(user.password)
        await page.keyboard.press("Enter")


async def catch_captcha(page: Page, user: User):
    # Хватаем капчу
    selector = (
        '//*[@id="HH-React-Root"]'
        '/div/div[4]/div[1]/div/div/'
        'div/div/div/div/div/div/div/'
        'div/div/form/div[2]/div[3]/img'
    )
    captcha_selector = await page.waitForXPath(
        selector, visible=True, timeout=1000
    )
    if captcha_selector:
        redis = await get_redis()
        image_path = "media/screenshots/%s.png" % uuid.uuid4()
        await captcha_selector.screenshot({"path": image_path})
        await publish_user_message(user, image_path)

        sub = redis.pubsub()
        await sub.subscribe("%s:%s" % (user.curatorId, user.id))

        async for message in sub.listen():
            if message:
                logger.info("Getting result %s" % message.get("data"))
                captcha_password_input = await page.waitForXPath(
                    "//input[@data-qa='login-input-password']", visible=True, timeout=1000
                )
                if captcha_password_input:
                    await captcha_password_input.focus()
                    await page.keyboard.type(message.get("data"))
                    await page.keyboard.press("Enter")
