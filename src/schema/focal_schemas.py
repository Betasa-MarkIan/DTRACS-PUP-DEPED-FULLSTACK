from util import global_enums
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, model_validator, EmailStr, Field

class FocalBaseSchema(BaseModel):
    class Config: 
        from_attributes = True

class RegistrationSchema(FocalBaseSchema):
    user_id: str = Field(default="PENDING")
    first_name: str
    last_name: str
    middle_name: str
    office: global_enums.OfficeEnum
    section_designation: str = Field(default=None)
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
        return f"{self.last_name}, {self.first_name} {self.middle_name}".strip()

class FocalAccountLoginSchema(FocalBaseSchema):
    email: str
    password: str 

class FocalAccountUpdateSchema(FocalBaseSchema):
    first_name: str 
    last_name: str
    middle_name: Optional[str] = Field(default=None)
    email: Optional[EmailStr] = Field(default=None)
    contact_number: Optional[str] = Field(default=None)

    @property
    def full_name(self) -> str:
        middle_name = f"{self.middle_name}" if self.middle_name else ""
        return f"{self.last_name}, {self.first_name} {middle_name}".strip()

class FocalDesignationUpdateSchema(FocalBaseSchema):
    user_id: str
    designation: global_enums.SectionEnum

class FocalForgetPasswordSchema(FocalBaseSchema):
    email: str

class FocalSetNewPasswordSchema(FocalBaseSchema):
    password: str

class CreateTask(FocalBaseSchema):
    creator_id: str
    title: str
    description: Optional[str] = Field(default=None)
    deadline: Optional[str] = "2025-08-10 13:00"
    accounts_required: Optional[List] = []
    links: Optional[list] = Field(default=None)
    task_status: str = "ONGOING"
    
    @property
    def deadline_obj(self) -> datetime:
        if isinstance (self.deadline, str):
            added_milisec = f"{self.deadline}:00"
            duedate = datetime.strptime(added_milisec, "%Y-%m-%d %H:%M:%S")
            return duedate
        else: 
            return self.deadline
        
class UpdateTask(FocalBaseSchema):
    title: str
    description: Optional[str] = Field(default=None)
    deadline: str = "2025-08-10 13:00"
    accounts_required: Optional[List] =[]
    links: Optional[list] = Field(default=None)
    
    @property
    def deadline_obj(self) -> datetime:
        added_milisec = f"{self.deadline}:00"
        duedate = datetime.strptime(added_milisec, "%Y-%m-%d %H:%M:%S")
        return duedate

