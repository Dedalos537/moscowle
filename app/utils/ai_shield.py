import subprocess
import time
import requests
import os
import sys

def check_ollama():
    """Verifica si el servidor de Ollama está respondiendo."""
    try:
        response = requests.get('http://127.0.0.1:11434/api/tags', timeout=2)
        return response.status_code == 200
    except:
        return False

def start_ollama():
    """Inicia el servidor de Ollama si no está corriendo."""
    if check_ollama():
        print("[AI-SHIELD] Ollama ya está en ejecución.")
        return True

    print(" [AI-SHIELD] Iniciando servidor Ollama...")
    
    # Intentar encontrar el ejecutable de Ollama
    ollama_path = "/opt/homebrew/bin/ollama" # Ruta detectada en este sistema
    if not os.path.exists(ollama_path):
        import shutil
        ollama_path = shutil.which("ollama") or "ollama"

    try:
        # Iniciar en segundo plano sin bloquear el terminal de Flask
        # Redirigimos la salida a un log específico para no contaminar el terminal principal
        with open('logs/ollama_startup.log', 'a') as log_file:
            subprocess.Popen(
                [ollama_path, "serve"],
                stdout=log_file,
                stderr=log_file,
                start_new_session=True
            )
        
        # Esperar a que el servidor responda (máximo 15 segundos)
        for i in range(15):
            time.sleep(1)
            if check_ollama():
                print(f"[AI-SHIELD] Ollama iniciado correctamente tras {i+1}s.")
                return True
        
        print("[AI-SHIELD] Tiempo de espera agotado al iniciar Ollama.")
        return False
    except Exception as e:
        print(f"[AI-SHIELD] Error crítico al intentar iniciar Ollama: {e}")
        return False

if __name__ == "__main__":
    start_ollama()
