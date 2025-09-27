from fastapi import Depends
import redis.asyncio as redis
import time
from fastapi import HTTPException, status, Request
from database.redis import get_redis_client
from typing import Any
import math


class BlacklistedUsers:
    def __init__(self, redis_client: redis.Redis):
       self.redis = redis_client

    async def blacklisting(self, identifier: str, retry_after: int | None = None):
        current_time = time.time()
        key = f"blacklisted:{identifier}"
        blacklist_set_key = "blacklisted_users"

        if retry_after is None:
            expiry = await self.redis.get(key)
            
            if not expiry:
                return {"status": "whitelisted", "retry_after": 0, "user": identifier}
            
            expiry_float = float(expiry)
            if current_time > expiry_float:
                await self.redis.delete(key)
                await self.redis.srem(blacklist_set_key, identifier)
                return {"status": "whitelisted", "retry_after": 0, "user": identifier}
    
            remaining_time = max(0, int(expiry_float - current_time))
            return {"status": "blacklisted", "retry_after": remaining_time, "user": identifier}

        elif retry_after:
            expires_at = current_time + retry_after
            remaining_time = retry_after
            await self.redis.setex(key, retry_after, expires_at)
            await self.redis.sadd(blacklist_set_key, identifier)
            await self.redis.expire(blacklist_set_key, retry_after + 3600)
            return {"status": "blacklisted", "retry_after": remaining_time, "user": identifier}
        

async def get_blacklist_status(redis_client: redis.Redis = Depends(get_redis_client)) -> BlacklistedUsers:
    return BlacklistedUsers(redis_client)


class SlidingWindowRateLimiter:
    def __init__(self, redis_client: redis.Redis):
       self.redis = redis_client

    async def check_rate_limit(
        self, 
        identifier: str, 
        max_requests: int, 
        window_seconds: int,
        blacklist_checker: BlacklistedUsers
    ) -> dict[str, Any]:

        current_time = time.time()
        window_start = current_time - window_seconds
        key = f"rate_limit:login:{identifier}"

        blacklist = await blacklist_checker.blacklisting(identifier, retry_after=None)

        if blacklist["status"] == "blacklisted":
            return {
                "allowed": False,
                "current_requests": 0,
                "max_requests": max_requests,
                "retry_after": blacklist["retry_after"],
                "window_seconds": window_seconds
            }
        
        await self.redis.zremrangebyscore(key, 0, window_start)
        current_requests = await self.redis.zcard(key)

        if current_requests >= max_requests - 1:
            oldest_entry = await self.redis.zrange(key, 0, 0, withscores=True)
            if oldest_entry:
                oldest_time = oldest_entry[0][1]
                retry_after = int(math.ceil(oldest_time + window_seconds - current_time))
            else:
                retry_after = window_seconds
            
            await blacklist_checker.blacklisting(identifier, retry_after)

            return {
                "allowed": False,
                "current_requests": current_requests,
                "max_requests": max_requests,
                "retry_after": retry_after,
                "window_seconds": window_seconds
            } 
        
        member = f"{identifier}:{time.time_ns()}"
        await self.redis.zadd(key, {member: current_time})
        if current_requests == 0:
            await self.redis.expire(key, window_seconds)

        return {
                "allowed": True,
                "current_requests": current_requests + 1,
                "max_requests": max_requests,
                "retry_after": 0,
                "window_seconds": window_seconds
            } 


async def get_rate_limiter(redis_client: redis.Redis = Depends(get_redis_client)) -> SlidingWindowRateLimiter:
    return SlidingWindowRateLimiter(redis_client)


async def sliding_window_rate_limit(
    request: Request,
    max_attempts: int = 10,
    window_seconds: int = 60 * 10, 
    rate_limiter: SlidingWindowRateLimiter = Depends(get_rate_limiter),
    blacklist: BlacklistedUsers = Depends(get_blacklist_status)
):
    client_ip = request.state.real_ip
    result = await rate_limiter.check_rate_limit(client_ip, max_attempts, window_seconds, blacklist)

    time_val = result["retry_after"]
    minutes = time_val // 60
    seconds = time_val % 60
    retry_after = f"{minutes:02d}:{seconds:02d}"

    parts = retry_after.split(":")
    if len(parts) == 2:
        left, right = parts
        if len(left) == 1:
            left = f"0{left}"
        if len(right) == 1:
            right = f"0{right}"
        retry_after = f"{left}:{right}"

    if not result["allowed"]:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "error": "Rate limit exceeded",
                "message": f"Too many login attempts. Try again in {retry_after} minute/s",
                "sliding_window": True,
                "current_attempts": result["current_requests"],
                "max_attempts": result["max_requests"],
                "retry_after": retry_after,
                "window_seconds": window_seconds
            }
        )

    return {
        "allowed": result["allowed"],
        "current_requests": result["current_requests"],
        "max_requests": result["max_requests"],
        "retry_after": retry_after,
        "window_seconds": result["window_seconds"],
    }