#!/bin/bash
# Moscowle IA — Dev Helper
# Uso: ./dev.sh [start|stop|restart|logs|rebuild|db]
# Si se ejecuta sin args, arranca todo (equivalente a 'start')

set -e

COMPOSE_FILE="docker-compose.dev.yml"
CMD="${1:-start}"

case "$CMD" in
  start)
    echo "🚀 Iniciando stack de desarrollo..."
    exec sg docker -c "
      cd '$PWD'
      docker compose -f '$COMPOSE_FILE' up --watch -d
    "
    ;;
  stop)
    echo "🛑 Deteniendo stack..."
    exec sg docker -c "cd '$PWD' && docker compose -f '$COMPOSE_FILE' down" 
    ;;
  restart)
    echo "🔄 Reiniciando stack..."
    exec sg docker -c "
      cd '$PWD'
      docker compose -f '$COMPOSE_FILE' down
      docker compose -f '$COMPOSE_FILE' build
      docker compose -f '$COMPOSE_FILE' up -d
    "
    ;;
  logs)
    exec sg docker -c "cd '$PWD' && docker compose -f '$COMPOSE_FILE' logs -f"
    ;;
  rebuild)
    echo "🔨 Reconstruyendo y reiniciando..."
    exec sg docker -c "
      cd '$PWD'
      docker compose -f '$COMPOSE_FILE' build --no-cache
      docker compose -f '$COMPOSE_FILE' up -d
    "
    ;;
  db)
    exec sg docker -c "cd '$PWD' && docker compose -f '$COMPOSE_FILE' exec db psql -U moscowle"
    ;;
  ps)
    exec sg docker -c "cd '$PWD' && docker compose -f '$COMPOSE_FILE' ps"
    ;;
  *)
    echo "Uso: ./dev.sh [start|stop|restart|logs|rebuild|db|ps]"
    echo ""
    echo "  start    Arranca la DB, backend y frontend (hot-reload activo)"
    echo "  stop     Detiene todo"
    echo "  restart  Reconstruye imágenes y reinicia"
    echo "  logs     Sigue los logs de todos los servicios"
    echo "  rebuild  Reconstruye desde cero (--no-cache) y reinicia"
    echo "  db       Abre psql en la base de datos"
    echo "  ps       Muestra el estado de los servicios"
    exit 1
    ;;
esac
