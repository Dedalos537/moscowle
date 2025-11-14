"""
Conexión simplificada a la base de datos
"""

import pymysql
from contextlib import contextmanager
from typing import Optional, Dict, Any, List
from app.core.config import get_settings
from app.core.logging import get_logger

settings = get_settings()
logger = get_logger("database")

# Pool de conexiones simple
_connection_pool = []
_max_connections = 20


def init_db_pool():
    """Inicializar pool de conexiones"""
    logger.info("Initializing database connection pool")


def close_db_pool():
    """Cerrar pool de conexiones"""
    global _connection_pool
    for conn in _connection_pool:
        try:
            conn.close()
        except:
            pass
    _connection_pool.clear()
    logger.info("Database connection pool closed")


def get_connection():
    """Obtener conexión a la base de datos"""
    return pymysql.connect(
        host=settings.DB_HOST,
        user=settings.DB_USER,
        password=settings.DB_PASSWORD,
        database=settings.DB_NAME,
        charset='utf8mb4',
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=False
    )


@contextmanager
def get_db_session():
    """Context manager para sesiones de base de datos"""
    conn = None
    try:
        conn = get_connection()
        session = DatabaseSession(conn)
        yield session
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"Database session error: {e}")
        raise
    finally:
        if conn:
            conn.close()


class DatabaseSession:
    """Sesión de base de datos simplificada"""
    
    def __init__(self, connection):
        self.connection = connection
        self.cursor = connection.cursor()
        self._in_transaction = False
    
    def execute_query(self, query: str, params=None) -> List[Dict[str, Any]]:
        """Ejecutar query SELECT"""
        try:
            self.cursor.execute(query, params or ())
            return self.cursor.fetchall()
        except Exception as e:
            logger.error(f"Query error: {e}")
            raise
    
    def execute_update(self, query: str, params=None) -> int:
        """Ejecutar query INSERT/UPDATE/DELETE"""
        try:
            result = self.cursor.execute(query, params or ())
            return self.cursor.rowcount
        except Exception as e:
            logger.error(f"Update error: {e}")
            raise
    
    def begin_transaction(self):
        """Iniciar transacción"""
        self._in_transaction = True
    
    def commit(self):
        """Confirmar transacción"""
        self.connection.commit()
        self._in_transaction = False
    
    def rollback(self):
        """Cancelar transacción"""
        self.connection.rollback()
        self._in_transaction = False
    
    def get_last_insert_id(self) -> int:
        """Obtener último ID insertado"""
        return self.cursor.lastrowid
    
    def __del__(self):
        """Cleanup"""
        if hasattr(self, 'cursor') and self.cursor:
            self.cursor.close()