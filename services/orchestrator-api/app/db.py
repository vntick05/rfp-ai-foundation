import asyncpg

from app.config import get_settings


async def check_database() -> bool:
    settings = get_settings()
    conn = await asyncpg.connect(settings.database_url)
    try:
        value = await conn.fetchval("SELECT 1")
        return value == 1
    finally:
        await conn.close()
