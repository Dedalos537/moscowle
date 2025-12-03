#!/bin/bash

# Script para iniciar solo el backend con K-Means
# Uso: ./start_backend_only.sh

set -e

echo "🔧 Iniciando solo Backend con K-Means..."
echo "========================================"

# Crear archivo .env si no existe
if [ ! -f backend/.env ]; then
    echo "📝 Creando archivo .env..."
    cat > backend/.env << 'EOF'
FLASK_ENV=development
FLASK_APP=wsgi:app
SECRET_KEY=dev-secret-key-change-in-production
DB_HOST=db
DB_USER=root
DB_PASSWORD=Rucula_530
DB_NAME=Moscowle_Complete
DATABASE_URL=mysql+pymysql://root:Rucula_530@db/Moscowle_Complete
EOF
    echo "   ✅ .env creado"
fi

# Limpiar
echo -e "\n1️⃣ Limpiando ambiente..."
docker-compose -f backend/docker-compose.override.yml down 2>/dev/null || true

# Construir
echo -e "\n2️⃣ Construyendo imagen..."
docker-compose -f backend/docker-compose.override.yml build

# Iniciar
echo -e "\n3️⃣ Iniciando Backend..."
docker-compose -f backend/docker-compose.override.yml up -d

echo -e "\n========================================"
echo "✅ Backend iniciado"
echo "========================================"
echo ""
echo "📊 API Backend: http://localhost:8000"
echo ""
echo "📝 Ver logs:"
echo "   docker-compose logs -f"
echo ""
echo "🛑 Detener:"
echo "   docker-compose down"
echo ""
