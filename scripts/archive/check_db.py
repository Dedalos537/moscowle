
from app import create_app, db
from app.models import User
from sqlalchemy import inspect

app = create_app()

with app.app_context():
    print("Database URI:", app.config['SQLALCHEMY_DATABASE_URI'])
    try:
        inspector = inspect(db.engine)
        tables = inspector.get_table_names()
        print("Tables found:", tables)
        
        if 'user' in tables:
            columns = [c['name'] for c in inspector.get_columns('user')]
            print("User columns:", columns)
            
            # Try a query
            user_count = User.query.count()
            print(f"User count: {user_count}")
        else:
            print("User table NOT found!")

    except Exception as e:
        print(f"Database error: {e}")
        import traceback
        traceback.print_exc()
