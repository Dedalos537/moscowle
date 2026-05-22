import time
from datetime import datetime, timedelta
from app.services.context_loader_service import context_loader
import logging

logger = logging.getLogger('app')

class ContextCache:
    """Caché de contexto con expiración automática"""
    
    def __init__(self, ttl_seconds=300):  # 5 minutos por defecto
        self.ttl = ttl_seconds
        self.cache = {}
        self.timestamps = {}
    
    def get(self, key: str, loader_func=None):
        """Obtener contexto del caché o recargarlo"""
        current_time = time.time()
        
        # Si existe en caché y no ha expirado
        if key in self.cache:
            cached_time = self.timestamps.get(key, 0)
            if current_time - cached_time < self.ttl:
                logger.info(f"✓ Contexto {key} desde caché (edad: {int(current_time - cached_time)}s)")
                return self.cache[key]
        
        # Recargar desde BD
        if loader_func:
            logger.info(f"⟲ Recargando contexto {key}...")
            data = loader_func()
            self.cache[key] = data
            self.timestamps[key] = current_time
            return data
        
        return None
    
    def invalidate(self, key: str = None):
        """Invalidar caché"""
        if key:
            if key in self.cache:
                del self.cache[key]
                del self.timestamps[key]
                logger.info(f"✓ Caché invalidada: {key}")
        else:
            self.cache.clear()
            self.timestamps.clear()
            logger.info("✓ Caché global invalidada")

# Instancia global
context_cache = ContextCache(ttl_seconds=300)  # 5 minutos

def get_cached_context():
    """Obtener contexto con caché automático"""
    return context_cache.get(
        'full_context',
        loader_func=context_loader.get_full_context
    )

def get_cached_context_text():
    """Obtener contexto formateado con caché automático"""
    context = get_cached_context()
    if context:
        return context_loader.format_context_for_llama(context)
    return ""

def invalidate_context():
    """Invalidar caché (llamar cuando cambien datos de BD)"""
    context_cache.invalidate('full_context')
