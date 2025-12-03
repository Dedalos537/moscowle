#!/bin/bash

# Script de Verificación del Sistema de Mensajería
# Propósito: Validar que todos los componentes están en lugar
# Fecha: 3 de diciembre de 2025

echo "🔍 Verificando Sistema de Mensajería..."
echo "========================================\n"

# Colores para output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Verificar archivos backend
echo "📦 Verificando Backend..."
files_backend=(
    "backend/app/models/contact.py"
    "backend/app/services/contact_service.py"
    "backend/app/schemas/contact_schema.py"
    "backend/app/routes/contact_routes.py"
    "backend/migrations/add_contact_messages_tables.sql"
)

for file in "${files_backend[@]}"; do
    if [ -f "$file" ]; then
        echo -e "${GREEN}✓${NC} $file"
    else
        echo -e "${RED}✗${NC} $file (NO ENCONTRADO)"
    fi
done

# Verificar archivos frontend
echo "\n🎨 Verificando Frontend..."
files_frontend=(
    "Principal_Page/src/components/organisms/Contact.tsx"
    "Dashboard Administrativo Integral/src/components/dashboard/MessagesModule.tsx"
)

for file in "${files_frontend[@]}"; do
    if [ -f "$file" ]; then
        echo -e "${GREEN}✓${NC} $file"
    else
        echo -e "${RED}✗${NC} $file (NO ENCONTRADO)"
    fi
done

# Verificar líneas de código
echo "\n📊 Estadísticas de Código..."
echo "Backend Models:"
wc -l "backend/app/models/contact.py" 2>/dev/null || echo "  Archivo no encontrado"

echo "Backend Services:"
wc -l "backend/app/services/contact_service.py" 2>/dev/null || echo "  Archivo no encontrado"

echo "Backend Routes:"
wc -l "backend/app/routes/contact_routes.py" 2>/dev/null || echo "  Archivo no encontrado"

echo "Frontend Dashboard:"
wc -l "Dashboard Administrativo Integral/src/components/dashboard/MessagesModule.tsx" 2>/dev/null || echo "  Archivo no encontrado"

# Verificar que Contact.tsx está actualizado
echo "\n🔐 Verificando Configuración de API..."
if grep -q "VITE_BACKEND_URL" "Principal_Page/src/components/organisms/Contact.tsx"; then
    echo -e "${GREEN}✓${NC} Contact.tsx usa VITE_BACKEND_URL"
else
    echo -e "${YELLOW}⚠${NC} Contact.tsx no usa VITE_BACKEND_URL (revisar)"
fi

# Verificar que MessagesModule está actualizado
if grep -q "getMessage\|loadMessages" "Dashboard Administrativo Integral/src/components/dashboard/MessagesModule.tsx"; then
    echo -e "${GREEN}✓${NC} MessagesModule.tsx tiene funciones de mensajes"
else
    echo -e "${YELLOW}⚠${NC} MessagesModule.tsx podría no tener todas las funciones"
fi

# Verificar imports en backend app
echo "\n⚙️  Verificando Integración Backend..."
if grep -q "from .routes.contact_routes import contact_bp" "backend/app/__init__.py"; then
    echo -e "${GREEN}✓${NC} contact_bp registrado en app/__init__.py"
else
    echo -e "${RED}✗${NC} contact_bp NO registrado (revisar app/__init__.py)"
fi

if grep -q "from .models import contact" "backend/app/__init__.py"; then
    echo -e "${GREEN}✓${NC} Modelos de contact importados"
else
    echo -e "${YELLOW}⚠${NC} Modelos de contact no importados (verificar)"
fi

# Resumen final
echo "\n========================================"
echo "✅ Verificación Completada"
echo ""
echo "Próximos pasos:"
echo "1. Ejecutar migración SQL:"
echo "   mysql -u root -p moscowle < backend/migrations/add_contact_messages_tables.sql"
echo ""
echo "2. Iniciar Backend (puerto 8000):"
echo "   cd backend && python app.py"
echo ""
echo "3. Iniciar Frontend (puerto 5173 y 5174):"
echo "   cd Principal_Page && npm run dev"
echo "   cd 'Dashboard Administrativo Integral' && npm run dev"
echo ""
echo "4. Probar flujo:"
echo "   - Llenar formulario en http://localhost:5173"
echo "   - Ver en dashboard http://localhost:5174"
echo ""
echo "📖 Documentación completa en: SISTEMA_MENSAJERIA_COMPLETO.md"
