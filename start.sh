#!/bin/bash
DIR="$(cd "$(dirname "$0")" && pwd)"
source "$DIR/venv/bin/activate"
gunicorn --workers 2 --bind 0.0.0.0:5001 --timeout 120 --log-level info run:app &
echo "Backend PID: $!"
cd "$DIR/edysync"
npx ng serve --host 0.0.0.0 --port 4200 --poll 2000 &
echo "Frontend PID: $!"
wait
