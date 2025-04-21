from asyncio import current_task
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    create_async_engine,
    async_sessionmaker,
    async_scoped_session
)

from config import settings


class LaunchDbEngine:
    def __init__(self, url: str, echo: bool = False):
        self.engine = create_async_engine(url=url, echo=echo, pool_pre_ping=True)
        self.session_factory = async_sessionmaker(
            bind=self.engine, autoflush=False, autocommit=False, expire_on_commit=False
        )

    def get_scoped_session(self):
        session = async_scoped_session(
            session_factory=self.session_factory,
            scopefunc=current_task,
        )
        return session

    async def session_dependency(self) -> AsyncGenerator:
        async with self.session_factory() as session:
            try:
                yield session
            finally:
                await session.close()

    async def scoped_session_dependency(self) -> AsyncGenerator:
        session = self.get_scoped_session()
        yield session
        await session.close()

    @asynccontextmanager
    async def tg_session(self) -> AsyncGenerator:
        session = self.session_factory()
        try:
            yield session
        finally:
            await session.close()


pg_engine = LaunchDbEngine(url=str(settings.db.url))
