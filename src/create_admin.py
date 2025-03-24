import asyncio
from src.models import User
from src.database import async_session_maker
from src.config import DB_ADMIN_PASS, DB_ADMIN_EMAIL
from fastapi_users.password import PasswordHelper


async def create_superuser():
    password_helper = PasswordHelper()
    async with async_session_maker() as session:
        user = User(
            email=DB_ADMIN_EMAIL,
            hashed_password=password_helper.hash(DB_ADMIN_PASS),
            is_active=True,
            is_superuser=True,
            is_verified=True
        )
        session.add(user)
        await session.commit()

asyncio.run(create_superuser())
