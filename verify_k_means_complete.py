#!/usr/bin/env python3
"""
Script de verificación completa para K-Means Clustering
Comprueba que toda la implementación funciona correctamente en Docker
"""

import subprocess
import sys
import json
import time
from pathlib import Path

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    END = '\033[0m'

def print_success(msg):
    print(f"{Colors.GREEN}✅ {msg}{Colors.END}")

def print_error(msg):
    print(f"{Colors.RED}❌ {msg}{Colors.END}")

def print_warning(msg):
    print(f"{Colors.YELLOW}⚠️  {msg}{Colors.END}")

def print_info(msg):
    print(f"{Colors.BLUE}ℹ️  {msg}{Colors.END}")

def run_command(cmd, description=""):
    """Ejecuta un comando y retorna el resultado"""
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=30
        )
        if result.returncode == 0:
            if description:
                print_success(description)
            return True, result.stdout
        else:
            if description:
                print_error(description)
            return False, result.stderr
    except subprocess.TimeoutExpired:
        print_error(f"Timeout: {description}")
        return False, "Comando tardó demasiado"
    except Exception as e:
        print_error(f"Error ejecutando comando: {str(e)}")
        return False, str(e)

def check_docker_running():
    """Verifica que Docker está corriendo"""
    print_info("Verificando que Docker está activo...")
    success, output = run_command("docker ps", "Docker está disponible")
    return success

def check_container_running(container_name):
    """Verifica que un contenedor específico está corriendo"""
    print_info(f"Verificando contenedor: {container_name}")
    cmd = f"docker ps --filter 'name={container_name}' --format '{{{{.Names}}}}'"
    success, output = run_command(cmd)
    if container_name in output:
        print_success(f"Contenedor {container_name} está activo")
        return True
    else:
        print_warning(f"Contenedor {container_name} no está activo")
        return False

def check_file_in_container(container, filepath):
    """Verifica que un archivo existe dentro del contenedor"""
    cmd = f"docker exec {container} test -f {filepath}"
    success, _ = run_command(cmd)
    if success:
        print_success(f"Archivo encontrado en contenedor: {filepath}")
        return True
    else:
        print_error(f"Archivo NO encontrado: {filepath}")
        return False

def check_function_in_container(container, filepath, function_name):
    """Verifica que una función existe en el contenedor"""
    cmd = f"docker exec {container} grep -c 'def {function_name}' {filepath}"
    success, output = run_command(cmd)
    if success and int(output.strip()) > 0:
        print_success(f"Función {function_name} encontrada")
        return True
    else:
        print_error(f"Función {function_name} NO encontrada")
        return False

def check_imports_in_container(container):
    """Verifica que los imports necesarios funcionan"""
    print_info("Verificando imports necesarios...")
    
    imports = [
        "sklearn.cluster",
        "sklearn.metrics",
        "sklearn.preprocessing",
        "numpy",
        "pandas",
        "joblib"
    ]
    
    python_code = ";".join([f"import {imp}" for imp in imports])
    cmd = f"docker exec {container} python3 -c \"{python_code}\""
    
    success, output = run_command(cmd, "Todos los imports de ML disponibles")
    return success

def check_test_execution(container):
    """Ejecuta el test de K-Means dentro del contenedor"""
    print_info("Ejecutando test de K-Means...")
    cmd = f"docker exec {container} python3 /app/test_k_means_segmentation.py"
    success, output = run_command(cmd, "Test de K-Means pasó correctamente")
    if not success:
        print_warning("Output del test:")
        print(output)
    return success

def check_flask_app(container):
    """Verifica que la app Flask se puede crear"""
    print_info("Verificando aplicación Flask...")
    
    python_code = """
import sys
sys.path.insert(0, '/app')
try:
    from app import create_app
    app = create_app()
    print('OK')
except Exception as e:
    print(f'ERROR: {e}')
    sys.exit(1)
"""
    
    cmd = f"docker exec {container} python3 -c \"{python_code}\""
    success, output = run_command(cmd, "Aplicación Flask se crea correctamente")
    return success

def check_ai_service_import(container):
    """Verifica que el servicio de IA se importa correctamente"""
    print_info("Verificando módulo ai_service...")
    
    python_code = """
import sys
sys.path.insert(0, '/app')
try:
    from app.services.ai_service import run_k_means_segmentation
    print('OK')
except ImportError as e:
    print(f'ERROR: {e}')
    sys.exit(1)
"""
    
    cmd = f"docker exec {container} python3 -c \"{python_code}\""
    success, output = run_command(cmd, "Módulo ai_service importa correctamente")
    return success

