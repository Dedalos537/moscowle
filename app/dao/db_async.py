from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from contextlib import asynccontextmanager
import os
from dotenv import load_dotenv

load_dotenv()


DATABASE_URL = os.getenv("SQLALCHEMY_DATABASE_URI", "sqlite:///instance/moscowle.db")
if "mysql" in DATABASE_URL and "+aiomysql" not in DATABASE_URL:
    # Handle various mysql drivers to convert to aiomysql
    if "mysql+mysqlconnector://" in DATABASE_URL:
        DATABASE_URL = DATABASE_URL.replace("mysql+mysqlconnector://", "mysql+aiomysql://")
    elif "mysql+pymysql://" in DATABASE_URL:
        DATABASE_URL = DATABASE_URL.replace("mysql+pymysql://", "mysql+aiomysql://")
    elif "mysql://" in DATABASE_URL:
        DATABASE_URL = DATABASE_URL.replace("mysql://", "mysql+aiomysql://")
elif "sqlite" in DATABASE_URL and "+aiosqlite" not in DATABASE_URL:
    DATABASE_URL = DATABASE_URL.replace("sqlite://", "sqlite+aiosqlite://")

try:
    async_engine = create_async_engine(
        DATABASE_URL,
        echo=False,
        pool_size=20,          # Connection pool size
        max_overflow=10,       # Max connections to create beyond pool_size
        pool_timeout=30,       # Timeout for getting connection from pool
        pool_recycle=1800,     # Recycle connections after 30 minutes
        future=True
    )
except ImportError as e:
    print(f"Async DB setup failed: {e}")
    async_engine = None
except Exception as e:
    print(f"Async DB setup failed: {e}")
    async_engine = None
    AsyncSessionLocal = None

if async_engine:
    try:
        AsyncSessionLocal = sessionmaker(
            bind=async_engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False
        )
    except Exception as e:
        print(f"Session maker failed: {e}")
        AsyncSessionLocal = None
else:
    if 'AsyncSessionLocal' not in locals():
        AsyncSessionLocal = None

@asynccontextmanager
async def get_async_db():

    if AsyncSessionLocal is None:
        # Fallback for when async engine failed to initialize
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
