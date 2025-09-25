from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
import re
from sqlalchemy.future import select
from models import db_models
from exceptions import ExceptionDict, ExceptionRaised
from passlib.context import CryptContext

exc = ExceptionDict()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


async def updating_account(updated_account: dict):
    updates = {k:v for k,v in updated_account.items()
              if v is not None}
    if not updates:
        raise exc.get("UpdateFailed")
    
    return updates 

def model_to_dict(account):
    account_info = {k:v for k,v in account.__dict__.items()
                    if not k.startswith("_")}
    
    return account_info


async def get_school_verified(db: AsyncSession):
    result = await db.execute(select(db_models.SchoolAccountsVerified))
    accounts = result.scalars().all()
    
    if not accounts:
        raise ExceptionRaised()

    return accounts


async def get_focal_verified(db: AsyncSession):
    result = await db.execute(select(db_models.FocalAccountsVerified))
    accounts = result.scalars().all()

    if not accounts:
        raise ExceptionRaised()
    
    return accounts


async def get_schools_in_req_list(db: AsyncSession):
    result = await db.execute(select(db_models.SchoolAccountsRequest))
    accounts = result.scalars().all()

    if not accounts:
        raise ExceptionRaised()
    
    return accounts


async def get_focals_in_req_list(db: AsyncSession):
    result = await db.execute(select(db_models.FocalAccountsRequest))
    accounts = result.scalars().all()
    
    if not accounts:
        raise ExceptionRaised()
    
    return accounts
 

async def get_all_admin_accounts(db: AsyncSession):
    result = await db.execute(select(db_models.AdminAccount))
    accounts = result.scalars().all()

    if not accounts:
        raise ExceptionRaised()

    return accounts


async def get_school_req_by_id(db: AsyncSession, user_id: str):
    result = await db.execute(
        select(db_models.SchoolAccountsRequest)
        .where(db_models.SchoolAccountsRequest.user_id == user_id)
        )
    account = result.scalar_one_or_none()
    
    if account is None:
        raise exc.get("AccountNotFound")
    
    return account


async def get_focal_req_by_id(db: AsyncSession, user_id: str):
    result = await db.execute(
        select(db_models.FocalAccountsRequest)
        .where(db_models.FocalAccountsRequest.user_id == user_id)
        )
    account = result.scalar_one_or_none()
    
    if account is None:
        raise exc.get("AccountNotFound")
    
    return account


async def get_school_verified_by_id(db: AsyncSession, user_id: str):
    result = await db.execute(
        select(db_models.SchoolAccountsVerified)
        .where(db_models.SchoolAccountsVerified.user_id == user_id)
    )
    account = result.scalar_one_or_none()
    
    if account is None:
        raise exc.get("AccountNotFound")

    return account


async def get_focal_verified_by_id(db: AsyncSession, user_id: str):
    result = await db.execute(
        select(db_models.FocalAccountsVerified)
        .where(db_models.FocalAccountsVerified.user_id == user_id)
    )
    account = result.scalar_one_or_none()
    
    if account is None:
        raise exc.get("AccountNotFound")

    return account


async def get_admin_by_id(db: AsyncSession, user_id: str):
    result = await db.execute(
        select(db_models.AdminAccount)
        .where(db_models.AdminAccount.user_id == user_id)
    )
    account = result.scalar_one_or_none()
    
    if account is None:
        raise exc.get("AccountNotFound")

    return account


async def get_ids_in_assignment(db: AsyncSession, task: db_models.Tasks):
    account_ids = [
        assignment.school_id
        for assignment in task.assignments
    ]

    if not account_ids:
        raise exc.get("RetrievingTasksFailed")
    
    return await get_schools_assigned(db, account_ids)


async def get_schools_assigned(db: AsyncSession, school_ids: list):
    result = await db.execute(
        select(db_models.SchoolAccountsVerified)
        .where(db_models.SchoolAccountsVerified.user_id.in_(school_ids))
    )
    accounts = result.scalars().all()

    if not accounts:
        raise exc.get("AccountNotFound")
    
    return accounts


async def generate_task_id(db: AsyncSession):
    result = await db.execute(text(
        'SELECT task_id FROM tasks ORDER BY task_id DESC LIMIT 1'
    ))
    last_id = result.scalar()

    if last_id:
        match = re.search(r'TASK-(\d+)', str(last_id))
        if match:

            next_number = int(match.group(1)) + 1
        else:
            next_number = 1
    else: 
        next_number = 1

    task_id =  f"TASK-{next_number:04d}"
    return task_id

