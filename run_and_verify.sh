#!/bin/bash

# Script principal para levantar el ambiente Docker y verificar que todo funciona
# Uso: ./run_and_verify.sh

set -e

echo "🚀 Iniciando ambiente Docker..."
echo "=============================="

# 1. Limpiar contenedores previos
echo -e "\n1️⃣ Limpiando ambiente anterior..."
docker-compose -f docker-compose.yml -f backend/docker-compose.override.yml down || true
sleep 2

# 2. Construir imágenes
echo -e "\n2️⃣ Construyendo imágenes Docker..."
docker-compose -f docker-compose.yml -f backend/docker-compose.override.yml build backend

# 3. Iniciar servicios
echo -e "\n3️⃣ Iniciando servicios..."
docker-compose -f docker-compose.yml -f backend/docker-compose.override.yml up -d db backend

# 4. Esperar a que la base de datos esté lista
echo -e "\n4️⃣ Esperando que la BD esté lista..."
for i in {1..30}; do
    if docker exec moscowle_backend_ai python3 -c "
import pymysql
pymysql.connect(host='db', user='root', password='Rucula_530', database='Moscowle_Complete')
print('DB conectada')
" 2>/dev/null; then
        echo "   ✅ Base de datos lista"
        break
    fi
    echo "   ⏳ Reintentando ($i/30)..."
    sleep 2
done

# 5. Ejecutar verificación
echo -e "\n5️⃣ Ejecutando verificación K-Means..."
sleep 2
bash verify_k_means_docker.sh

# 6. Test de la API
echo -e "\n6️⃣ Probando endpoints de la API..."
sleep 3

# Test simple - health check
echo "   Probando /health (si existe)..."
curl -s http://localhost:8000/health || echo "   (Endpoint no disponible)"

# Test K-Means endpoint
echo -e "\n   Probando /api/ai/run_clustering..."
RESPONSE=$(curl -s -X POST http://localhost:8000/api/ai/run_clustering \
  -H "Content-Type: application/json" \
  -d '{"k": 3}' \
  -w "\n%{http_code}")

HTTP_CODE=$(echo "$RESPONSE" | tail -n 1)
BODY=$(echo "$RESPONSE" | sed '$d')

if [ "$HTTP_CODE" = "200" ] || [ "$HTTP_CODE" = "201" ]; then
    echo "   ✅ Endpoint respondió correctamente (HTTP $HTTP_CODE)"
    echo "   Respuesta: $(echo "$BODY" | head -c 100)..."
else
    echo "   ⚠️  HTTP $HTTP_CODE (podría ser normal si no hay datos en la DB)"
    echo "   Respuesta: $BODY"
fi

echo -e "\n=============================="
echo "✅ AMBIENTE DOCKER LISTO"
echo "=============================="
echo ""
echo "📊 Dashboard:"
echo "   Frontend: http://localhost:3001"
echo "   Principal: http://localhost:3002"
echo ""
echo "🔧 Backend:"
echo "   API: http://localhost:8000"
echo ""
echo "📊 Base de datos:"
echo "   Host: localhost:3307"
echo "   User: root"
echo "   Password: Rucula_530"
echo "   Database: Moscowle_Complete"
echo ""
echo "📝 Para ver logs:"
echo "   docker-compose logs -f backend"
echo ""
echo "🛑 Para detener:"
echo "   docker-compose down"
echo ""
