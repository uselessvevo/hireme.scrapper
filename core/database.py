import typing
import asyncpg
from core import config


class DatabaseAsync:

    def __init__(
        self,
        user: str = config.DB_USER,
        password: str = config.DB_PASSWORD,
        host: str = config.DB_HOST,
        port: str = config.DB_PORT,
        database: str = config.DB_NAME,
        **connection_kwargs
    ) -> None:
        self._user: str = user
        self._password: str = password
        self._host: str = host
        self._port: str = port
        self._database: str = database
        self._connection_kwargs = connection_kwargs
        self._connection: typing.Union[typing.Coroutine, None] = None

    async def __aenter__(self) -> asyncpg.connection.Connection:
        self._connection = await asyncpg.connect(
            user=self._user,
            password=self._password,
            host=self._host,
            port=self._port,
            database=self._database,
            **self._connection_kwargs
        )
        return self._connection

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await self._connection.close()
