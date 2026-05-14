from app import create_app, db
from sqlalchemy import text

app = create_app()

with app.app_context():
    try:
        # SQLite o MySQL: add column if not exists
        db.session.execute(text("ALTER TABLE user ADD COLUMN document_number VARCHAR(20) NULL;"))
        db.session.commit()
        print("Migración exitosa: Columna 'document_number' añadida a 'user'.")
    except Exception as e:
        print(f"Error o la columna ya existe: {e}")
        db.session.rollback()
