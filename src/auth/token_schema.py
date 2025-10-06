from pydantic import BaseModel
from datetime import datetime

class Access_Token_Payload(BaseModel):
    sub: str = None
    type: str = None
    exp: datetime = None

    class config:
        from_attributes=True

class Refresh_Token_Payload(BaseModel):
    sub: str = None
    session_id: str = None
    type: str = None
    exp: datetime = None

    class config:
        from_attributes=True

class TokenData(BaseModel):
    access_token: str
    token_type: str = "Bearer"
    user_id: str

class Login(BaseModel):
    """Schema for login."""
    email: str
    password: str

    class config:
        from_attributes=True



class Login_Token_Payload(BaseModel):
    """Schema for login token payload"""
    sub: str = None
    type: str = None
    exp: datetime = None

    class config:
        from_attributes=True

class LoginTokenData(BaseModel):
    """Schema for the login response"""
    login_token: str
    token_type: str = "Bearer"
    identifier: str