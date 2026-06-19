"""Initialize database tables and seed demo user."""

import asyncio

from sqlalchemy import select

from app.auth import generate_api_key, hash_password
from app.database import Base, async_session, engine
from app.models import User


async def init() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with async_session() as db:
        result = await db.execute(select(User).where(User.email == "demo@example.com"))
        if not result.scalar_one_or_none():
            user = User(
                email="demo@example.com",
                hashed_password=hash_password("demo1234"),
                api_key=generate_api_key(),
            )
            db.add(user)
            await db.commit()
            print("Created demo user: demo@example.com / demo1234")


if __name__ == "__main__":
    asyncio.run(init())
