from typing import Any, Optional
import time
import asyncio

class AsyncCache:
    """
    Simple Async In-Memory Cache for demonstration of the pattern.
    In production, replace with aioredis or similar.
    """
    _store = {}
    _ttl = {}

    @classmethod
    async def get(cls, key: str) -> Optional[Any]:
        if key in cls._store:
            if time.time() < cls._ttl.get(key, 0):
                return cls._store[key]
            else:
                del cls._store[key]
                del cls._ttl[key]
        return None

    @classmethod
    async def set(cls, key: str, value: Any, ttl: int = 300):
        cls._store[key] = value
        cls._ttl[key] = time.time() + ttl

    @classmethod
    async def delete(cls, key: str):
        if key in cls._store:
            del cls._store[key]
            del cls._ttl[key]

    @classmethod
    async def clear(cls):
        cls._store.clear()
        cls._ttl.clear()

def cached(ttl: int = 60, key_builder: Optional[callable] = None):
    """
    Decorator for async methods to cache result.
    """
    def decorator(func):
        async def wrapper(*args, **kwargs):
            if key_builder:
                key = key_builder(*args, **kwargs)
            else:
                key = f"{func.__name__}:{str(args)}:{str(kwargs)}"
            
            cached_val = await AsyncCache.get(key)
            if cached_val:
                return cached_val
            
            result = await func(*args, **kwargs)
            await AsyncCache.set(key, result, ttl)
            return result
        return wrapper
    return decorator
