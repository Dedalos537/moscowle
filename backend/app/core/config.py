"""
Configuración de la aplicación
"""

from pydantic_settings import BaseSettings
from typing import List
import os


class Settings(BaseSettings):
    """Configuración de la aplicación"""
    
    # Información de la aplicación
    APP_NAME: str = "Moscowle Backend"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True
    
    # Base de datos
    DB_HOST: str = "localhost"
    DB_USER: str = "root"  
    DB_PASSWORD: str = "Rucula_530"
    DB_NAME: str = "Moscowle_Complete"
    DATABASE_URL: str = "mysql+pymysql://root:Rucula_530@localhost/Moscowle_Complete"
    
    # JWT
    SECRET_KEY: str = "tu_clave_secreta_super_segura_aqui_cambiar_en_produccion"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # Servidor
    HOST: str = "127.0.0.1"
    PORT: int = 8001
    
    # CORS
    ALLOWED_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:5173", 
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
        "http://localhost:3001",
        "http://127.0.0.1:3001",
        "http://localhost:3002", 
        "http://127.0.0.1:3002",
        "http://localhost:3003",
        "http://127.0.0.1:3003"
    ]
    
    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "logs/app.log"
    
    # Email
    SMTP_SERVER: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    EMAIL_USER: str = "tu_email@gmail.com"
    EMAIL_PASSWORD: str = "tu_password_app"
    
    class Config:
        env_file = ".env"
        case_sensitive = True


# Instancia global de configuración
_settings = None


def get_settings() -> Settings:
    """Obtener configuración singleton"""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings