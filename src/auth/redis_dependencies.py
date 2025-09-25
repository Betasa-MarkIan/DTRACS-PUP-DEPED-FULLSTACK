from fastapi import Depends
import redis.asyncio as redis
import time
from fastapi import HTTPException, status, Request
from database.redis import get_redis_client
from typing import Any
from uuid import uuid4


class SlidingWindowRateLimiter:
    def __init__(self, redis_client: redis.Redis):
       self.redis = redis_client

    async def check_rate_limit(self, identifier: str, max_requests: int, window_seconds: int) -> dict[str, Any]:

        blacklist = await get_blacklist_status(self.redis).blacklisting(identifier, window_seconds)
        if blacklist["status"] == "blacklisted":
            return {
                "allowed": False,
                "current_requests": 0,
                "max_requests": max_requests,
                "retry_after": blacklist["retry_after"],
                "window_seconds": window_seconds
            }
        
        current_time = time.time()
        window_start = current_time - window_seconds
        key = f"rate_limit:login:{identifier}"

        await self.redis.zremrangebyscore(key, 0, window_start)
        current_requests = await self.redis.zcard(key)

        if current_requests >= max_requests:
            oldest_entry = await self.redis.zrange(key, 0, 0, withscores=True)
            if oldest_entry:
                oldest_time = oldest_entry[0][1]
                retry_after = int(oldest_time + window_seconds - current_time)

            else:
                retry_after = window_seconds
            
            minutes = round(retry_after/60)
            seconds = retry_after%60
            retry_after = f"{minutes}:{seconds}"
            await get_blacklist_status(self.redis).blacklisting(identifier, retry_after)

            return {
                "allowed": False,
                "current_requests": current_requests,
                "max_requests": max_requests,
                "retry_after": retry_after,
                "window_seconds": window_seconds
            } 
        
        await self.redis.zadd(key, {f"{current_time}:{uuid4()}": current_time})
        await self.redis.expire(key, window_seconds)

        return {
                "allowed": True,
                "current_requests": current_requests + 1,
                "max_requests": max_requests,
                "retry_after": 0,
                "window_seconds": window_seconds
            } 


class BlacklistedUsers:
    def __init__(self, redis_client: redis.Redis):
       self.redis = redis_client

    async def blacklisting(self, identifier: str, retry_after: int | None = None):
        current_time = time.time()
        key = f"blacklisted:{identifier}"
        remaining_time = int(retry_after + current_time)

        already_exist = await self.redis.zscore(key, identifier)
        if already_exist:
            if current_time > already_exist:
                await self.redis.zrem(key, identifier)  

                return {"status": "whitelisted", "retry_after": 0,"user": identifier} 
            
            else:
                remaining_time = int(retry_after + current_time)
                return {"status": "blacklisted", "retry_after": remaining_time, "user": identifier} 

        await self.redis.zadd(key, {identifier: remaining_time})
        await self.redis.expire(key, retry_after)

        return {"status": "blacklisted", "retry_after": retry_after, "user": identifier} 


async def get_rate_limiter(redis_client: redis.Redis = Depends(get_redis_client)) -> SlidingWindowRateLimiter:

    return SlidingWindowRateLimiter(redis_client)

async def get_blacklist_status(redis_client: redis.Redis = Depends(get_redis_client)) -> BlacklistedUsers:

    return BlacklistedUsers(redis_client)

async def sliding_window_rate_limit(
    request: Request,
    max_attempts: int = 10,
    window_seconds: int = 60 * 10, #10 minutes,
    rate_limiter: SlidingWindowRateLimiter = Depends(get_rate_limiter)
):
    client_ip = request.state.real_ip
    result = await rate_limiter.check_rate_limit(client_ip, max_attempts, window_seconds)

    if not result["allowed"]:
        result["retry_after"]

        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "error": "Rate limit exceeded",
                "message": f"Too many login attempts. Try again in {result['retry_after']} seconds",
                "sliding_window": True,
                "current_attempts": result["current_requests"],
                "max_attempts": result["max_requests"],
                "retry_after": result["retry_after"],
                "window_seconds": window_seconds
            }
        )
    
    return result












