import asyncio
import asyncpg
from core import config


class Database:

    def __init__(self, loop: asyncio.AbstractEventLoop) -> None:
        self._pool = loop.run_until_complete(
            asyncpg.create_pool(
                user=config.DB_USER,
                password=config.DB_PASSWORD,
                host=config.DB_HOST,
                port=config.DB_PORT,
                database=config.DB_NAME
            )
        )

    @property
    def pool(self) -> asyncpg.Connection:
        return self._pool

    def __repr__(self):
        return f'{self.__class__.__name__} <id: {id(self)}>'
