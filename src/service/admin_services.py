from repository import admin_repositories
from exceptions import ExceptionRaised, ExceptionDict
from schema import focal_schemas, admin_schemas
from models import db_models
from passlib.context import CryptContext
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

exc = ExceptionDict()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


async def add_verified_school(db: AsyncSession, user_id: str):
    result = await db.execute(
        select(db_models.SchoolAccountsRequest)
        .where(db_models.SchoolAccountsRequest.user_id == user_id)   
    )
    request_account = result.scalar_one_or_none()

    if request_account is None:
        return None

    account_data = {
        key: value
        for key, value in request_account.__dict__.items()
        if not key.startswith("_") 
    }
    account_data["user_id"] = None
    
    verified_account = db_models.SchoolAccountsVerified(**account_data)
    await db.delete(request_account)    

    return await admin_repositories.push_specific(db, verified_account)


async def add_verified_focal(db: AsyncSession, user_id: str):
    result = await db.execute(
        select(db_models.FocalAccountsRequest)
        .where(db_models.FocalAccountsRequest.user_id == user_id)
    )
    request_account = result.scalar_one_or_none()

    if request_account is None:
        return None
    
    account_data = {
        key:value
        for key, value in request_account.__dict__.items()
        if not key.startswith("_")
    }
    account_data["user_id"] = None
    
    verified_account = db_models.FocalAccountsVerified(**account_data)
    await db.delete(request_account)

    return await admin_repositories.push_specific(db, verified_account)


async def update_designation(db: AsyncSession, data: focal_schemas.FocalDesignationUpdateSchema):
    result = await db.execute(
        select(db_models.FocalAccountsVerified)
        .where(db_models.FocalAccountsVerified.user_id == data.user_id)
    )
    account = result.scalar_one_or_none()

    if account is None:
        raise exc.get("AccountNotFound")
    
    account.section_designation = data.designation

    return await admin_repositories.push_commit(db, account)


async def admin_password_check(db: AsyncSession, admin_credentials: admin_schemas.AdminVerificationCheck):
    result  = await db.execute(
        select(db_models.AdminAccount)
        .where(db_models.AdminAccount.user_id == admin_credentials.user_id)
    )

    account = result.scalar_one_or_none()
    if account is None:
        raise exc.get("AccountNotFound")

    if not pwd_context.verify(admin_credentials.password, account.password):
        raise ExceptionRaised(detail="Admin password incorrect. Please try again")
    
    return None


async def task_status_counter(tasks: list):
    list_of_task_status = []
    complete_count = incomplete_count = ongoing_count = 0

    for task in tasks:
        if task.task_status == "COMPLETE":
            complete_count += 1
        elif task.task_status == "INCOMPLETE":
            incomplete_count += 1
        elif task.task_status == "ONGOING":
            ongoing_count += 1

    task_data = {
        "focal_id": task.creator_id,
        "complete": complete_count,
        "incomplete": incomplete_count,
        "ongoing": ongoing_count
    }
    
    list_of_task_status.append(task_data)
    return list_of_task_status

async def assignments_status_counter(tasks: list):
    list_of_statuses = []
    for task in tasks:
        complete = incomplete = 0

        for assigned in task.assignments:
            if assigned.status == "COMPLETE":
                complete += 1
            elif assigned.status == "INCOMPLETE":
                incomplete += 1

        assigned_data = {
            "task_id": task.task_id,
            "complete": complete,
            "incomplete": incomplete,
            }
        
        list_of_statuses.append(assigned_data)

    return list_of_statuses
