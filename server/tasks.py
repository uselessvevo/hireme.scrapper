import asyncio

from scrapper.loader import logger


async def get_all_tasks_names() -> list[str]:
    return list(i.get_name() for i in asyncio.all_tasks(asyncio.get_event_loop()) if i.done())


async def get_task_by_name(task_name: str) -> asyncio.Task:
    tasks = asyncio.all_tasks(asyncio.get_event_loop())
    for task in tasks:
        if task.get_name() == task_name:
            if task.done():
                return task


async def cancel_task(task_name: str) -> bool:
    task = await get_task_by_name(task_name)
    if not task:
        return False

    if not task.cancelled():
        task.cancel()
        return True
    else:
        logger.warning("Task %s already canceled" % task_name)
        return False
