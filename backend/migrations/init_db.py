"""
Script para inicializar la base de datos
"""

import os
import sys
import pymysql
from pathlib import Path

# Agregar el directorio parent al path para importar módulos
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.config import get_settings
from app.core.logging import setup_logging, get_logger

setup_logging()
logger = get_logger("init_db")
settings = get_settings()


def execute_sql_file(connection, file_path):
    """Ejecutar archivo SQL"""
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            sql_content = file.read()
        
        # Dividir por declaraciones
        statements = sql_content.split(';')
        
        with connection.cursor() as cursor:
            for statement in statements:
                statement = statement.strip()
                if statement and not statement.startswith('--'):
                    cursor.execute(statement)
        
        connection.commit()
        logger.info(f"SQL file executed successfully: {file_path}")
        
    except Exception as e:
        logger.error(f"Error executing SQL file {file_path}: {e}")
        connection.rollback()
        raise


def init_database():
    """Inicializar base de datos"""
    try:
        # Conectar sin especificar base de datos
        connection = pymysql.connect(
            host=settings.DB_HOST,
            user=settings.DB_USER,
            password=settings.DB_PASSWORD,
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor
        )
        
        logger.info("Connected to MySQL server")
        
        # Ejecutar script de inicialización
        script_path = Path(__file__).parent / "init_database.sql"
        execute_sql_file(connection, script_path)
        
        logger.info("Database initialization completed successfully")
        
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        raise
    
    finally:
        if 'connection' in locals():
            connection.close()


if __name__ == "__main__":
    init_database()