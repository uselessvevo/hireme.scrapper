import random
from pathlib import Path

import asyncio
import pyppeteer

from scrapper.exceptions import TaskNotFound
from scrapper.loader import db, logger
from scrapper.structs import User
from core.config import PUPPETER_LAUNCH_SETTINGS
from scrapper.actions.auth import check_is_authorized


async def spawn_scrapper_worker(queue: asyncio.Queue) -> None:
    logger.info(f"Queue: {id(queue)} {queue}")
    user_data = await queue.get()

    # Создаём или выбираем директорию с сессией пользователя

    user_data_dir: Path = PUPPETER_LAUNCH_SETTINGS.get("userDataDir") / str(user_data.id)
    if not user_data_dir.exists():
        user_data_dir.mkdir()

    PUPPETER_LAUNCH_SETTINGS["userDataDir"] = str(user_data_dir)

    browser = await pyppeteer.launch(**PUPPETER_LAUNCH_SETTINGS)
    page = await browser.newPage()
    await page.setViewport({"width": 1920, "height": 1280})

    while True:
        try:
            await check_is_authorized(page, user_data)
            await asyncio.sleep(random.uniform(1, 1.5))
            await browser.close()

        except Exception as e:
            logger.critical("Error on %s. %s" % (queue, str(e)))

        finally:
            queue.task_done()
            logger.info("Done with queue - %s" % queue)


async def get_task_by_name(task_name: str) -> asyncio.Task:
    tasks = asyncio.all_tasks(loop)
    for task in tasks:
        if task.get_name() == task_name:
            return task


async def cancel_task(task_name: str) -> None:
    task = await get_task_by_name(task_name)
    if not task:
        raise TaskNotFound(task_name)

    if not task.cancelled():
        task.cancel()
    else:
        logger.warning("Task %s already canceled" % task_name)


async def prepare_scrapper_task(curator_id: int, user_id: int) -> None:
    # Get all users
    user = await db.pool.fetchrow(
        """
        SELECT
            u.id,
            u.email,
            u.firstname,
            u.middlename,
            u.patronymic,
            u.password,
            u.curator_id,
            f.filter_url
        FROM 
            users u
        JOIN
            filters f 
        ON 
            u.id = f.user_id
        WHERE
            u.id = $1 AND u.curator_id = $2 AND "is_employee" IS FALSE
        ORDER BY 
            u.id
        """,
        int(user_id),
        curator_id
    )
    if not user:
        raise ValueError("User with id %s not found" % user_id)

    queue: asyncio.Queue = asyncio.Queue()
    task = asyncio.create_task(spawn_scrapper_worker(queue))
    task.set_name("%s:%s" % (curator_id, user_id))

    user = dict(user)
    user_model: User = User(
        id=user.get("id"),
        curatorId=curator_id,  # user.get("curatorId"),
        firstname=user.get("firstname"),
        middlename=user.get("middlename"),
        patronymic=user.get("patronymic"),
        resumeUrl=user.get("resume_url"),
        email=user.get("email"),
        password=user.get("password"),
        isEmployee=user.get("is_employee"),
        resumeFilter=user.get("filter_url"),
    )
    await queue.put(user_model)
    await queue.join()

    task.cancel()
    await asyncio.gather(task, return_exceptions=True)


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(prepare_scrapper_task(curator_id=34320012, user_id=2))
