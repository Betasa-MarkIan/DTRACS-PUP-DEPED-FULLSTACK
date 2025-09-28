from fastapi import APIRouter, status, Depends, HTTPException, Request, Response
from repository import admin_repositories, focal_repositories
from schema import admin_schemas, focal_schemas, db_response
from service import admin_services, focal_services
from models import db_models
from database.redis import get_redis_client
from auth import token_schema, redis_dependencies, auth_security, auth_dependencies
from util import helpers
from exceptions import ExceptionDict
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from database.database import get_db

exc = ExceptionDict()
router = APIRouter(prefix = "/admin", tags = ["Admin"])

@router.post("/login", status_code=status.HTTP_200_OK)
async def login (
    request: Request,
    response: Response,
    login_data: token_schema.Login,
    db: AsyncSession = Depends(get_db),
    rate_limit: dict = Depends(redis_dependencies.sliding_window_rate_limit)
) -> token_schema.TokenData:
    
    result = await db.execute(
        select(db_models.AdminAccount)
        .where(db_models.AdminAccount.email == login_data.email)
    )

    account = result.scalar_one_or_none()
    if account is None:
        raise exc.get("AccountNotFound")
    
    if not auth_security.verify_password(login_data.password, account.password):
        raise exc.get("InvalidCredentials")
    
    client_ip = request.state.real_ip
    key = f"rate_limit:login:{client_ip}"
    try: 
        await (await get_redis_client()).delete(key)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Key not in cache memory",
        )
    return await auth_dependencies.create_tokens(db, request, response, account.user_id)

@router.get("/account/info/id/", status_code=status.HTTP_200_OK)
async def get_admin_info(user: db_models.AdminAccount = Depends(auth_dependencies.get_current_user)) -> db_response.AdminResponse:
    return db_response.AdminResponse.model_validate(user)

@router.post("/account/verification", status_code=status.HTTP_200_OK)
async def get_accounts_to_verify(
    user_id: str,
    db: AsyncSession = Depends(get_db)
) -> db_response.SchoolResponse | db_response.FocalResponse :
    
    verified_account = await admin_services.add_verified_school(db, user_id)
    if verified_account:
        return db_response.SchoolResponse.model_validate(verified_account)
    elif verified_account is None:
        verified_account = await admin_services.add_verified_focal(db, user_id)
        if verified_account:
            return db_response.FocalResponse.model_validate(verified_account)
        else:
            raise exc.get("AccountNotFound")

@router.get("/school/account/request")
async def get_school_request_accounts(db: AsyncSession = Depends(get_db)) -> list[db_response.SchoolResponse]:
    accounts = await helpers.get_schools_in_req_list(db)
    accounts_list = [db_response.SchoolResponse.model_validate(account) for account in accounts]
    return accounts_list

@router.get("/focal/account/request")
async def get_focal_request_accounts(db: AsyncSession = Depends(get_db)) -> list[db_response.FocalResponse]:
    accounts = await helpers.get_focals_in_req_list(db)
    accounts_list = [db_response.FocalResponse.model_validate(account) for account in accounts]
    return accounts_list

@router.get("/school/verified/accounts", status_code=status.HTTP_200_OK)
async def get_all_verified_school_accounts(db: AsyncSession = Depends(get_db)) -> list[db_response.SchoolResponse]:
    accounts = await helpers.get_school_verified(db)
    accounts_list = [db_response.SchoolResponse.model_validate(account) for account in accounts]
    return accounts_list

@router.get("/focal/verified/accounts", status_code=status.HTTP_200_OK)
async def get_all_verified_focal_accounts(db: AsyncSession = Depends(get_db))-> list[db_response.FocalResponse]:
    accounts = await helpers.get_focal_verified(db)
    accounts_list = [db_response.FocalResponse.model_validate(account) for account in accounts]
    return accounts_list

@router.get("/accounts", status_code=status.HTTP_200_OK)
async def get_admin_accounts(db: AsyncSession = Depends(get_db)) -> list[db_response.AdminResponse]:
    accounts = await helpers.get_all_admin_accounts(db)
    admin_accounts_list = [db_response.AdminResponse.model_validate(account) for account in accounts]
    return admin_accounts_list

