from typing import Optional
from pydantic import BaseModel, model_validator, EmailStr, Field

class SchoolBaseSchema(BaseModel):
    class Config: 
        from_attributes = True

class RegistrationSchema(SchoolBaseSchema):
    user_id: str = Field(default="PENDING")
    first_name: str 
    last_name: str
    middle_name: Optional[str]
    school_name: str
    school_address: str
    position: str = Field(default=None)
    email: EmailStr
    contact_number: str
    password: str
    confirm_password: str
    registration_date: str = Field(default="PENDING")
    avatar: str = Field(default=None)
    
    @model_validator(mode="after")
    def check_passwords_match(self):
        if self.password != self.confirm_password:
            raise ValueError("Passwords do not match")
        return self

    @property
    def full_name(self) -> str:
        middle_name = f"{self.middle_name}" if self.middle_name else ""
        return f"{self.last_name}, {self.first_name} {middle_name}".strip()

class SchoolAccountLoginSchema(SchoolBaseSchema):
    email: EmailStr
    password: str 

class SchoolAccountUpdateSchema(SchoolBaseSchema):
    first_name: str 
    last_name: str
    middle_name: Optional[str] = Field(default=None)
    email: Optional[EmailStr] = Field(default=None)
    contact_number: Optional[str] = Field(default=None)

    @property
    def full_name(self) -> str:
        middle_name = f"{self.middle_name}" if self.middle_name else ""
        return f"{self.last_name}, {self.first_name} {middle_name}".strip()

class SchoolForgetPasswordSchema(SchoolBaseSchema):
    email: str

class SchoolSetNewPasswordSchema(SchoolBaseSchema):
    password: str

class UpdateRemarks(SchoolBaseSchema):
    task_id: str
    school_id: str
    status: str
    links: Optional[list] = Field(default=None)
