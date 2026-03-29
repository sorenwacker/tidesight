"""Database connection and session management."""

from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from tidesight.config import settings


class Base(DeclarativeBase):
    """SQLAlchemy declarative base for all models."""

    pass


engine = create_async_engine(settings.database_url, echo=False)

async_session_maker = async_sessionmaker(engine, expire_on_commit=False)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Yield a database session for dependency injection.

    Yields:
        AsyncSession: Database session that auto-commits on success.
    """
    async with async_session_maker() as session:
        yield session


async def init_db() -> None:
    """Create all database tables."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
