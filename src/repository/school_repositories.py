from sqlalchemy.ext.asyncio import AsyncSession
from models import db_models
from exceptions import ExceptionDict
from passlib.context import CryptContext
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Any

exc = ExceptionDict()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

async def create_school_request(db: AsyncSession, account_data: dict):
    new_account = db_models.SchoolAccountsRequest(**account_data)
    try:
        db.add(new_account)
        await db.commit()
        await db.refresh(new_account)
    except Exception as e:
        await db.rollback()
        raise exc.get("DatabaseError", error=e)
    return new_account

async def push_commit(db: AsyncSession, obj: Any):
    try:
        await db.commit()
        await db.refresh(obj)
    except Exception as e:
        await db.rollback()
        raise exc.get("DatabaseError", error=e)
    return obj
