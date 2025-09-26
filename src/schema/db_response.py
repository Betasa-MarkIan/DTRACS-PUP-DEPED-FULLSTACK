from pydantic import BaseModel, computed_field
from typing import Optional
from datetime import datetime

class ResponseModel(BaseModel):
   class Config: 
        from_attributes = True

class FocalResponse(ResponseModel):
    user_id: str
    last_name: str
    first_name: str 
    middle_name: str | None
    full_name: str
    office: str
    section_designation: str | None
    email: str
    contact_number: str | None
    registration_date: datetime
    avatar: str | None

class SchoolResponse(ResponseModel):
    user_id: str
    last_name: str
    first_name: str 
    middle_name: str | None
    full_name: str
    school_name: str
    school_address: str
    position: str | None
    email: str
    contact_number: str | None
    registration_date: datetime
    avatar: str | None

class AdminResponse(ResponseModel):
    user_id: str
    last_name: str
    first_name: str 
    middle_name: str | None
    email: str

    @computed_field
    @property
    def full_name(self) ->str:
        middle_name = f"{self.middle_name}" if self.middle_name else ""
        return f"{self.last_name}, {self.first_name} {middle_name}"
    
class TaskResponse(ResponseModel):
    creator_name: str
    creator_id: str
    office: str
    section: str
    task_id: str
    title: str
    description: Optional[str] = None
    links: Optional[list] = None
    task_status: str
    status_updated_at: Optional[datetime] = None
    deadline: datetime
    creation_date: datetime
    modified_date: Optional[datetime] = None

class AssignedResponse(ResponseModel):
    task_id: str
    school_id: str
    school_name: str
    account_name: str
    assigned_at: datetime
    status: str
    status_updated_at: Optional[datetime] = None
    remarks: str
    links: Optional[list] = None

class DataForTaskChart(ResponseModel):
    task_status: list
    assignments_status: list