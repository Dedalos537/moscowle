import logging
from typing import Callable

from app.extensions import cache

logger = logging.getLogger('app')

CONTEXT_CACHE_KEY = 'full_context'


def cache_get(key: str, loader_func: Callable | None = None, timeout: int = 300):
    data = cache.get(key)
    if data is not None:
        logger.info(f'Cache HIT: {key}')
        return data
    logger.info(f'Cache MISS: {key}, loading...')
    if loader_func:
        data = loader_func()
        if data is not None:
            cache.set(key, data, timeout=timeout)
        return data
    return None


def cache_invalidate(key: str = None):
    if key:
        cache.delete(key)
        logger.info(f'Cache invalidated: {key}')
    else:
        cache.clear()
        logger.info('Cache cleared')


def invalidate_context():
    cache_invalidate(CONTEXT_CACHE_KEY)
