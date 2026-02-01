
from app import create_app
from flask import url_for

app = create_app()

with app.app_context():
    print("Blueprints registered:", list(app.blueprints.keys()))
    
    if 'api' in app.blueprints:
        print("API blueprint IS registered.")
        try:
            url = url_for('api.get_notifications')
            print(f"URL for api.get_notifications: {url}")
        except Exception as e:
            print(f"Failed to build URL: {e}")
    else:
        print("API blueprint is NOT registered!")
