import base64
from cryptography import fernet

from aiohttp import web
from aiohttp_session import get_session
from aiohttp_session import session_middleware
from aiohttp_session import setup as aiohttp_session_setup
from aiohttp_session.cookie_storage import EncryptedCookieStorage

from aiojobs.aiohttp import setup as aiojobs_setup

from server.routes import start_task, get_active_tasks, cancel_tasks, restart_tasks


def setup_server() -> web.Application:
    web_app = web.Application()

    # Setup session
    fernet_key = fernet.Fernet.generate_key()
    secret_key = base64.urlsafe_b64decode(fernet_key)
    aiohttp_session_setup(web_app, EncryptedCookieStorage(secret_key))

    # Setup aiojobs
    aiojobs_setup(web_app)

    return web_app


async def setup_routes(web_app: web.Application) -> web.Application:
    web_app.router.add_post("/start-task", start_task)
    web_app.router.add_get("/cancel-task", cancel_tasks)
    web_app.router.add_get("/restart-task", restart_tasks)
    web_app.router.add_get("/active-tasks", get_active_tasks)

    return web_app


if __name__ == "__main__":
    app = setup_server()
    app = setup_routes(app)
    web.run_app(app)
