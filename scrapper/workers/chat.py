import copy
import uuid
from contextlib import suppress

import asyncio

import aiocron as aiocron
import asyncpg
import pyppeteer
from pathlib import Path

from core.database import DatabaseAsync
from core.config import CRONTAB_SETTINGS
from core.config import PUPPETER_LAUNCH_SETTINGS

from core.redis import get_redis
from core.redis import publish_user_message

from scrapper.actions.chat import open_chat_page
from scrapper.actions.auth import open_login_page
from scrapper.actions.auth import check_is_authorized

from scrapper.structs import User
from scrapper.loader import logger


async def run_worker(queue: asyncio.Queue) -> None:
    logger.info(f"Queue: {id(queue)} {queue}")

    launch_settings = copy.copy(PUPPETER_LAUNCH_SETTINGS)
    user_data_dir: Path = launch_settings.get("userDataDir") / str(uuid.uuid4())
    if not user_data_dir.exists():
        user_data_dir.mkdir()

    launch_settings["userDataDir"] = str(user_data_dir)

    browser = await pyppeteer.launch(**launch_settings)
    page = await browser.newPage()
    await page.setViewport({"width": 1920, "height": 1280})

    with suppress(asyncio.CancelledError):
        while True:
            user_data: User = await queue.get()
            if user_data is None:
                logger.warning("Queue %s is empty or `NoneType`" % queue)
                break

            try:
                await check_is_authorized(page, user_data, open_chat_page, open_login_page)
                await browser.close()

            except Exception as e:
                logger.critical("[%s] %s" % (user_data.id, str(e)))

            finally:
                logger.info("Done with queue for user %s %s" % (user_data.id, user_data_dir))
                queue.task_done()

    # await page.close()
    # await browser.close()
    user_data_dir.rmdir()
    logger.info("Folder %s deleted" % user_data_dir.name)


async def get_users(offset) -> list[asyncpg.Record]:
    async with DatabaseAsync() as conn:
        users = await conn.fetch(
            """
            SELECT DISTINCT ON (u.id)
                u.id,
                u.email,
                u.firstname,
                u.middlename,
                u.patronymic,
                u.password,
                u.curator_id,
                f.filter,
                f.filter_url
            FROM
                users u
            JOIN
                filters f
            ON
                u.id = f.user_id
            WHERE
                "is_employee" IS FALSE
            ORDER BY
                u.id
            LIMIT 5
            OFFSET $1
            """,
            offset
        )

    return users


@aiocron.crontab(CRONTAB_SETTINGS)
async def prepare_task(workers: int = None) -> None:
    redis = await get_redis()
    offset = int(await redis.get("scrapper_offset")) or 0

    users = await get_users(offset)
    if not users:
        await redis.set("scrapper_offset", 0)
        users = await get_users(0)

        if not users:
            await publish_user_message(users, "Не удалось найти пользователей для чата")
            raise ValueError("Users not found")

    offset += 5
    logger.info("Scrapper offset sat to %s" % offset)
    await redis.set("scrapper_offset", offset)

    queue = asyncio.Queue()
    tasks = []

    workers = workers or len(users) // 3
    workers = 1 if not workers else workers

    for _ in range(workers):
        task = asyncio.create_task(run_worker(queue))
        task.set_name(str(uuid.uuid4()))
        tasks.append(task)

    for user in users:
        user = dict(user)
        user_model: User = User(
            id=user.get("id"),
            curator_id=user.get("curator_id"),
            firstname=user.get("firstname"),
            middlename=user.get("middlename"),
            patronymic=user.get("patronymic"),
            email=user.get("email"),
            password=user.get("password"),
            is_employee=user.get("is_employee"),
            resume_url=user.get("filter_url"),
            filter_url=user.get("filter_url"),
            filter_data=user.get("filter_data", {})
        )
        await queue.put(user_model)

    await queue.join()

    _, not_done = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)

    for task in not_done:
        task.cancel()


if __name__ == "__main__":
    # For tests only
    # loop = asyncio.get_event_loop()
    # loop.create_task(prepare_task())
    # loop.run_forever()

    prepare_task.start()
    asyncio.get_event_loop().run_forever()
