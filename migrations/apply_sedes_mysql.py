import os
import sqlalchemy
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get Database URL
DATABASE_URL = os.getenv('SQLALCHEMY_DATABASE_URI')
print(f"Connecting to database: {DATABASE_URL}")

def run_migration():
    if not DATABASE_URL or 'sqlite' in DATABASE_URL:
        print("Not using MySQL database or URL not found.")
        return

    try:
        engine = create_engine(DATABASE_URL)
        with engine.connect() as conn:
            print("Connected successfully.")
            
            # 1. Create Sede table
            print("Checking/Creating 'sede' table...")
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS sede (
                    id INTEGER AUTO_INCREMENT PRIMARY KEY,
                    name VARCHAR(100) NOT NULL UNIQUE,
                    address VARCHAR(255),
                    active BOOLEAN DEFAULT 1,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """))
            
            # Insert default sedes
            result = conn.execute(text("SELECT count(*) FROM sede"))
            count = result.scalar()
            if count == 0:
                print("Inserting default sedes: Talara, Piura")
                conn.execute(text("INSERT INTO sede (name, active) VALUES ('Talara', 1)"))
                conn.execute(text("INSERT INTO sede (name, active) VALUES ('Piura', 1)"))
            
            # 2. Add sede_id to User table
            print("Checking user table for sede_id...")
            try:
                # Check column existence (MySQL specific syntax)
                conn.execute(text("SELECT sede_id FROM user LIMIT 1"))
                print("Column 'sede_id' already exists.")
            except Exception:
                print("Column 'sede_id' missing. Adding...")
                conn.execute(text("ALTER TABLE user ADD COLUMN sede_id INTEGER"))
                conn.execute(text("ALTER TABLE user ADD CONSTRAINT fk_user_sede FOREIGN KEY (sede_id) REFERENCES sede(id)"))

            # 3. Create therapist_sede table
            print("Checking/Creating 'therapist_sede' table...")
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS therapist_sede (
                    therapist_id INTEGER NOT NULL,
                    sede_id INTEGER NOT NULL,
                    PRIMARY KEY (therapist_id, sede_id),
                    FOREIGN KEY (therapist_id) REFERENCES user (id),
                    FOREIGN KEY (sede_id) REFERENCES sede (id)
                )
            """))
            
            conn.commit()
            print("Migration completed successfully.")
            
    except Exception as e:
        print(f"Migration failed: {e}")

if __name__ == "__main__":
    run_migration()
