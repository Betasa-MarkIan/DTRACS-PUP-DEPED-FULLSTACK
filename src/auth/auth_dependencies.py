from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from database.database import get_db
from models import db_models
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from auth import auth_security

security = HTTPBearer()

async def get_current_user(
    #request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
):
    # access_token = request.cookies.get("access_token")
    # if not access_token:
    #     raise HTTPException(
    #         status_code=status.HTTP_401_UNAUTHORIZED,
    #         detail="Could not validate credentials",
    #         headers={"WWW-Authenticate": "Bearer"},
    #     )
    token = credentials.credentials
    payload = auth_security.verify_access_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = payload.get("sub")

    if "SCHOOL" in user_id:
        result = await db.execute(
            select(db_models.SchoolAccountsVerified)
            .where(db_models.SchoolAccountsVerified.user_id == user_id)
        )
    
    elif "FOCAL" in user_id:
        result = await db.execute(
            select(db_models.FocalAccountsVerified)
            .where(db_models.FocalAccountsVerified.user_id == user_id)
        )

    else:
        result = await db.execute(
            select(db_models.AdminAccount)
            .where(db_models.AdminAccount.user_id == user_id)
        )

    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )
    
    return user


# DELETE FROM dtracs_database.user_tokens WHERE user_id = 'FOCAL-0003' AND expires_at < NOW();

