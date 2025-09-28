from config.config import settings
import redis.asyncio as redis

async def get_redis_client() -> redis.Redis:
    return redis.from_url(f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}", decode_responses=True)

# async def get_redis_client() -> redis.Redis:
#     return redis.from_url(settings.REDIS_URL, decode_responses=True)




