import asyncio

from scrapper.exceptions import TaskNotFound
from scrapper.loader import logger

from scrapper.worker import loop


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
