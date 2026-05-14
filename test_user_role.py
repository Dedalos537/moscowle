from app import create_app
from app.extensions import db
from app.models import User

app = create_app()
with app.app_context():
    u = User.query.filter_by(email='diego.adrenalina11@gmail.com').first()
    if u:
        print(f"Diego role: {u.role}")
    else:
        print("Diego not found")
