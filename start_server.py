import eventlet
eventlet.monkey_patch()

import os
from app import create_app
from app.extensions import socketio

app = create_app()
port = int(os.environ.get('PORT', 8080))
socketio.run(app, host='0.0.0.0', port=port)
