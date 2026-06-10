from app.dao.db_async import get_async_db
from app.dao.base import BaseDAO
from datetime import datetime

async def get_dao(dao_class, *args, **kwargs):
    async with get_async_db() as session:
        yield dao_class(session)
