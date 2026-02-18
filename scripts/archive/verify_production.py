import os
import sys
from sqlalchemy import create_engine, text

# Simula la carga de entorno (ajusta si es necesario)
# En cPanel, estas variables vienen del entorno de Passenger
print("---- INICIO DIAGNOSTICO ----")
print(f"Current Working Directory: {os.getcwd()}")

uri = os.getenv('SQLALCHEMY_DATABASE_URI')
print(f"URI detectada: {uri}")

if not uri:
    print("ALERTA: SQLALCHEMY_DATABASE_URI no está definida. La app usaría SQLite por defecto.")
    print("Esto explica por qué no ves tus credenciales (está usando una DB vacía o local).")
else:
    print("Intentando conectar a MySQL...")
    try:
        engine = create_engine(uri)
        with engine.connect() as conn:
            result = conn.execute(text("SELECT count(*) FROM user"))
            count = result.scalar()
            print(f"¡CONEXIÓN EXITOSA! Usuarios encontrados en la tabla 'user': {count}")
            
            if count == 0:
                print("La conexión funciona, pero NO HAY USUARIOS. Debes importar el SQL.")
            else:
                print("La conexión funciona y TIENE DATOS. Si no entras, revisa la contraseña.")
    except Exception as e:
        print(f"ERROR DE CONEXIÓN: {e}")

print("---- FIN DIAGNOSTICO ----")