@router.put("/focal/designation/id/", status_code=status.HTTP_200_OK)
async def update_focal_account(data: focal_schemas.FocalDesignationUpdateSchema, db: AsyncSession = Depends(get_db)) -> db_response.FocalResponse:
    updated_account = await admin_services.update_designation(db, data)
    db_response.FocalResponse.model_validate(updated_account)
    return updated_account

@router.delete("/school/request/delete/id/", status_code=status.HTTP_200_OK)
async def delete_school_request(
    user_id: str,
    admin_credentials: admin_schemas.AdminVerificationCheck,
    db: AsyncSession = Depends(get_db)
) -> db_response.SchoolResponse:
    
    account = await helpers.get_school_req_by_id(db, user_id)
    await admin_services.admin_password_check(db, admin_credentials)
    deleted_account = await admin_repositories.push_delete(db, account)
    db_response.SchoolResponse.model_validate(deleted_account)
    return deleted_account

@router.delete("/focal/request/delete/id/", status_code=status.HTTP_200_OK)
async def delete_focal_request(
    user_id: str, 
    admin_credentials: admin_schemas.AdminVerificationCheck,
    db: AsyncSession = Depends(get_db)
) -> db_response.FocalResponse:

    account = await helpers.get_focal_req_by_id(db, user_id)
    await admin_services.admin_password_check(db, admin_credentials)
    deleted_account = await admin_repositories.push_delete(db, account)
    db_response.FocalResponse.model_validate(deleted_account)    
    return deleted_account

@router.delete("/school/verified/account/delete/id/", status_code=status.HTTP_200_OK)
async def delete_school_verified_account(
    user_id: str, 
    admin_credentials: admin_schemas.AdminVerificationCheck,
    db: AsyncSession = Depends(get_db)
) -> db_response.SchoolResponse:

    account = await helpers.get_school_verified_by_id(db, user_id)
    await admin_services.admin_password_check(db, admin_credentials)
    deleted_account = await admin_repositories.push_delete(db, account)
    await admin_repositories.push_delete_tokens(db, user_id)
    response = db_response.SchoolResponse.model_validate(deleted_account)
    return response

@router.delete("/focal/verified/account/delete/id/", status_code=status.HTTP_200_OK)
async def delete_focal_verified_account(
    user_id: str, 
    admin_credentials: admin_schemas.AdminVerificationCheck,
    db: AsyncSession = Depends(get_db)
) -> db_response.FocalResponse:

    account = await helpers.get_focal_verified_by_id(db, user_id)
    await admin_services.admin_password_check(db, admin_credentials)
    deleted_account = await admin_repositories.push_delete(db, account)
    await admin_repositories.push_delete_tokens(db, user_id)
    response = db_response.FocalResponse.model_validate(deleted_account)
    return response

@router.get("/tasks/all/focal_id/", status_code=status.HTTP_200_OK)
async def get_tasks_per_focal(user_id: str, db: AsyncSession = Depends(get_db)) -> list[db_response.TaskResponse]:
    tasks = await focal_repositories.get_tasks_of_focal(db, user_id)
    response = [db_response.TaskResponse.model_validate(task) for task in tasks]
    return response

@router.get("/office/section", status_code=status.HTTP_200_OK)
async def get_focal_by_section(section_designation: str, db: AsyncSession = Depends(get_db)) -> list[db_response.FocalResponse]:
    accounts = await focal_services.get_focal_account_by_section(db, section_designation)
    accounts_list = [db_response.FocalResponse.model_validate(account)for account in accounts]
    return accounts_list

@router.get("/recharts/task/data", status_code=status.HTTP_200_OK)
async def count_task_per_focal(user_id: str, db: AsyncSession = Depends(get_db)) -> db_response.DataForTaskChart:

    all_tasks = await focal_repositories.get_tasks_of_focal(db, user_id)
    task = await admin_services.task_status_counter(all_tasks)
    assigned = await admin_services.assignments_status_counter(all_tasks)
    response = db_response.DataForTaskChart(
        task_status=task,
        assignments_status=assigned
    )
    return response

@router.get("/task/assignments", status_code=status.HTTP_200_OK)
async def assignments_by_task(task_id: str, db: AsyncSession = Depends(get_db)) -> list [db_response.AssignedResponse]:
    return await focal_services.all_assignment_display(db, task_id)
