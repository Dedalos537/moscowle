from app import create_app
import os
import sys

# Ensure app is in python path
sys.path.insert(0, os.path.dirname(__file__))

app = create_app()

def application(environ, start_response):
    # ----------------------------------------------------------
    # CRITICAL FIX FOR CPANEL / SUBDIRECTORY DEPLOYMENT
    # ----------------------------------------------------------
    
    # 1. Try to get script_name from Passenger (standard way)
    script_name = environ.get('PASSENGER_BASE_URI', '')
    
    # 2. If missing, manually check if we are being accessed via /moscowle
    # This prevents CSS/JS 404s when variables aren't passed correctly
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
    # If the server says we are HTTPS but WSGI doesn't know, force it.
    if environ.get('HTTPS') == 'on':
        environ['wsgi.url_scheme'] = 'https'
            
    return app(environ, start_response)
