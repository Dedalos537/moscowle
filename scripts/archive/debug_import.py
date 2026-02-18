
try:
    print("Attempting to import app.routes.api_routes...")
    from app.routes import api_routes
    print("Import successful!")
except Exception as e:
    import traceback
    print("Import failed:")
    traceback.print_exc()
