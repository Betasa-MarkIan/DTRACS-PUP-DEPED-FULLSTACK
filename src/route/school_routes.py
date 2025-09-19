from fastapi import APIRouter, status, Depends
from schema import school_schemas, db_response
from service import school_services, focal_services
from repository import focal_repositories
from util import account_util
from exceptions import ExceptionDict
from sqlalchemy.ext.asyncio import AsyncSession
from database import get_db

exc = ExceptionDict()
router = APIRouter(prefix="/school", tags=["School"])


@router.post("/account/request", status_code=status.HTTP_201_CREATED)
async def create_school_account_request(
    school_request: school_schemas.RegistrationSchema,
    db: AsyncSession = Depends(get_db)
) -> db_response.SchoolResponse: 
    
    account_request = await school_services.create_school_account_request(db, school_request)
    response = db_response.SchoolResponse.model_validate(account_request)

    return response


@router.get("/account/info/id/", status_code=status.HTTP_200_OK)
async def get_school_verified_info(user_id: str, db: AsyncSession = Depends(get_db)) -> db_response.SchoolResponse:

    account_info = await account_util.get_school_verified_by_id(db, user_id)
    response = db_response.SchoolResponse.model_validate(account_info)

    return response


@router.post("/account/login")
async def login_school_account(
    login_data: school_schemas.SchoolAccountLoginSchema,
    db: AsyncSession = Depends(get_db)
) -> db_response.SchoolResponse:
    
    valid_login = await school_services.verify_login(db, login_data)
    response = db_response.SchoolResponse.model_validate(valid_login)

    return response


@router.put("/account/update/id/") 
async def update_school_account(
    user_id: str,
    updated_data: school_schemas.SchoolAccountUpdateSchema,
    db: AsyncSession = Depends(get_db)
) -> db_response.SchoolResponse:
  
    updated_account = await school_services.update_school_account(db, user_id, updated_data)
    response = db_response.SchoolResponse.model_validate(updated_account)

    return response


@router.put("/account/avatar/id/", status_code=status.HTTP_200_OK)
async def update_school_avatar(
    user_id: str,
    avatar: str,
    db: AsyncSession = Depends(get_db)
) -> db_response.SchoolResponse:
    
    updated_account = await school_services.update_avatar_school_verified(db, user_id, avatar)
    response = db_response.SchoolResponse.model_validate(updated_account)
    
    return response


@router.get("/task/id/", status_code=status.HTTP_200_OK)
async def get_task_by_id(task_id: str, db: AsyncSession = Depends(get_db)) -> db_response.TaskResponse:

    task = await focal_repositories.get_task_by_id(db, task_id)
    response = db_response.TaskResponse.model_validate(task)
    
    return response


@router.get("/office/section", status_code=status.HTTP_200_OK)
async def get_focal_by_section(section_designation: str,
    db: AsyncSession = Depends(get_db)
) -> list[db_response.FocalResponse]:
    
    accounts = await focal_services.get_focal_account_by_section(db, section_designation)
    accounts_list = [db_response.FocalResponse.model_validate(account)for account in accounts]

    return accounts_list


@router.get("/all/tasks", status_code=status.HTTP_200_OK)
async def get_all_task_by_school(user_id: str, db: AsyncSession = Depends(get_db)):

    get_school_tasks = await school_services.get_school_assignments(db, user_id)
    response = [db_response.TaskResponse.model_validate(task) for task in get_school_tasks ]

    return response


@router.put("/update/task/status", status_code=status.HTTP_200_OK)
async def update_task_remark(
    to_update: school_schemas.UpdateRemarks,
    db: AsyncSession = Depends(get_db)
    ) -> db_response.AssignedResponse:
  
    assignment = await school_services.update_remarks(db, to_update)
    assignment_for_display = await school_services.assignment_display(db, assignment)
    
    return assignment_for_display


@router.get("/all/task/assignments", status_code=status.HTTP_200_OK)
async def assignments_by_task(task_id: str, db: AsyncSession = Depends(get_db)) -> list [db_response.AssignedResponse]:

    return await focal_services.all_assignment_display(db, task_id)
