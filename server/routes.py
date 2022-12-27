from aiohttp import web
from aiojobs.aiohttp import spawn
from scrapper.worker import prepare_task


async def start_task(request: web.Request) -> web.Response:
    await spawn(request, prepare_task(**await request.json()))
    return web.Response(status=201)


async def get_active_tasks(request: web.Request) -> web.Response:
    pass


async def cancel_task(request: web.Request) -> web.Response:
    pass


async def restart_task(request: web.Request) -> web.Response:
    pass
