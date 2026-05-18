from typing import Any
from functools import wraps
from flask import jsonify

def api_response(data: Any = None, message: str = "Success", status_code: int = 200, success: bool = True):
    return jsonify({
        "success": success,
        "message": message,
        "data": data,
        "timestamp": datetime.utcnow().isoformat()
    }), status_code

from app.dao.db_async import get_async_db
from app.dao.base import BaseDAO
from datetime import datetime

async def get_dao(dao_class, *args, **kwargs):
    async with get_async_db() as session:
        yield dao_class(session)
