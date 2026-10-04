from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine
)
from sqlalchemy import text
from app.core.config import settings
from app.core.logging import logger

database_url = settings.get_database_url()

# Create asynchronous SQLAlchemy engine
async_engine = create_async_engine(
    database_url,
    echo=(settings.LOG_LEVEL.upper() == "DEBUG"),
    future=True,
    pool_pre_ping=True,
)

# Async session factory
AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency that yields an asynchronous database session.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def check_db_health() -> bool:
    """
    Executes a lightweight query to verify active database connectivity.
    Returns True if healthy and responsive, False otherwise.
    """
    try:
        async with AsyncSessionLocal() as session:
            result = await session.execute(text("SELECT 1"))
            return result.scalar() == 1
    except Exception as e:
        logger.warning(f"Database health check failed: {e}")
        return False
