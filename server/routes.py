from aiohttp import web
from aiojobs.aiohttp import setup, spawn


async def start_task(request: web.Request) -> web.Response:
    pass


async def get_active_tasks(request: web.Request) -> web.Response:
    pass


async def cancel_task(request: web.Request) -> web.Response:
    pass


async def restart_task(request: web.Request) -> web.Response:
    pass
