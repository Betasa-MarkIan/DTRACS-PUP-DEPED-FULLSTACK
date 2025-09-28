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
