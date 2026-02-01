import os
import sys

# 1. SETUP PATHS
# Ensure the application directory is in the Python path
# This is critical for finding 'app' and 'config'
basedir = os.path.dirname(os.path.abspath(__file__))
if basedir not in sys.path:
    sys.path.insert(0, basedir)

# 2. DEFINING APP FACTORY
def get_app():
    try:
        from app import create_app
        application = create_app()
        return application
    except Exception as e:
        # FATAL ERROR TRAP
        # If the app fails to load, create a fallback WSGI app that displays the error
        import traceback
        trace = traceback.format_exc()
        
        def error_app(environ, start_response):
            status = '500 Internal Server Error'
            response_headers = [('Content-type', 'text/plain; charset=utf-8')]
            start_response(status, response_headers)
            return [f"Critical Startup Error:\n\n{trace}".encode('utf-8')]
        
        return error_app

# 3. INITIALIZE APP
app = get_app()

# 4. PASSENGER WSGI ENTRY POINT
def application(environ, start_response):
    # ----------------------------------------------------------
    # CRITICAL FIX FOR CPANEL / SUBDIRECTORY DEPLOYMENT
    # ----------------------------------------------------------
    
    # 1. Try to get script_name from Passenger (standard way)
    script_name = environ.get('PASSENGER_BASE_URI', '')
    
    # 2. If missing, manually check if we are being accessed via /moscowle
    if not script_name:
        request_uri = environ.get('REQUEST_URI', '')
        if request_uri.startswith('/moscowle'):
            script_name = '/moscowle'

    # 3. Apply the fix
    if script_name:
        environ['SCRIPT_NAME'] = script_name
        
        # Ensure PATH_INFO is stripped of the prefix so Flask routes match correctly
        path_info = environ.get('PATH_INFO', '')
        if path_info.startswith(script_name):
            environ['PATH_INFO'] = path_info[len(script_name):]
            
    # 4. HTTPS Fix (ProxyFix fallback)
    if environ.get('HTTPS') == 'on':
        environ['wsgi.url_scheme'] = 'https'
            
    return app(environ, start_response)
