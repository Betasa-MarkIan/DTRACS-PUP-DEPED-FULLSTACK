from datetime import datetime
from exceptions import ExceptionDict
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload
from sqlalchemy.future import select
from passlib.context import CryptContext
from models import db_models
from typing import Any

exc = ExceptionDict()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

async def create_focal_account(db: AsyncSession, account_data: dict) -> dict:
    new_account = db_models.FocalAccountsRequest(**account_data)
    try: 
        db.add(new_account)
        await db.commit()
        await db.refresh(new_account)
    except Exception as e:
        await db.rollback()
        raise exc.get("DatabaseError", error=e)
    return new_account

async def push_specific(db: AsyncSession, obj: Any):
    try:
        db.add(obj)
        await db.commit()
        await db.refresh(obj)
    except Exception as e:
        await db.rollback()
        raise exc.get("DatabaseError", error=e)

    return obj

async def push_commit(db: AsyncSession, obj: Any):
    try:
        await db.commit()
        await db.refresh(obj)
    except Exception as e:
        await db.rollback()
        raise exc.get("DatabaseError", error=e)
    return obj

async def push_commit_multiple(db: AsyncSession, obj_list: list):
    try:
        await db.commit()
        for obj in obj_list:
            await db.refresh(obj)
    except Exception as e:
        await db.rollback()
        raise exc.get("DatabaseError", error=e)
    return None

async def push_delete(db: AsyncSession, obj: Any):
    try:
        await db.delete(obj)
        await db.commit()
    except Exception as e:
        await db.rollback()
        raise exc.get("DatabaseError", error=e)
    return obj

async def update_global_credentials(db: AsyncSession, account: db_models.FocalAccountsVerified):
    tasks = await get_all_task(db)
    updated_tasks =[]
    for task in tasks:
        if task.creator_id == account.user_id:
            task.creator_name = account.full_name
            updated_tasks.append(task)
    if not updated_tasks:
        return None
    return await push_commit_multiple(db, updated_tasks)

async def filter_tasks(db: AsyncSession, filter: dict = None):
    query = select(db_models.Tasks).options(joinedload(db_models.Tasks.assignments))
    if filter:
        if "user_id" in filter:
            query = query.where(db_models.Tasks.creator_id == filter["user_id"])
        
    result = await db.execute(query)
    filtered =  result.unique().scalars().all()
    if not filtered:
        raise exc.get("AccountNotFound") 
    return filtered

async def updated_task_statuses(db: AsyncSession, tasks: list[db_models.Tasks]):
    status = {
        "ONGOING": "ONGOING",
        "INCOMPLETE": "INCOMPLETE",
        "COMPLETE": "COMPLETE",
    }
    modified_objects =[]
    for task in tasks:
        if isinstance(task.deadline, str):
                task.deadline = datetime.strptime(task.deadline, "%Y-%m-%d %H:%M:%S")
        compliance_status = True

        for assignment in task.assignments:                
            if (task.deadline < datetime.now()) and (assignment.status == "INCOMPLETE"):
                assignment.remarks = "MISSING"

        for assignment in task.assignments: 
            if assignment.status == status["INCOMPLETE"]:
                compliance_status = False
                break
        
        if compliance_status:
            task.task_status = status["COMPLETE"]
        elif (not compliance_status) and (task.deadline >= datetime.now()):
            task.task_status = status["ONGOING"]
        elif (not compliance_status) and (task.deadline <= datetime.now()):
            task.task_status = status["INCOMPLETE"]
        
        task.status_updated_at = datetime.now()
        modified_objects.append(task)
        modified_objects.extend(task.assignments)
    
    await push_commit_multiple(db, modified_objects)
    return tasks

async def get_all_task(db: AsyncSession):
    tasks = await filter_tasks(db)
    return await updated_task_statuses(db, tasks)

async def get_tasks_of_focal(db: AsyncSession, user_id: str):
    tasks = await filter_tasks(db, filter={"user_id": user_id})
    return await updated_task_statuses(db, tasks)

async def get_task_by_id(db:AsyncSession, task_id: str):
    tasks = await get_all_task(db)
    task = next((task for task in tasks if task.task_id == task_id), None)

    if task is None:
        raise exc.get("NoTaskFound")
    return task

async def task_assignments(db: AsyncSession):
    result = await db.execute(select(db_models.TaskAssignment))
    assignments = result.scalars().all()

    if not assignments:
        raise exc.get("RetrievingTasksFailed")
    return assignments
