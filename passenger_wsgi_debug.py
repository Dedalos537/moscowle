import sys, os

# ===================================================================
# MODO DEBUG DE EMERGENCIA - MOSCOWLE
# Úsame si tu app da "Internal Server Error" o pantalla roja
# ===================================================================

# 1. Agregamos el directorio actual al path
sys.path.insert(0, os.path.dirname(__file__))

# 2. Intentamos importar la app con captura de errores
try:
    from app import create_app
    application = create_app()
    
except Exception as e:
    import traceback
    
    # Si falla, creamos una mini-app que muestra el error en el navegador
    def application(environ, start_response):
        status = '500 Internal Server Error'
        error_msg = f"CRITICAL STARTUP ERROR:\n{str(e)}\n\n{traceback.format_exc()}"
        
        response_headers = [('Content-type', 'text/plain; charset=utf-8')]
        start_response(status, response_headers)
        return [error_msg.encode('utf-8')]
