from fastapi import APIRouter, Request, Response, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from exceptions import ExceptionDict
from database import get_db
from repository import focal_repositories
from models import db_models
from config import settings
from datetime import datetime, timedelta
from auth import auth_security, token_schema
from auth.auth_dependencies import get_current_user
from typing import Any
import secrets

router = APIRouter(prefix="/auth", tags=["authentication"])
exc = ExceptionDict()

# TODO: Add admin to auth

@router.post("/refresh", status_code=status.HTTP_200_OK)
async def refresh_access_token(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db)
) -> token_schema.TokenData:
    
    refresh_token = request.cookies.get("refresh_token")
    if not refresh_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token missing")
    
    payload = auth_security.verify_refresh_token(refresh_token)
    if not payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token missing")
    
    user_id = payload.get("sub")
    session_id = payload.get("session_id")
    
    result = await db.execute(
            select(db_models.UserTokens)
            .where(db_models.UserTokens.user_id == user_id)
            .where(db_models.UserTokens.session_id == session_id)
        )
    
    stored_token = result.scalar_one_or_none()
    if stored_token is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token revoked")
    
    if stored_token.expires_at < datetime.now():
        await db.delete(stored_token)
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail="Refresh token expired"
        )

    new_tokens = await create_tokens(db, request, response, user_id)

    await db.delete(stored_token)
    await db.commit()
    
    if auth_security.verify_password(refresh_token, stored_token.token):
        await db.delete(stored_token)


    return new_tokens







# @router.post("/school/login", status_code=status.HTTP_200_OK)
# async def login (
#     request: Request,
#     response: Response,
#     login_data: school_schemas.SchoolAccountLoginSchema,
#     db: AsyncSession = Depends(get_db)
# ) -> token_schema.TokenData:

#     """
#     school information will no longer come from the logins
#     """ 

#     result = await db.execute(
#         select(db_models.SchoolAccountsVerified)
#         .where(db_models.SchoolAccountsVerified.email == login_data.email)
#     )

#     school_account = result.scalar_one_or_none()

#     if school_account is None or not security.verify_password(login_data.password, school_account.password):
#         raise HTTPException(
#             status_code=status.HTTP_401_UNAUTHORIZED,
#             detail="Incorrect email or password",
#             headers={"WWW-Authenticate": "Bearer"},
#         )

#     access_token = security.create_access_token(data={"sub": school_account.user_id})
#     session_id = secrets.token_urlsafe(48)
#     refresh_token = security.create_refresh_token(data={
#         "sub": school_account.user_id,
#         "session_id": session_id
#     })

#     hashed_refresh_token = security.hash_password(refresh_token)
#     expire = datetime.now() + timedelta(seconds=settings.REFRESH_TOKEN_EXPIRE)

#     db_refresh_token = db_models.SchoolTokens(
#         ip_address=request.state.real_ip,
#         school_id=school_account.user_id,
#         token=hashed_refresh_token,
#         expires_at=expire,
#         session_id=session_id
#     )

#     await focal_repositories.push_specific(db, db_refresh_token)

#     response.set_cookie(
#         key="access_token",
#         value=access_token,
#         httponly=True,
#         expires=settings.ACCESS_TOKEN_EXPIRE,
#         secure=not settings.DEBUG,  # True in production (HTTPS only)
#         samesite="lax",
#         path="/"
#     )
#     response.set_cookie(
#         key="refresh_token",
#         value=refresh_token,
#         httponly=True,
#         expires=settings.REFRESH_TOKEN_EXPIRE,
#         secure=not settings.DEBUG,
#         samesite="lax",
#         path="/auth/refresh"  # Only sent to the refresh endpoint!
#     )

#     token_response = token_schema.TokenData(
#         access_token=access_token,
#         token_type="Bearer",
#         user_id=school_account.user_id
#     )

#     return token_response


@router.post("/login", status_code=status.HTTP_200_OK)
async def login (
    request: Request,
    response: Response,
    login_data: token_schema.Login,
    db: AsyncSession = Depends(get_db)
) -> token_schema.TokenData:

    """
    user information will no longer come from the logins
    """ 
    result = await db.execute(
        select(db_models.SchoolAccountsVerified)
        .where(db_models.SchoolAccountsVerified.email == login_data.email)
    )
    account = result.scalar_one_or_none()
    
    if account is None:
        result = await db.execute(
        select(db_models.FocalAccountsVerified)
        .where(db_models.FocalAccountsVerified.email == login_data.email)
        )
        account = result.scalar_one_or_none()
    
    elif account is None:
        result = await db.execute(
        select(db_models.AdminAccount)
        .where(db_models.AdminAccount.email == login_data.email)
        )
        account = result.scalar_one_or_none()

    if account is None or not auth_security.verify_password(login_data.password, account.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    generate_tokens = await create_tokens(db, request, response, account.user_id)

    return generate_tokens


@router.post("/logout", status_code=status.HTTP_200_OK)
async def logout(
    request: Request,
    response: Response,
    current_user: Any = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    refresh_token = request.cookies.get("refresh_token")
    if refresh_token:

        decoded_refresh_token = auth_security.verify_refresh_token(refresh_token)
        result = await db.execute(
            select(db_models.UserTokens)
            .where(db_models.UserTokens.user_id == current_user.user_id)
            .where(db_models.UserTokens.session_id == decoded_refresh_token["session_id"])
        )

        user = result.scalar_one_or_none
        if user is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token revoked")
        
        if auth_security.verify_password(refresh_token, user.token):
            await db.delete(user)
        
        await db.commit()

    response.delete_cookie("access_token", path="/")
    response.delete_cookie("refresh_token", path="/auth/refresh")

    return {"message": "Successfully logged out"}

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

    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        expires=settings.ACCESS_TOKEN_EXPIRE,
        secure=not settings.DEBUG,  # True in production (HTTPS only)
        samesite="lax",
        path="/"
    )
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        expires=settings.REFRESH_TOKEN_EXPIRE,
        secure=not settings.DEBUG,
        samesite="lax",
        path="/auth/refresh"  # Only sent to the refresh endpoint!
    )

    token_response = token_schema.TokenData(
        access_token=access_token,
        token_type="Bearer",
        user_id=user_id
    )

    return token_response

"""
Add condition, when user is deleted, token should be deleted as well
"""