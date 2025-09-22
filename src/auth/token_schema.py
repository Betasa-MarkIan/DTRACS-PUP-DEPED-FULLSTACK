from pydantic import BaseModel
from datetime import datetime

class TokenData(BaseModel):
    """Schema for the response after successful login."""
    access_token: str
    token_type: str = "Bearer"
    user_id: str

class Access_Token_Payload(BaseModel):
    """Schema representing the data stored INSIDE the JWT."""
    sub: str = None
    type: str = None
    exp: datetime = None

    class config:
        from_attributes=True

class Refresh_Token_Payload(BaseModel):
    """Schema representing the data stored INSIDE the JWT."""
    sub: str = None
    session_id: str = None
    type: str = None
    exp: datetime = None

    class config:
        from_attributes=True

class Login(BaseModel):
    """Schema for login."""
    email: str
    password: str

    class config:
        from_attributes=True



# add a field for refresh_token status
# auto delete once the refresh_token expires