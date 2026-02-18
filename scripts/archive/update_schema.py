from app import create_app, db
from sqlalchemy import text

app = create_app()

def migrate():
    with app.app_context():
        # Check and add columns to User table
        with db.engine.connect() as conn:
            # Check for sessions_total
            try:
                conn.execute(text("ALTER TABLE user ADD COLUMN sessions_total INTEGER DEFAULT 0"))
                print("Added sessions_total column")
            except Exception as e:
                print(f"sessions_total likely exists: {e}")

            # Check for sessions_attended
            try:
                conn.execute(text("ALTER TABLE user ADD COLUMN sessions_attended INTEGER DEFAULT 0"))
                print("Added sessions_attended column")
            except Exception as e:
                print(f"sessions_attended likely exists: {e}")

            # Check for session_cost
            try:
                conn.execute(text("ALTER TABLE user ADD COLUMN session_cost FLOAT DEFAULT 0.0"))
                print("Added session_cost column")
            except Exception as e:
                print(f"session_cost likely exists: {e}")
                
            conn.commit()

if __name__ == "__main__":
    migrate()
