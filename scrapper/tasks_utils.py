import asyncio

from scrapper.exceptions import TaskNotFound
from scrapper.loader import logger


async def get_all_tasks_names() -> set[str]:
    return set(i.get_name() for i in asyncio.all_tasks(asyncio.get_event_loop()))


async def get_task_by_name(task_name: str) -> asyncio.Task:
    tasks = asyncio.all_tasks(asyncio.get_event_loop())
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
