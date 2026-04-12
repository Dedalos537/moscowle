"""
Migration: Crear tabla YapeTransaction para ingesta de Yape/Plin.

Ejecutar con:
    python3 -c "from app import create_app; app = create_app(); exec(open('migrations/add_yape_transaction.py').read())"
"""

from app import create_app
from app.extensions import db
from sqlalchemy import text

def migrate():
    app = create_app()
    with app.app_context():
        # Crear tabla si no existe
        db.create_all()
        
        # Verificar que operation_number tiene INDEX único
        try:
            db.session.execute(text(
                'CREATE UNIQUE INDEX IF NOT EXISTS idx_yape_operation_number ON yape_transaction(operation_number)'
            ))
            db.session.commit()
            print("✅ Índice único en operation_number creado")
        except Exception as e:
            print(f"⚠️ Índice ya existe o error: {e}")
        
        print("✅ YapeTransaction table setup completed")

if __name__ == '__main__':
    migrate()
