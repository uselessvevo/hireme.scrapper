import copy
import random
import uuid
from contextlib import suppress
from pathlib import Path

import asyncio
import pyppeteer

from core.redis import publish_user_message
from core.database import DatabaseAsync
from core.config import PUPPETER_LAUNCH_SETTINGS
from scrapper.actions.filters import open_filter_page

from scrapper.structs import User
from scrapper.loader import logger
from scrapper.actions.auth import open_login_page, check_is_authorized


async def run_worker(queue: asyncio.Queue) -> None:
    logger.info(f"Queue: {id(queue)} {queue}")

    # Создаём или выбираем директорию с сессией пользователя

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
                await check_is_authorized(page, user_data, open_filter_page, open_login_page)
                await browser.close()

            except Exception as e:
                logger.critical("[%s] %s" % (user_data.id, str(e)))

            finally:
                logger.info("Done with queue for user %s" % user_data.id)
                queue.task_done()

    user_data_dir.rmdir()
    logger.info("Folder %s deleted" % user_data_dir.name)


async def prepare_task(
    curator_id: int,
    user_id: int,
) -> None:
    async with DatabaseAsync() as conn:
        user = await conn.fetchrow(
            """
            SELECT
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
                u.id = $1 AND "is_employee" IS FALSE
            ORDER BY
                u.id
            """,
            int(user_id),
        )
        if not user:
            await publish_user_message(user, "Не удалось найти фильтр, либо пользователя. %s" % user.resume_url)
            raise ValueError("User with id %s not found" % user_id)

    queue: asyncio.Queue = asyncio.Queue()
    task = asyncio.create_task(run_worker(queue))
    task.set_name("%s:%s" % (curator_id, user_id))

    user = dict(user)
    user_model: User = User(
        id=user.get("id"),
        curator_id=curator_id,
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

    task.cancel()
    await asyncio.gather(task, return_exceptions=True)


if __name__ == "__main__":
    # For tests only
    loop = asyncio.get_event_loop()
    loop.run_until_complete(prepare_task(curator_id=34320012, user_id=2))
