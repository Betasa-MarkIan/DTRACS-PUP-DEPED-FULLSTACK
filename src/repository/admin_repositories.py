from passlib.context import CryptContext
from datetime import datetime, timedelta
from exceptions import ExceptionRaised, ExceptionDict
from models import db_models
from schema import admin_schemas
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import Any

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
exc = ExceptionDict()


async def push_specific(db: AsyncSession, obj: Any):
    try:
        db.add(obj)
        await db.commit()
        await db.refresh(obj)
    
    except Exception as e:
        await db.rollback()
        raise exc.get("DatabaseError", error=e)
    
    return obj

async def push_commit(db: AsyncSession, obj: Any):
    try:
        await db.commit()
        await db.refresh(obj)

    except Exception as e:
        await db.rollback()
        raise exc.get("DatabaseError", error=e)
    
    return obj

async def push_delete(db: AsyncSession, obj: Any):
    try:
        await db.delete(obj)
        await db.commit()

    except Exception as e:
        await db.rollback()
        raise exc.get("DatabaseError", error=e)
    
    return obj

async def push_delete_tokens(db: AsyncSession, user_id: str):
    await db.execute(delete(db_models.UserTokens).where(db_models.UserTokens.user_id == user_id))
    await db.commit()
    
    return None


async def verify_login(db: AsyncSession, login: admin_schemas.AdminLoginSchema):
    ATTEMPT_LIMIT = 5
    LOCK_TIME = timedelta(minutes=3)

    result = await db.execute(
        select(db_models.AdminAccount)
        .where(db_models.AdminAccount.email == login.email)
    )
    account = result.scalar_one_or_none()

    if account is None:
        raise exc.get("AccountNotFound")
    
    if account.lock_until and account.lock_until > datetime.now():
        raise ExceptionRaised(detail=f"Admin account temporarily locked ({account.lock_until - datetime.now()}). Try again later")
    
    if not pwd_context.verify(login.password, account.password):
        account.failed_login_attempt +=1

        if account.failed_login_attempt >= ATTEMPT_LIMIT:
            account.lock_until = datetime.now() + LOCK_TIME
            account.failed_login_attempt = 0

        await db.commit()
        raise exc.get("InvalidCredentials")
    
    account.failed_login_attempt = 0

    try:
        await db.commit()
        await db.refresh(account)

    except Exception as e:
        await db.rollback()
        raise exc.get("DatabaseError", error=e)
        
    return account






