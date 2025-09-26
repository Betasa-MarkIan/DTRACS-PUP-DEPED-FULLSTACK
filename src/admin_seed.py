import asyncio
import os
from dotenv import load_dotenv
from sqlalchemy import select
from passlib.context import CryptContext
from database import AsyncSessionLocal, engine
from models.db_models import AdminAccount

# Load environment variables
load_dotenv()

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


async def seed_admin():
    # Get admin credentials from environment
    admin_email = os.getenv("ADMIN_GMAIL")
    admin_pass = os.getenv("ADMIN_PASS")

    if not admin_email or not admin_pass:
        print("❌ Missing ADMIN_GMAIL or ADMIN_PASS in .env")
        return

    # Hash the password
    try:
        hashed_admin_pass = pwd_context.hash(admin_pass)
    except Exception as e:
        print("❌ Failed to hash password:", e)
        return

    # Begin async DB session
    async with AsyncSessionLocal() as session:
        q = await session.execute(
            select(AdminAccount).where(AdminAccount.email == admin_email)
        )
        existing = q.scalar_one_or_none()

        if existing:
            print("✅ Admin already exists:", existing.email, existing.user_id)
            await engine.dispose()
            return

        # Create and insert admin account
        admin = AdminAccount(
            user_id=os.getenv("ADMIN_ID"),
            office=os.getenv("ADMIN_OFFICE"),
            office_description=os.getenv("ADMIN_OFFICE_DESCRIPTION"),
            last_name=os.getenv("ADMIN_LAST_NAME"),
            first_name=os.getenv("ADMIN_FIRST_NAME"),
            middle_name=os.getenv("ADMIN_MIDDLE_NAME"),
            email=admin_email,
            password=hashed_admin_pass,
        )

        session.add(admin)
        await session.commit()
        await session.refresh(admin)

        print("✅ Admin seeded successfully:", admin.email, admin.user_id)


if __name__ == "__main__":
    asyncio.run(seed_admin())
