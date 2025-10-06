from pydantic import BaseModel
from datetime import datetime

class Login_Token_Payload(BaseModel):
    sub: str = None
    type: str = None
    exp: datetime = None

    class config:
        from_attributes=True

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
    email: str
    password: str

class LoginTokenData(BaseModel):
    login_token: str
    token_type: str = "Bearer"
    identifier: str