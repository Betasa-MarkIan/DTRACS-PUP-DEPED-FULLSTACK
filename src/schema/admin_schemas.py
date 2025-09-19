from pydantic import BaseModel, EmailStr

class AdminBaseSchema(BaseModel):
    class Config: 
        from_attributes = True

class AdminLoginSchema(AdminBaseSchema):
    email: EmailStr
    password: str

class AdminVerificationCheck(AdminBaseSchema):
    user_id: str
    password: str