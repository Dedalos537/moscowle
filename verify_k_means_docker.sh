#!/bin/bash

# Script para verificar que el K-Means clustering funciona correctamente en Docker
# Uso: ./verify_k_means_docker.sh

set -e

echo "🔍 Verificando K-Means en Docker..."
echo "=================================="

# 1. Verificar que los archivos están en el contenedor
echo -e "\n✓ Verificando archivos..."
docker exec moscowle_backend_ai ls -lh /app/app/services/ai_service.py || {
    echo "❌ Error: ai_service.py no encontrado"
    exit 1
}

# 2. Contar líneas de la función run_k_means_segmentation
echo -e "\n✓ Verificando función K-Means..."
LINES=$(docker exec moscowle_backend_ai grep -c "def run_k_means_segmentation" /app/app/services/ai_service.py)
if [ "$LINES" -eq 1 ]; then
    echo "   ✅ Función run_k_means_segmentation encontrada"
else
    echo "   ❌ Función no encontrada o duplicada"
    exit 1
fi

# 3. Verificar imports necesarios
echo -e "\n✓ Verificando importes..."
docker exec moscowle_backend_ai python3 -c "
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from sklearn.preprocessing import StandardScaler
import numpy
import pandas
print('   ✅ Todos los imports de ML disponibles')
" || {
    echo "   ❌ Error en imports"
    exit 1
}

# 4. Test de la función en el contenedor
echo -e "\n✓ Ejecutando test del K-Means..."
docker exec moscowle_backend_ai python3 /app/test_k_means_segmentation.py || {
    echo "   ❌ Test falló"
    exit 1
}

# 5. Verificar que la API responde
echo -e "\n✓ Verificando endpoints API..."
docker exec moscowle_backend_ai python3 -c "
import sys
sys.path.insert(0, '/app')
from app import create_app
app = create_app()
print('   ✅ Aplicación Flask creada correctamente')
" || {
    echo "   ❌ Error al crear la aplicación"
    exit 1
}

# 6. Logs del contenedor
echo -e "\n✓ Últimos logs del contenedor:"
docker logs --tail=20 moscowle_backend_ai

echo -e "\n=================================="
echo "✅ VERIFICACIÓN COMPLETA - TODO OK"
echo "=================================="
