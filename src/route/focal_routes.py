from fastapi import APIRouter, status, Depends
from repository import focal_repositories
from schema import focal_schemas, db_response
from service import focal_services
from models import db_models
from util import helpers
from auth.auth_dependencies import get_current_user
from exceptions import ExceptionDict
from sqlalchemy.ext.asyncio import AsyncSession
from database.database import get_db

exc = ExceptionDict()
router = APIRouter(prefix="/focal", tags=["Focal"])


@router.post("/account/registration", status_code=status.HTTP_201_CREATED)
async def create_focal_account_request(
    focal_account_data: focal_schemas.RegistrationSchema,
    db: AsyncSession = Depends(get_db)
) -> db_response.FocalResponse:
    
    account_request = await focal_services.create_focal_account_request(db, focal_account_data)   
    response = db_response.FocalResponse.model_validate(account_request)

    return response


@router.get("/account/info/id/", status_code=status.HTTP_200_OK)
async def get_focal_verified_info(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    user: db_models.FocalAccountsVerified = Depends(get_current_user)
) -> db_response.FocalResponse:

    account_info = await helpers.get_focal_verified_by_id(db, user_id)
    response = db_response.FocalResponse.model_validate(account_info)

    return response


@router.get("/school/verified/accounts", status_code=status.HTTP_200_OK)
async def get_all_verified_school_accounts(db: AsyncSession = Depends(get_db)) -> list[db_response.SchoolResponse]:

    accounts = await helpers.get_school_verified(db)
    accounts_list = [db_response.SchoolResponse.model_validate(account) for account in accounts]
    
    return accounts_list


@router.get("/school/accounts", status_code=status.HTTP_200_OK)
async def get_school_accounts_by_school(
    school_name: str,
    db: AsyncSession = Depends(get_db)
) -> list[db_response.SchoolResponse]:
    
    accounts = await focal_services.get_school_verified_by_school_name(db, school_name)
    accounts_list = [db_response.SchoolResponse.model_validate(account)for account in accounts]

    return accounts_list


@router.put("/account/update/id/") 
async def update_focal_account(
    user_id: str,
    updated_data: focal_schemas.FocalAccountUpdateSchema,
    db: AsyncSession = Depends(get_db)
) -> db_response.FocalResponse:

    updated_account = await focal_services.update_focal_account(db, updated_data, user_id)
    await focal_repositories.update_global_credentials(db, updated_account)

    return db_response.FocalResponse.model_validate(updated_account)


@router.put("/account/avatar/id/", status_code=status.HTTP_200_OK)
async def update_focal_avatar(
    user_id: str, 
    avatar: str,
    db: AsyncSession = Depends(get_db)
) -> db_response.FocalResponse:
    
    updated_account = await focal_services.update_avatar_focal_verified(db, user_id, avatar)
    response = db_response.FocalResponse.model_validate(updated_account)
    
    return response


@router.get("/tasks/all", status_code=status.HTTP_200_OK)
async def get_all_task(db: AsyncSession = Depends(get_db)) -> list[db_response.TaskResponse]:

    updated_tasks = await focal_repositories.get_all_task(db)
    response = [db_response.TaskResponse.model_validate(task) for task in updated_tasks]

    return response


@router.get("/tasks/all/focal_id/", status_code=status.HTTP_200_OK)
async def get_tasks_per_focal(user_id: str, db: AsyncSession = Depends(get_db)) -> list[db_response.TaskResponse]:

    tasks = await focal_repositories.get_tasks_of_focal(db, user_id)
    response = [db_response.TaskResponse.model_validate(task) for task in tasks]
    
    return response


@router.get("/task/id/", status_code=status.HTTP_200_OK)
async def get_task_by_id(task_id: str, db: AsyncSession = Depends(get_db)) -> db_response.TaskResponse:

    task = await focal_repositories.get_task_by_id(db, task_id)
    response = db_response.TaskResponse.model_validate(task)

    return response


@router.get("/task/assignments", status_code=status.HTTP_200_OK)
async def assignments_by_task(task_id: str, db: AsyncSession = Depends(get_db)) -> list [db_response.AssignedResponse]:

    return await focal_services.all_assignment_display(db, task_id)


@router.delete("/task/delete/id/", status_code=status.HTTP_200_OK)
async def delete_task(task_id: str, db: AsyncSession = Depends(get_db)) -> db_response.TaskResponse:

    task = await focal_repositories.get_task_by_id(db, task_id)
    deleted_task = await focal_repositories.push_delete(db, task)
    response = db_response.TaskResponse.model_validate(deleted_task)
    
    return response


@router.post("/task/new-task", status_code=status.HTTP_201_CREATED)
async def create_new_task(
    task_data: focal_schemas.CreateTask,
    db: AsyncSession = Depends(get_db)
) -> db_response.TaskResponse:
    
    accounts_assigned_status = await focal_services.accounts_assigned_status(db, task_data.accounts_required)
    create_task = await focal_services.create_new_task(db, task_data, accounts_assigned_status)
    response = db_response.TaskResponse.model_validate(create_task)    

    return response


@router.put("/task/update/id/", status_code=status.HTTP_200_OK)
async def update_task(
    task_id: str, 
    update_task: focal_schemas.UpdateTask,
    db: AsyncSession = Depends(get_db)
) -> db_response.TaskResponse:
    
    updated_task = await focal_services.update_task(db, task_id, update_task)
    response = db_response.TaskResponse.model_validate(updated_task)
    
    return response


@router.post("/create/multiple/tasks", status_code=status.HTTP_200_OK)
async def create_many_task(
    tasks: list[focal_schemas.CreateTask],
    db: AsyncSession = Depends(get_db)
) -> list[db_response.TaskResponse]:
    
    created_task=[]
    for task in tasks:
        create = await create_new_task(task, db)
        created_task.append(create)
    
    return created_task


@router.get("/all/task/assignments", status_code=status.HTTP_200_OK)
async def assignments_by_task(task_id: str, db: AsyncSession = Depends(get_db)) -> list [db_response.AssignedResponse]:

    return await focal_services.all_assignment_display(db, task_id)
