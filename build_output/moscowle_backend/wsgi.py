"""
WSGI config for PythonAnywhere.
PythonAnywhere: Web tab → Code → WSGI configuration file
"""
import sys
import os

# ── Ruta del proyecto ──
path = '/home/moscowle'
if path not in sys.path:
    sys.path.insert(0, path)

# ── Activar virtualenv ──
venv_path = '/home/moscowle/.virtualenvs/moscowle_backend/lib/python3.11/site-packages'
if os.path.isdir(venv_path) and venv_path not in sys.path:
    sys.path.insert(0, venv_path)

from app import create_app
application = create_app()
