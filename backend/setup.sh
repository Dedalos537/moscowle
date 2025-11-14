#!/bin/bash

# Script de configuración del backend unificado
# Centro de Terapias Juan Pablo II

echo "🚀 Configurando Backend Unificado Moscowle..."

# Crear directorio de logs
mkdir -p logs

# Crear entorno virtual si no existe
if [ ! -d "venv" ]; then
    echo "📦 Creando entorno virtual..."
    python3 -m venv venv
fi

# Activar entorno virtual
echo "✅ Activando entorno virtual..."
source venv/bin/activate

# Instalar dependencias
echo "📚 Instalando dependencias..."
pip install --upgrade pip
pip install -r requirements.txt

# Verificar que el archivo .env existe
if [ ! -f ".env" ]; then
    echo "⚠️  Archivo .env no encontrado. Asegúrate de configurar las variables de entorno."
    exit 1
fi

# Inicializar base de datos
echo "🗄️  Inicializando base de datos..."
python migrations/init_db.py

echo "✨ ¡Backend configurado correctamente!"
echo ""
echo "Para ejecutar el servidor:"
echo "  source venv/bin/activate"
echo "  python main.py"
echo ""
echo "O con uvicorn:"
echo "  uvicorn main:app --reload --host 127.0.0.1 --port 8001"