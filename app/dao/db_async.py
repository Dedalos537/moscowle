import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

load_dotenv()


DATABASE_URL = os.getenv('SQLALCHEMY_DATABASE_URI', 'sqlite:///instance/moscowle.db')
if 'mysql' in DATABASE_URL and '+aiomysql' not in DATABASE_URL:
    if 'mysql+mysqlconnector://' in DATABASE_URL:
        DATABASE_URL = DATABASE_URL.replace('mysql+mysqlconnector://', 'mysql+aiomysql://')
    elif 'mysql+pymysql://' in DATABASE_URL:
        DATABASE_URL = DATABASE_URL.replace('mysql+pymysql://', 'mysql+aiomysql://')
    elif 'mysql://' in DATABASE_URL:
        DATABASE_URL = DATABASE_URL.replace('mysql://', 'mysql+aiomysql://')
elif 'sqlite' in DATABASE_URL and '+aiosqlite' not in DATABASE_URL:
    DATABASE_URL = DATABASE_URL.replace('sqlite://', 'sqlite+aiosqlite://')

try:
    async_engine = create_async_engine(
        DATABASE_URL, echo=False, pool_size=20, max_overflow=10, pool_timeout=30, pool_recycle=1800, future=True
    )
except ImportError as e:
    print(f'Async DB setup failed: {e}')
    async_engine = None
except Exception as e:
    print(f'Async DB setup failed: {e}')
    async_engine = None
    AsyncSessionLocal = None

if async_engine:
    try:
        AsyncSessionLocal = sessionmaker(
            bind=async_engine, class_=AsyncSession, expire_on_commit=False, autoflush=False
        )
    except Exception as e:
        print(f'Session maker failed: {e}')
        AsyncSessionLocal = None
elif 'AsyncSessionLocal' not in locals():
    AsyncSessionLocal = None


@asynccontextmanager
async def get_async_db():

    if AsyncSessionLocal is None:
        yield None
        return

    session = AsyncSessionLocal()
    try:
        yield session
        await session.commit()
    except Exception as e:
        await session.rollback()
        raise e
    finally:
        await session.close()
