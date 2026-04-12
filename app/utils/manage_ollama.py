import os
import subprocess
import time
import requests
import socket
import logging

# Configurar logger para que salga en el terminal de Flask
logger = logging.getLogger('app')

def is_ollama_running():
    """Verifica si el puerto 11434 está siendo escuchado."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('127.0.0.1', 11434)) == 0

def check_model_exists(model_name="llama3.1:8b"):
    """Verifica si el modelo específico está disponible en Ollama."""
    try:
        response = requests.get("http://127.0.0.1:11434/api/tags")
        if response.status_code == 200:
            models = response.json().get('models', [])
            return any(m['name'] == model_name for m in models)
        return False
    except Exception:
        return False

def start_ollama():
    """Intenta iniciar el proceso de Ollama en segundo plano."""
    if is_ollama_running():
        logger.info("✅ Ollama ya está corriendo.")
        return True
    
    logger.info("🚀 Iniciando Ollama...")
    try:
        # Intentar rutas comunes de MacOS (Homebrew y System)
        ollama_bin = "/opt/homebrew/bin/ollama"
        if not os.path.exists(ollama_bin):
            ollama_bin = "/usr/local/bin/ollama"
        if not os.path.exists(ollama_bin):
            import shutil
            ollama_bin = shutil.which("ollama") or "ollama"

        # Usamos nohup para que siga corriendo independientemente del proceso de Flask
        subprocess.Popen([ollama_bin, "serve"], 
                         stdout=subprocess.DEVNULL, 
                         stderr=subprocess.DEVNULL,
                         start_new_session=True)
        
        # Esperar a que el servidor levante (máximo 15 segundos)
        for i in range(15):
            if is_ollama_running():
                logger.info(f"✅ Ollama iniciado exitosamente tras {i+1}s.")
                return True
            time.sleep(1)
            logger.info(f"...esperando sincronización de IA ({i+1}/15)")
        
        return False
    except FileNotFoundError:
        logger.error("❌ Error: No se encontró el ejecutable 'ollama'. Asegúrate de tenerlo instalado.")
        return False
    except Exception as e:
        logger.error(f"❌ Error al iniciar Ollama: {e}")
        return False

def init_ia_check():
    """Función para ser llamada desde el arranque de Flask."""
    logger.info("--- [ IA CHECK: COMPAÑERO LLAMA ] ---")
    if start_ollama():
        if check_model_exists("llama3.1:8b"):
            logger.info("✅ Modelo llama3.1:8b listo para usar.")
            return True
        else:
            logger.warning("⚠️ Ollama está activo pero el modelo 'llama3.1:8b' no se encontró.")
            logger.info("💡 Ejecuta 'ollama pull llama3.1:8b' en tu terminal.")
            return False
    else:
        logger.error("❌ No se pudo conectar con Ollama. La IA estará desactivada.")
        return False

if __name__ == "__main__":
    # Test directo
    init_ia_check()
