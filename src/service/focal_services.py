from datetime import datetime
from passlib.context import CryptContext
from exceptions import ExceptionDict
from schema import focal_schemas, db_response
from util import helpers
from models import db_models
from repository import focal_repositories
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import delete, union_all
from sqlalchemy.future import select

exc = ExceptionDict()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

async def create_focal_account_request(db: AsyncSession, focal_account_data: focal_schemas.RegistrationSchema):
    hashed_password = pwd_context.hash(focal_account_data.password)
    account_data = {
        "user_id": None,
        "last_name": focal_account_data.last_name,
        "first_name": focal_account_data.first_name,
        "middle_name": focal_account_data.middle_name,
        "full_name": focal_account_data.full_name,
        "office": focal_account_data.office,
        "section_designation": focal_account_data.section_designation,
        "email": focal_account_data.email,
        "contact_number": focal_account_data.contact_number,
        "password": hashed_password,
        "registration_date": datetime.now(),
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
    account_exist = result.scalar_one_or_none()
    if account_exist:
        raise exc.get("AccountDuplication")
    return await focal_repositories.create_focal_account(db, account_data)

async def verify_login(db: AsyncSession, login_data: focal_schemas.FocalAccountLoginSchema):
    result = await db.execute(
        select(db_models.FocalAccountsVerified)
        .where(db_models.FocalAccountsVerified.email == login_data.email)
    )
    account = result.scalar_one_or_none()
    if account is None:
        raise exc.get("AccountNotFound")
    if not pwd_context.verify(login_data.password, account.password):
        raise exc.get("InvalidCredentials")
    return account

async def update_focal_account(
    db: AsyncSession,
    updated_data: focal_schemas.FocalAccountUpdateSchema,
    user_id: str
):
    updates_dict = updated_data.model_dump(exclude_unset=True)
    updates = await helpers.updating_account(updates_dict)
    allowed_fields_for_update = {"last_name", "first_name", "middle_name", "email", "contact_number"}
    valid_updates = {
        field: value
        for field, value in updates.items()
        if field in allowed_fields_for_update and value is not None
    }
    account = await helpers.get_focal_verified_by_id(db, user_id)
    if account is None:
        raise exc.get("AccountNotFound")
    for field, value in valid_updates.items():
        setattr(account, field, value)

    middle_part = f" {account.middle_name}" if account.middle_name else ""
    account.full_name = f"{account.last_name}, {account.first_name}{middle_part}".strip()
    return await focal_repositories.push_commit(db, account)

async def update_avatar_focal_verified(db: AsyncSession, user_id: str, new_avatar: str):
    account = await helpers.get_focal_verified_by_id(db, user_id)
    account.avatar = new_avatar
    return await focal_repositories.push_commit(db, account)

async def get_school_verified_by_school_name(db: AsyncSession, school_name: str):
    result = await db.execute(
        select(db_models.SchoolAccountsVerified)
        .where(db_models.SchoolAccountsVerified.school_name == school_name)
    )
    accounts = result.scalars().all()
    if not accounts:
        raise exc.get("AccountNotFound")
    return accounts

async def get_focal_account_by_section(db: AsyncSession, section_designation: str):
    result = await db.execute(
        select(db_models.FocalAccountsVerified)
        .where(db_models.FocalAccountsVerified.section_designation == section_designation)
    )
    accounts = result.scalars().all()
    if not accounts:
        raise exc.get("AccountNotFound")
    return accounts

async def all_assignment_display(db: AsyncSession, task_id: str):
    specific_task = await focal_repositories.get_task_by_id(db, task_id)
    school_accounts = await helpers.get_ids_in_assignment(db, specific_task)
    displays = []
    for assignment in specific_task.assignments:
        for account in school_accounts:
            if account.user_id == assignment.school_id:
                display = db_response.AssignedResponse(
                task_id=assignment.task_id,
                school_id=account.user_id,
                school_name=account.school_name,
                account_name=account.full_name,
                assigned_at=assignment.assigned_at,
                status=assignment.status,
                status_updated_at=assignment.status_updated_at,
                remarks=assignment.remarks,
                links=assignment.links
                )
                displays.append(display)

    if not displays:
        raise exc.get("RetrievingTasksFailed")
    return displays

async def get_schools_assigned(db: AsyncSession, schools_names: list):
    result = await db.execute(
        select(db_models.SchoolAccountsVerified.user_id)
        .where(db_models.SchoolAccountsVerified.school_name.in_(schools_names))
    )
    school_ids = result.scalars().all()
    if not school_ids:
        raise exc.get("AccountNotFound")
    
    accounts_assigned_from_school = []
    accounts_assigned_from_school.extend(school_ids)
    return accounts_assigned_from_school

async def accounts_assigned_status(db: AsyncSession, school_ids: list):
    result = await db.execute(
        select(db_models.SchoolAccountsVerified)
        .where(db_models.SchoolAccountsVerified.user_id.in_(school_ids))
    )
    accounts = result.scalars().all()
    if not accounts:
        raise exc.get("TaskCreationFailed")

    accounts_assigned_list = []
    for account in accounts:
        account_status = {
            "school_id": account.user_id,
            "account_name": account.full_name,
            "school": account.school_name,
            "status": "INCOMPLETE",
            "remarks": "PENDING",
            "links": None
        }
        accounts_assigned_list.append(account_status)
    return accounts_assigned_list

async def create_new_task(
    db: AsyncSession,
    task_data: focal_schemas.CreateTask,
    accounts_assigned_status: list
):
    creator_focal = await helpers.get_focal_verified_by_id(db, task_data.creator_id)
    generated_task_id = await helpers.generate_task_id(db)
    assignments = []
    for account in accounts_assigned_status:
        assignment = db_models.TaskAssignment(
            task_id=generated_task_id,
            school_id=account["school_id"],
            assigned_at=datetime.now(),
            status=account["status"],
            remarks=account["remarks"],
            links=account["links"]
        )
        assignments.append(assignment)

    task = db_models.Tasks(
        task_id=generated_task_id,
        creator_id=creator_focal.user_id,
        creator_name=creator_focal.full_name,
        office=creator_focal.office,
        section=creator_focal.section_designation,
        creation_date=datetime.now(),
        title=task_data.title,
        description=task_data.description,
        deadline=task_data.deadline_obj,
        task_status=task_data.task_status,
        links=task_data.links,
        assignments = assignments
    )
    return await focal_repositories.push_specific(db, task)

async def update_task(
    db: AsyncSession, 
    task_id: str, 
    update_task: focal_schemas.UpdateTask
):
    if not update_task.accounts_required:
        raise exc.get("TaskCreationFailed")
    
    task = await focal_repositories.get_task_by_id(db, task_id)
    old_list = [assigned.school_id for assigned in task.assignments]
    new_list = update_task.accounts_required 

    remove_from_list = [item for item in old_list if item not in new_list]
    add_to_list = [item for item in new_list if item not in old_list]

    if remove_from_list:
        await db.execute(
            delete(db_models.TaskAssignment)
            .where(
                db_models.TaskAssignment.task_id == task.task_id,
                db_models.TaskAssignment.school_id.in_(remove_from_list)
            )
    )
    modified_obj = []
    if add_to_list:
        assignment_to_add = await accounts_assigned_status(db, add_to_list)
        for new_assignment in assignment_to_add:
            assignment = db_models.TaskAssignment(
                task_id=task.task_id,
                school_id=new_assignment["school_id"],
                assigned_at=datetime.now(),
                status=new_assignment["status"],
                remarks=new_assignment["remarks"],
                links=new_assignment["links"]
            )
            db.add(assignment)
            modified_obj.append(assignment)

    task.links = update_task.links if update_task.links else None
    task.modified_date = datetime.now()

    for key, value in update_task.model_dump(exclude_unset=True).items():
        if key not in ["accounts_required", "links"] and value is not None:
            if hasattr(task, key):
                setattr(task, key, value)
    
    modified_obj.append(task)
    await focal_repositories.push_commit_multiple(db, modified_obj)
    return task














