from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import union_all
from schema import school_schemas, db_response
from repository import school_repositories, focal_repositories
from models import db_models
from util import helpers
from exceptions import ExceptionDict
from passlib.context import CryptContext

exc = ExceptionDict()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


async def create_school_account_request(db: AsyncSession, school_request: school_schemas.RegistrationSchema):

    hashed_password = pwd_context.hash(school_request.password)
    account_data = {
        "user_id": None,
        "last_name": school_request.last_name,
        "first_name": school_request.first_name,
        "middle_name": school_request.middle_name,
        "full_name": school_request.full_name,
        "school_name": school_request.school_name,
        "school_address": school_request.school_address,
        "position": school_request.position,
        "email": school_request.email,
        "contact_number": school_request.contact_number,
        "password": hashed_password,
        "registration_date": datetime.now(),
        "avatar": None,
    }
    
    if account_data is None:
        raise exc.get("AccountRegistrationFailed")
    
    email_check = union_all(
        select(db_models.SchoolAccountsRequest.email).where(db_models.SchoolAccountsRequest.email == account_data["email"]),

        select(db_models.FocalAccountsRequest.email).where(db_models.FocalAccountsRequest.email == account_data["email"]),

        select(db_models.SchoolAccountsVerified.email).where(db_models.SchoolAccountsVerified.email == account_data["email"]),

        select(db_models.FocalAccountsVerified.email).where(db_models.FocalAccountsVerified.email == account_data["email"]),

        select(db_models.AdminAccount.email).where(db_models.AdminAccount.email == account_data["email"])
        
    ).alias("email_check")

    result = await db.execute(select(email_check))
    email_exist = result.scalar_one_or_none()
    if email_exist:
        raise exc.get("AccountDuplication")
    
    return await school_repositories.create_school_request(db, account_data)


async def verify_login(db: AsyncSession, login_data: school_schemas.SchoolAccountLoginSchema):

    result = await db.execute(
        select(db_models.SchoolAccountsVerified)
        .where(db_models.SchoolAccountsVerified.email == login_data.email)
    )
    account = result.scalar_one_or_none()

    if account is None:
        raise exc.get("AccountNotFound")

    if not pwd_context.verify(login_data.password, account.password):
        raise exc.get("InvalidCredentials")
    
    return account


async def update_school_account(
    db: AsyncSession, 
    user_id: str,
    updated_data: school_schemas.SchoolAccountUpdateSchema, 
):
    account = await helpers.get_school_verified_by_id(db, user_id)
    updates_dict = updated_data.model_dump(exclude_unset=True)
    updates = await helpers.updating_account(updates_dict)

    allowed_fields_for_update = { "last_name", "first_name", "middle_name", "email", "contact_number" }

    valid_updates = {
        field: value
        for field, value in updates.items()
        if field in allowed_fields_for_update and value is not None
    }

    result = await db.execute(
            select(db_models.SchoolAccountsVerified)
            .where(db_models.SchoolAccountsVerified.user_id == account.user_id)
    )

    account = result.scalar_one_or_none()

    if account is None:
        raise exc.get("AccountNotFound")

    for field, value in valid_updates.items():
        setattr(account, field, value)
    
    middle_part = f" {account.middle_name}" if account.middle_name else ""
    account.full_name = f"{account.last_name}, {account.first_name}{middle_part}".strip()

    return await school_repositories.push_commit(db, account)
    

async def update_avatar_school_verified(
    db: AsyncSession, 
    user_id: str,
    new_avatar
):
    account = await helpers.get_school_verified_by_id(db, user_id) 
    account.avatar = new_avatar

    return await school_repositories.push_commit(db, account)


async def update_remarks(
    db: AsyncSession,
    to_update: school_schemas.UpdateRemarks,
): 
    task = await focal_repositories.get_task_by_id(db, to_update.task_id)

    school_found = False
    for assignment in task.assignments:
        if assignment.school_id == to_update.school_id:
            assignment.links = to_update.links
            assignment.status = to_update.status
            assignment.status_updated_at = datetime.now()
            school_found = True
        
            if (assignment.status == "COMPLETE") and (assignment.status_updated_at < task.deadline):
                assignment.remarks = "TURNED IN ON TIME"
            
            elif ((assignment.status == "COMPLETE")) and (assignment.status_updated_at >= task.deadline):
                assignment.remarks = "TURNED IN LATE"
            
            # default = PENDING
            elif (assignment.status == "INCOMPLETE") and (assignment.status_updated_at <= task.deadline):
                assignment.remarks = "PENDING"

            elif (assignment.status == "INCOMPLETE") and (assignment.status_updated_at >= task.deadline):
                assignment.remarks = "MISSING"

            break
                
    if not school_found:
        raise exc.get("AccountNotFound")
        
    return await school_repositories.push_commit(db, assignment)


async def assignment_display(db: AsyncSession, assigned: db_models.TaskAssignment):
    result = await db.execute(
        select(db_models.SchoolAccountsVerified)
        .where(db_models.SchoolAccountsVerified.user_id == assigned.school_id)
    )
    account = result.scalar_one_or_none()

    if account is None:
        raise exc.get("AccountNotFound")

    if account.user_id == assigned.school_id:
        display = db_response.AssignedResponse(
        task_id=assigned.task_id,
        school_id=account.user_id,
        school_name=account.school_name,
        account_name=account.full_name,
        assigned_at=assigned.assigned_at,
        status=assigned.status,
        status_updated_at=assigned.status_updated_at,
        remarks=assigned.remarks,
        links=assigned.links
        )
        
    if not display:
        raise exc.get("RetrievingTasksFailed")
    
    return display


async def get_school_assignments(db: AsyncSession, user_id: str):
    tasks = await focal_repositories.get_all_task(db)

    school_tasks = [
        task
        for task in tasks
        if any(assigned.school_id == user_id for assigned in task.assignments)
    ]

    if not school_tasks:
        raise exc.get("RetrievingTasksFailed")
    
    return school_tasks
