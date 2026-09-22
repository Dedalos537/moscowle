# Backend
The backend is a Flask application utilizing a service-repository pattern.

## Key Components
- **`app/bootstrap.py`**: Initializes extensions, registers blueprints, and configures security headers.
- **`server_ubuntu.py`**: The production entry point using `eventlet` for SocketIO support.
- **Database**: Uses SQLAlchemy with a routing mechanism for read-replicas.

## Flow
User Request $\rightarrow$ Route $\rightarrow$ Service $\rightarrow$ Model $\rightarrow$ DB.

Links: [[Core.MCP]], [[Core.LLM_Chain]]
