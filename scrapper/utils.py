from core import config


async def remove_user_session_folder(user_id: int) -> None:
    (config.BASE_DIR / "session" / str(user_id)).rmdir()
