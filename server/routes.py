from aiohttp import web
from aiojobs.aiohttp import spawn

from server.tasks import get_all_tasks_names, cancel_task
from scrapper.workers.vacancies import prepare_task


async def start_task(request: web.Request) -> web.Response:
    await spawn(request, prepare_task(**await request.json()))
    return web.Response(status=201)


async def get_active_tasks(request: web.Request) -> web.Response:
    return web.json_response({"tasks": await get_all_tasks_names()}, status=201)


async def cancel_tasks(request: web.Request) -> web.Response:
    jdata = await request.json()
    status = await cancel_task(jdata['task_name'])
    return web.Response(status=201 if status else 400)


async def restart_tasks(request: web.Request) -> web.Response:
    pass
