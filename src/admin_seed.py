import asyncio
import os
from dotenv import load_dotenv
from database.database import AsyncSessionLocal
from sqlalchemy import select, union_all
from passlib.context import CryptContext

load_dotenv()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

async def seed_admin():
    admin_email = os.getenv("ADMIN_GMAIL")
    admin_pass = os.getenv("ADMIN_PASS")
    hashed_admin_pass = pwd_context.hash(admin_pass)

    async with AsyncSessionLocal() as session:
        try:
            from models.db_models import AdminAccount, SchoolAccountsRequest, SchoolAccountsVerified, FocalAccountsRequest, FocalAccountsVerified

            q = union_all(
                (select(AdminAccount.email).where(AdminAccount.email == admin_email)),
                (select(SchoolAccountsRequest.email).where(AdminAccount.email == admin_email)),
                (select(SchoolAccountsVerified.email).where(AdminAccount.email == admin_email)),
                (select(FocalAccountsRequest.email).where(AdminAccount.email == admin_email)),
                (select(FocalAccountsVerified.email).where(AdminAccount.email == admin_email)),
            ).alias("email_check")

            result = await session.execute(select(q))
            existing = result.scalar_one_or_none()
            if existing:
                print("Admin already exists:", existing.email, existing.user_id)
                return
            
            admin = AdminAccount (
                user_id=os.getenv("ADMIN_ID"),
                office=os.getenv("ADMIN_OFFICE"),
                office_description=os.getenv("ADMIN_OFFICE_DESCRIPTION"),
                last_name=os.getenv("ADMIN_LAST_NAME"),
                first_name=os.getenv("ADMIN_FIRST_NAME"),
                middle_name=os.getenv("ADMIN_MIDDLE_NAME"),
                email=admin_email,
                password=hashed_admin_pass
            )
            session.add(admin)
            await session.commit()
            await session.refresh(admin)
            await session.close()
            print("Admin seeded:", admin.email, admin.user_id)
            return
        
        except ModuleNotFoundError:
            print("Admin model import from environment (.env) failed")

if __name__ == "__main__":
    asyncio.run(seed_admin())