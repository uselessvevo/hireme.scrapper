import base64
from cryptography import fernet

from aiohttp import web
from aiohttp_session import setup, get_session, session_middleware
from aiohttp_session.cookie_storage import EncryptedCookieStorage

from server.routes import start_task, get_active_tasks, cancel_task, restart_task


async def setup_server() -> web.Application:
    web_app = web.Application()

    fernet_key = fernet.Fernet.generate_key()
    secret_key = base64.urlsafe_b64decode(fernet_key)
    setup(web_app, EncryptedCookieStorage(secret_key))

    return web_app


async def setup_routes(web_app: web.Application) -> None:
    web_app.router.add_get("/start-task", start_task)
    web_app.router.add_get("/cancel-task", cancel_task)
    web_app.router.add_get("/restart-task", restart_task)
    web_app.router.add_get("/active-tasks", get_active_tasks)


if __name__ == "__main__":
    app = setup_server()
    web.run_app(app)

