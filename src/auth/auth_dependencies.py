from fastapi import Depends, HTTPException, status, Request, Response
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from database.database import get_db
from models import db_models
from config.config import settings
from repository import focal_repositories
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from auth import auth_security, token_schema
from exceptions import ExceptionDict
from datetime import datetime, timedelta
import secrets

security = HTTPBearer()
exc = ExceptionDict()

async def get_current_user(request: Request, db: AsyncSession = Depends(get_db)):
    access_token = request.cookies.get("access_token")
    if not access_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Access token missing from headers",
            headers={"WWW-Authenticate": "Bearer"},
        )
    payload = auth_security.verify_access_token(access_token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Access token not valid",
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
    elif "ADMIN" in user_id:
        result = await db.execute(
            select(db_models.AdminAccount)
            .where(db_models.AdminAccount.user_id == user_id)
        )
    user = result.scalar_one_or_none()
    if user is None:
        raise exc.get("AccountNotFound")
    return user


async def create_tokens(
    db: AsyncSession, 
    request: Request, 
    response: Response, 
    user_id: str
):
    access_token = auth_security.create_access_token(data={"sub": user_id})
    session_id = secrets.token_urlsafe(48)
    refresh_token = auth_security.create_refresh_token(data={
        "sub": user_id,
        "session_id": session_id
    })

    hashed_refresh_token = auth_security.hash_password(refresh_token)
    expire = datetime.now() + timedelta(seconds=settings.REFRESH_TOKEN_EXPIRE)

    db_refresh_token = db_models.UserTokens(
        ip_address=request.state.real_ip,
        user_id=user_id,
        token=hashed_refresh_token,
        expires_at=expire,
        session_id=session_id
    )

    await focal_repositories.push_specific(db, db_refresh_token)

    # response.set_cookie(
    #     key="access_token",
    #     value=access_token,
    #     #httponly=True,
    #     httponly=False,
    #     max_age=settings.ACCESS_TOKEN_EXPIRE,
    #     #secure=True,  # True in production (HTTPS only)
    #     secure=False,  # True in production (HTTPS only)
    #     #samesite="lax",
    #     samesite="lax",
    #     path="/",
    #     domain="localhost" 
    # )
    # response.set_cookie(
    #     key="refresh_token",
    #     value=refresh_token,
    #     #httponly=True,
    #     httponly=False,
    #     max_age=settings.REFRESH_TOKEN_EXPIRE,
    #     #secure=True,
    #     secure=False,
    #     #samesite="lax",
    #     samesite="lax",
    #     path="/auth" ,
    #     domain="localhost" 
    # )

    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        max_age=settings.ACCESS_TOKEN_EXPIRE,
        secure=False,              # MUST be true on https
        samesite="Lax",          # required for cross-site cookies
        path="/",
    )

    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        max_age=settings.REFRESH_TOKEN_EXPIRE,
        secure=False,              # MUST be true on https
        samesite="Lax",          # required for cross-site cookies
        path="/auth",
    )

    token_response = token_schema.TokenData(
        access_token=access_token,
        token_type="Bearer",
        user_id=user_id
    )
    return token_response

async def create_login_token(response: Response,  identifier: str):
    login_token = auth_security.create_login_access_token({"sub": identifier})
    expire = datetime.now() + timedelta(seconds=settings.LOGIN_ACCESS_TOKEN_EXPIRE)

    response.set_cookie(
        key="login_access_token",
        value=login_token,
        httponly=True,
        max_age=expire,
        secure=False,              # MUST be true on https
        samesite="Lax",          # required for cross-site cookies
        path="/",
    )
    return token_schema.LoginTokenData(
        login_token=login_token,
        token_type="Bearer",
        identifier=identifier
    )


async def create_login_restrict_token(response: Response,  identifier: str, expire: int):
    login_restrict_token = auth_security.create_login_restrict_token({"sub": identifier, "expire": expire})
    response.set_cookie(
        key="login_restrict_token",
        value=login_restrict_token,
        httponly=True,
        max_age=expire,
        secure=False,              # MUST be true on https
        samesite="Lax",          # required for cross-site cookies
        path="/",
    )
    return token_schema.LoginTokenData(
        login_token=login_restrict_token,
        token_type="Bearer",
        identifier=identifier
    )

