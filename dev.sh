#!/bin/sh
# Moscowle IA — Dev Helper (Cross-platform)
# Compatible con Linux, macOS, Windows (Git Bash / WSL2 / MSYS2)
# Uso: ./dev.sh [start|stop|restart|logs|rebuild|db|ps]

set -e

COMPOSE_FILE="docker-compose.dev.yml"
CMD="${1:-start}"

# Detect OS for cross-platform support
detect_os() {
    case "$(uname -s)" in
        Linux*)   echo "linux" ;;
        Darwin*)  echo "mac" ;;
        MINGW*|MSYS*|CYGWIN*) echo "windows" ;;
        *)        echo "unknown" ;;
    esac
}

OS=$(detect_os)

# Check prerequisites
if ! command -v docker >/dev/null 2>&1; then
    echo "Error: docker no está instalado."
    echo "  Linux:   https://docs.docker.com/engine/install/"
    echo "  macOS:   https://docs.docker.com/desktop/setup/install/mac-install/"
    echo "  Windows: https://docs.docker.com/desktop/setup/install/windows-install/"
    exit 1
fi

case "$CMD" in
    start)
        echo "Iniciando stack de desarrollo..."
        docker compose -f "$COMPOSE_FILE" up --watch -d
        echo ""
        echo "  Backend:  http://localhost:5001"
        echo "  Frontend: http://localhost:4200"
        echo "  DB:       postgresql://moscowle:moscowlepass@localhost:5432/moscowle"
        echo ""
        echo "Para ver logs: ./dev.sh logs"
        ;;
    stop)
        echo "Deteniendo stack..."
        docker compose -f "$COMPOSE_FILE" down
        ;;
    restart)
        echo "Reconstruyendo y reiniciando..."
        docker compose -f "$COMPOSE_FILE" down
        docker compose -f "$COMPOSE_FILE" build
        docker compose -f "$COMPOSE_FILE" up -d
        ;;
    logs)
        docker compose -f "$COMPOSE_FILE" logs -f
        ;;
    rebuild)
        echo "Reconstruyendo desde cero..."
        docker compose -f "$COMPOSE_FILE" build --no-cache
        docker compose -f "$COMPOSE_FILE" up -d
        ;;
    db)
        docker compose -f "$COMPOSE_FILE" exec db psql -U moscowle
        ;;
    ps)
        docker compose -f "$COMPOSE_FILE" ps
        ;;
    *)
        echo "Uso: ./dev.sh [comando]"
        echo ""
        echo "Comandos:"
        echo "  start    Arranca DB, backend y frontend (hot-reload)"
        echo "  stop     Detiene todo"
        echo "  restart  Reconstruye imágenes y reinicia"
        echo "  logs     Sigue los logs de todos los servicios"
        echo "  rebuild  Reconstruye desde cero (--no-cache) y reinicia"
        echo "  db       Abre psql en la base de datos"
        echo "  ps       Muestra el estado de los servicios"
        exit 1
        ;;
esac