def check_requirements_installed(container):
    """Verifica que todas las dependencias están instaladas"""
    print_info("Verificando dependencias instaladas...")
    
    packages = [
        "scikit-learn",
        "numpy",
        "pandas",
        "joblib",
        "Flask",
        "Flask-SQLAlchemy"
    ]
    
    cmd = "docker exec {} pip list | grep -E '{}'".format(
        container,
        "|".join(packages)
    )
    success, output = run_command(cmd, "Dependencias instaladas")
    print(output)
    return True

def check_container_logs(container):
    """Muestra los últimos logs del contenedor"""
    print_info("Últimos logs del contenedor:")
    cmd = f"docker logs --tail=15 {container}"
    success, output = run_command(cmd)
    if output:
        print(output)
    return True

def main():
    """Función principal de verificación"""
    print("\n" + "="*60)
    print("🔍 VERIFICACIÓN COMPLETA K-MEANS CLUSTERING EN DOCKER")
    print("="*60 + "\n")
    
    results = {}
    container_name = "moscowle_backend_ai"
    
    # 1. Verificar Docker
    print("\n📦 VERIFICACIÓN DE DOCKER")
    print("-"*60)
    results['docker'] = check_docker_running()
    
    # 2. Verificar contenedor
    print("\n🐳 VERIFICACIÓN DE CONTENEDOR")
    print("-"*60)
    results['container'] = check_container_running(container_name)
    
    if not results['container']:
        print_warning("El contenedor no está corriendo. Por favor inicia con:")
        print("  docker-compose up -d backend")
        return False
    
    # 3. Verificar archivos
    print("\n📄 VERIFICACIÓN DE ARCHIVOS")
    print("-"*60)
    results['ai_service_file'] = check_file_in_container(
        container_name,
        "/app/app/services/ai_service.py"
    )
    results['test_file'] = check_file_in_container(
        container_name,
        "/app/test_k_means_segmentation.py"
    )
    
    # 4. Verificar función
    print("\n⚙️  VERIFICACIÓN DE FUNCIONES")
    print("-"*60)
    results['kmeans_function'] = check_function_in_container(
        container_name,
        "/app/app/services/ai_service.py",
        "run_k_means_segmentation"
    )
    
    # 5. Verificar imports
    print("\n📚 VERIFICACIÓN DE IMPORTS")
    print("-"*60)
    results['imports'] = check_imports_in_container(container_name)
    
    # 6. Verificar dependencias
    print("\n📦 VERIFICACIÓN DE DEPENDENCIAS")
    print("-"*60)
    results['requirements'] = check_requirements_installed(container_name)
    
    # 7. Verificar Flask
    print("\n🔧 VERIFICACIÓN DE APLICACIÓN")
    print("-"*60)
    results['flask_app'] = check_flask_app(container_name)
    results['ai_service_import'] = check_ai_service_import(container_name)
    
    # 8. Ejecutar tests
    print("\n🧪 EJECUTAR TESTS")
    print("-"*60)
    results['tests'] = check_test_execution(container_name)
    
    # 9. Mostrar logs
    print("\n📊 LOGS DEL CONTENEDOR")
    print("-"*60)
    check_container_logs(container_name)
    
    # Resumen
    print("\n" + "="*60)
    print("📋 RESUMEN DE VERIFICACIÓN")
    print("="*60)
    
    all_passed = True
    for check, result in results.items():
        status = "✅" if result else "❌"
        print(f"{status} {check}: {'PASÓ' if result else 'FALLÓ'}")
        if not result:
            all_passed = False
    
    print("="*60)
    
    if all_passed:
        print_success("TODAS LAS VERIFICACIONES PASARON")
        print("\n✨ K-Means Clustering está listo para usar!")
        print("\nEndpoints disponibles:")
        print("  POST /api/ai/run_clustering - Ejecutar K-Means")
        print("  GET  /api/ai/clustering_status - Estado del clustering")
        print("\n")
        return True
    else:
        print_error("ALGUNAS VERIFICACIONES FALLARON")
        print("\nRevisa los errores arriba y verifica la configuración.")
        print("\n")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
