from datetime import datetime, timedelta
from jose import JWTError, jwt
from passlib.context import CryptContext
from config import settings 
from auth import token_schema
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from database import AsyncSessionLocal
from models import db_models
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import asyncio

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password: str, hash_password: str):
    return pwd_context.verify(plain_password, hash_password)

def hash_password(plain_password: str):
    return pwd_context.hash(plain_password)

def create_access_token(data: dict):
    expire = datetime.now() + timedelta(seconds=settings.ACCESS_TOKEN_EXPIRE)

    data_copy = data.copy()
    to_encode = token_schema.Access_Token_Payload(
        sub=data_copy["sub"],
        type="access",
        exp=expire
    )

    encoded_jwt = jwt.encode(
        to_encode.model_dump(),
        settings.JWT_ACCESS_SECRET_KEY,
        settings.JWT_ALGORITHM
    )

    return encoded_jwt

def create_refresh_token(data: dict):
    expire = datetime.now() + timedelta(seconds=settings.REFRESH_TOKEN_EXPIRE)

    data_copy = data.copy()
    to_encode = token_schema.Refresh_Token_Payload(
        sub=data_copy["sub"],
        session_id=data_copy["session_id"],
        type="refresh",
        exp=expire
    )

    encoded_jwt = jwt.encode(
        to_encode.model_dump(),
        settings.JWT_REFRESH_SECRET_KEY,
        settings.JWT_ALGORITHM
    )

    return encoded_jwt

def verify_access_token(token: str):
    try: 
        payload = jwt.decode(
            token,
            settings.JWT_ACCESS_SECRET_KEY,
            [settings.JWT_ALGORITHM]
        )

        if payload.get("type") != "access":
            return None
        
        return payload
    
    except JWTError:
        return None
    
def verify_refresh_token(token: str):
    try:
        payload = jwt.decode(
            token,
            settings.JWT_REFRESH_SECRET_KEY,
            [settings.JWT_ALGORITHM]
        )

        if payload.get("type") != "refresh":
            return None

        return payload
    
    except JWTError:
        return None

async def cleanup_expired_tokens():
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            delete(db_models.UserTokens)
            .where(db_models.UserTokens.expires_at < datetime.now())
        )

        await db.commit()
        print(f"24 hour routine token clean up complete. Cleaned up {result.rowcount} expired tokens")


scheduler = AsyncIOScheduler()
scheduler.add_job(
    lambda: asyncio.create_task(cleanup_expired_tokens()),
    'interval',
    hours=24
)

