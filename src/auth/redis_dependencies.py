from fastapi import Depends, HTTPException, status
from fastapi.responses import JSONResponse
import redis.asyncio as redis
from database.redis import get_redis_client
import time
import math

class BlacklistedUsers:
    def __init__(self, redis_client: redis.Redis):
       self.redis = redis_client
    
    async def add_blacklist(
        self,
        login_restrict_token: str,
        client_ip: str,
        retry_after: int
    ):
        current_time = time.time()
        identifier_key = f"{client_ip}:{login_restrict_token}"
        key = f"blacklisted:{identifier_key}"
        expires_at = current_time + retry_after
        remaining_time = retry_after
        await self.redis.setex(key, retry_after, expires_at)
        return {"status": "blacklisted", "retry_after": remaining_time, "user": key}

class SlidingWindowRateLimiter:
    def __init__(self, redis_client: redis.Redis):
       self.redis = redis_client

    async def check_rate_limit(
        self, 
        client_ip: str,
        token_identifier: str,
        max_requests: int = 5, 
        window_seconds: int = 100
    ) -> dict:

        current_time = time.time()
        window_start = current_time - window_seconds
        identifier = f"{client_ip}:{token_identifier}"
        key = f"rate_limit:login:{identifier}"
        
        await self.redis.zremrangebyscore(key, 0, window_start)
        current_requests = await self.redis.zcard(key)

        if current_requests >= max_requests - 1:
            oldest_entry = await self.redis.zrange(key, 0, 0, withscores=True)
            if oldest_entry:
                oldest_time = oldest_entry[0][1]
                retry_after = int(math.ceil(oldest_time + window_seconds - current_time))
            else:
                retry_after = window_seconds

            return {
                "status": "blacklisted",
                "current_requests": current_requests+1,
                "max_requests": max_requests,
                "retry_after": retry_after,
                "window_seconds": window_seconds
            }

        member = f"{identifier}:{time.time_ns()}"
        await self.redis.zadd(key, {member: current_time})
        if current_requests == 0:
            await self.redis.expire(key, window_seconds)
        
        return {
                "status": "whitelisted",
                "current_requests": current_requests + 1,
                "max_requests": max_requests,
                "retry_after": 0,
                "window_seconds": window_seconds
            } 

async def get_rate_limiter(redis_client: redis.Redis = Depends(get_redis_client)) -> SlidingWindowRateLimiter:
    return SlidingWindowRateLimiter(redis_client)

async def get_blacklist_status(redis_client: redis.Redis = Depends(get_redis_client)) -> BlacklistedUsers:
    return BlacklistedUsers(redis_client)

async def get_rate_info(rate_limit_info: dict):
    time_val = rate_limit_info["retry_after"]
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

    return JSONResponse(
        status_code=status.HTTP_401_UNAUTHORIZED,
        content={
            "error": "Login rate limit exceeded",
            "message": f"Too many login attempts. Try again in {retry_after} minute/s",
            "sliding_window": True,
            "current_attempts": rate_limit_info["current_requests"],
            "max_attempts": rate_limit_info["max_requests"],
            "retry_after": retry_after
        }
    )
