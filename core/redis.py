from typing import Any
import aioredis

from core.config import REDIS_PROT, REDIS_HOST, REDIS_PORT


async def get_redis() -> aioredis.StrictRedis:
    return aioredis.from_url("%s://%s:%s" % (REDIS_PROT, REDIS_HOST, REDIS_PORT))


async def publish_user_message(
    user,
    message: Any,
    message_type: str = "default",
    prefix: str = None
) -> None:
    redis = await get_redis()
    prefix = "%s_" % prefix if prefix else ""
    await redis.publish("%s%s:%s" % (prefix, user.curator_id, user.id), message)
