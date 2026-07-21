import os
import sys
from dotenv import load_dotenv

# Load local .env
load_dotenv('.env')
sys.path.append('.')

import asyncio
from sqlalchemy import select
from app.database import AsyncSession, engine
from app.models import User
from app.auth.security import hash_password

async def reset():
    async with AsyncSession(engine) as session:
        result = await session.execute(select(User).where(User.email == "admin@platform.com"))
        user = result.scalar_one_or_none()
        if user:
            print(f"User found: {user.name} ({user.email}). Resetting password...")
            user.hashed_password = hash_password("NexusAdmin2026!")
            await session.commit()
            print("Password reset successful!")
        else:
            print("User admin@platform.com not found.")

asyncio.run(reset())
