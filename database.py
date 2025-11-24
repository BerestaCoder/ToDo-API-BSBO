from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from typing import AsyncGenerator
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

engine = create_async_engine(
    DATABASE_URL,
    echo=True, # Показывать SQL в консоли (удобно для обучения)
    future=True, # Использовать новый API SQLAlchemy 2.0
    pool_pre_ping=True, # Проверять живое ли соединение
    connect_args={"statement_cache_size": 0}
)
async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False, # Не сохранять автоматически при каждом изменении
    autocommit=False, # Не коммитить автоматически
)

Base = declarative_base()

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_maker() as session:
        try:
            yield session # Отдаем сессию в endpoint
        finally:
            await session.close() # Закрываем сессию после использования

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    print("База данных инициализирована!")

async def drop_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    print("Все таблицы удалены!")