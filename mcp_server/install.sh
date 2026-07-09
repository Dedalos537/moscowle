#!/bin/bash
# Moscowle IA - Instalador del servidor MCP para Claude Desktop

set -e

MCP_DIR="$(cd "$(dirname "$0")" && pwd)"
CONFIG_SRC="$MCP_DIR/claude_desktop_config.json"

echo "=== Moscowle IA - Instalador MCP ==="
echo ""

# 1. Verificar Python
echo "1. Verificando Python..."
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 no encontrado"
    exit 1
fi
echo "   Python: $(python3 --version)"

# 2. Verificar uv
echo "2. Verificando uv..."
if ! command -v uv &> /dev/null; then
    echo "Error: uv no encontrado. Instalar con: curl -LsSf https://astral.sh/uv/install.sh | sh"
    exit 1
fi
echo "   uv: $(uv --version)"

# 3. Instalar dependencias
echo "3. Instalando dependencias..."
cd "$MCP_DIR"
uv sync
echo "   Dependencias instaladas"

# 4. Detectar plataforma Claude Desktop
echo "4. Detectando configuración de Claude Desktop..."
if [[ "$OSTYPE" == "darwin"* ]]; then
    CLAUDE_CONFIG_DIR="$HOME/Library/Application Support/Claude"
elif [[ "$OSTYPE" == "msys" || "$OSTYPE" == "cygwin" ]]; then
    CLAUDE_CONFIG_DIR="$APPDATA/Claude"
else
    CLAUDE_CONFIG_DIR="$HOME/.config/claude"
fi

CLAUDE_CONFIG="$CLAUDE_CONFIG_DIR/claude_desktop_config.json"

echo "   Config: $CLAUDE_CONFIG"

# 5. Backup y merge de configuración
if [ -f "$CLAUDE_CONFIG" ]; then
    echo "5. Configuración existente encontrada. Creando backup..."
    cp "$CLAUDE_CONFIG" "$CLAUDE_CONFIG.backup.$(date +%Y%m%d%H%M%S)"
    
    # Usar Python para hacer merge sin sobrescribir otras configs
    python3 -c "
import json, sys

with open('$CLAUDE_CONFIG') as f:
    existing = json.load(f)

with open('$CONFIG_SRC') as f:
    mcp_config = json.load(f)

existing.setdefault('mcpServers', {}).update(mcp_config['mcpServers'])

with open('$CLAUDE_CONFIG', 'w') as f:
    json.dump(existing, f, indent=2)

print('   Configuración actualizada con Moscowle MCP')
"
else
    echo "5. Creando configuración de Claude Desktop..."
    mkdir -p "$CLAUDE_CONFIG_DIR"
    cp "$CONFIG_SRC" "$CLAUDE_CONFIG"
    echo "   Configuración creada"
fi

echo ""
echo "=== ¡Instalación completada! ==="
echo ""
echo "Próximos pasos:"
echo "1. Reinicia Claude Desktop"
echo "2. En Claude, verás el icono MCP (🔧) en la barra lateral"
echo "3. Puedes preguntar sobre pacientes, sesiones, métricas, etc."
echo ""
echo "Ejemplo:"
echo '  "Analiza al paciente ID 5 y dame su progreso"'
echo ""
