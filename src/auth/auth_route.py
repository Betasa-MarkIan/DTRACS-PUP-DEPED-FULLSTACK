from fastapi import APIRouter, Request, Response, Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from exceptions import ExceptionDict
from database.database import get_db
from database.redis import get_redis_client
from models import db_models
from schema import db_response
from auth import auth_security, token_schema, redis_dependencies, auth_dependencies
from typing import Any
from datetime import datetime
from sqlalchemy import select, union_all
from models.db_models import AdminAccount, SchoolAccountsVerified, FocalAccountsVerified
import logging

exc = ExceptionDict()
security = HTTPBearer()
logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["authentication"])

@router.get("/proxy/get/current/user", status_code=status.HTTP_200_OK)
async def get_user(user_id: str, db: AsyncSession = Depends(get_db)):
    """Proxy route for retrieving  user information"""
    try:
        get_user = union_all(
            (select(AdminAccount.user_id).where(AdminAccount.user_id == user_id)),
            (select(SchoolAccountsVerified.user_id).where(SchoolAccountsVerified.user_id == user_id)),
            (select(FocalAccountsVerified.user_id).where(FocalAccountsVerified.user_id == user_id)),
        ).alias("get_user")
        
        result = await db.execute(select(get_user))
        user_id = result.scalar_one_or_none()
    except Exception as e:
        raise exc.get("DatabaseError", error=e)

    if "SCHOOL" in user_id:
        result = await db.execute(select(SchoolAccountsVerified).where(SchoolAccountsVerified.user_id == user_id))
        user = result.scalar_one_or_none()
        json_response = db_response.SchoolResponse.model_validate(user)
    elif "FOCAL" in user_id:
        result = await db.execute(select(FocalAccountsVerified).where(FocalAccountsVerified.user_id == user_id))
        user = result.scalar_one_or_none()
        json_response = db_response.FocalResponse.model_validate(user)
    elif "ADMIN" in user_id:
        result = await db.execute(select(AdminAccount).where(AdminAccount.user_id == user_id))
        user = result.scalar_one_or_none()
        json_response = db_response.AdminResponse.model_validate(user)

    return json_response

@router.get("/get/current/user", status_code=status.HTTP_200_OK)
async def get_user(current_user: Any = Depends(auth_dependencies.get_current_user)):
    if "SCHOOL" in current_user.user_id:
        json_response = db_response.SchoolResponse.model_validate(current_user)
    elif "FOCAL" in current_user.user_id:
        json_response = db_response.FocalResponse.model_validate(current_user)
    elif "ADMIN" in current_user.user_id:
        json_response = db_response.AdminResponse.model_validate(current_user)
    return json_response

@router.post("/refresh", status_code=status.HTTP_200_OK)
async def refresh_access_token(
    request: Request,
    response: Response,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> token_schema.TokenData:
    
    refresh_token = request.cookies.get("refresh_token")
    if not refresh_token:
        refresh_token = credentials.credentials
    if not refresh_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token missing from headers")
    payload = auth_security.verify_refresh_token(refresh_token)
    if not payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")
    
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
    new_tokens = await auth_dependencies.create_tokens(db, request, response, user_id)
    if auth_security.verify_password(refresh_token, stored_token.token):
        await db.delete(stored_token)
        await db.commit()

    return new_tokens

@router.post("/login", status_code=status.HTTP_200_OK)
async def login (
    request: Request,
    response: Response,
    login_data: token_schema.Login,
    db: AsyncSession = Depends(get_db),
    rate_limiter: redis_dependencies.SlidingWindowRateLimiter = Depends(redis_dependencies.get_rate_limiter),
    blacklist: redis_dependencies.BlacklistedUsers = Depends(redis_dependencies.get_blacklist_status)
) -> token_schema.TokenData | dict:

    """Rate limiting logic"""
    client_ip = request.state.real_ip
    login_access_token = request.cookies.get("login_access_token")
    if not login_access_token:
        login_access_token = await auth_dependencies.create_login_token(response, client_ip)

    rate_limit = await rate_limiter.check_rate_limit(client_ip, login_access_token)
    if rate_limit["status"] == "blacklisted":
        response.delete_cookie("login_access_token", path="/")
        login_restrict_token = await auth_dependencies.create_login_restrict_token(response, client_ip, rate_limit["retry_after"])
        await blacklist.add_blacklist(login_restrict_token, client_ip, rate_limit["retry_after"])
        return await redis_dependencies.get_rate_info(rate_limit)

    """User info query logic"""
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
    if account is None:
        result = await db.execute(
        select(db_models.AdminAccount)
        .where(db_models.AdminAccount.email == login_data.email)
        )
        account = result.scalar_one_or_none()
    if account is None or not auth_security.verify_password(login_data.password, account.password):
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={
                "detail": "Incorrect email or password"
            }
        )
            
    """Whitelist after successfull login"""
    identifier = f"{client_ip}:{login_access_token}"
    key = f"rate_limit:login:{identifier}"
    try: 
        await (await get_redis_client()).delete(key)
        response.delete_cookie("login_access_token", path="/")
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Key not in cache memory",
        )
    
    """Generate access/refresh tokens"""
    generate_tokens = await auth_dependencies.create_tokens(db, request, response, account.user_id)
    return generate_tokens

@router.post("/logout", status_code=status.HTTP_200_OK)
async def logout(
    request: Request,
    response: Response,
    current_user: Any = Depends(auth_dependencies.get_current_user),
    db: AsyncSession = Depends(get_db)
):
    refresh_token = request.cookies.get("refresh_token")
    if not refresh_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token missing")
    
    decoded_refresh_token = auth_security.verify_refresh_token(refresh_token)
    result = await db.execute(
        select(db_models.UserTokens)
        .where(db_models.UserTokens.user_id == current_user.user_id)
        .where(db_models.UserTokens.session_id == decoded_refresh_token["session_id"])
    )

    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token revoked")
    if not auth_security.verify_password(refresh_token, user.token):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token database mismatch")
    
    await db.delete(user)
    await db.commit()
    response.delete_cookie("access_token", path="/")
    response.delete_cookie("login_access_token", path="/")
    response.delete_cookie("refresh_token", path="/auth")
    return {"message": "Successfully logged out"}
