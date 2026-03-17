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
        import traceback
        trace = traceback.format_exc()
        
        def error_app(environ, start_response):
            # Use 200 OK so browsers don't hide the error
            status = '200 OK'
            output = f"Critical Startup Error:\n\n{trace}".encode('utf-8')
            response_headers = [
                ('Content-type', 'text/plain; charset=utf-8'),
                ('Content-Length', str(len(output)))
            ]
            start_response(status, response_headers)
            return [output]
        
        return error_app

# 3. INITIALIZE APP with Global Try-Catch
try:
    app = get_app()
except Exception as e:
    import traceback
    trace = traceback.format_exc()
    def app(environ, start_response):
        status = '200 OK'
        output = f"Global Initialization Error:\n\n{trace}".encode('utf-8')
        response_headers = [('Content-type', 'text/plain'), ('Content-Length', str(len(output)))]
        start_response(status, response_headers)
        return [output]

# 4. PASSENGER WSGI ENTRY POINT
def application(environ, start_response):
    # ----------------------------------------------------------
    # CRITICAL FIX FOR CPANEL / SUBDIRECTORY DEPLOYMENT
    # ----------------------------------------------------------
    
    script_name = environ.get('SCRIPT_NAME', '')
    
    # 1. Detect if we are in a subdirectory (e.g. /moscowle)
    # Check REQUEST_URI or SCRIPT_NAME provided by Passenger
    if not script_name:
        request_uri = environ.get('REQUEST_URI', '')
        # Hardcode detection for '/moscowle' if missing
        if request_uri and request_uri.startswith('/moscowle'):
            script_name = '/moscowle'
            
    # 2. Apply SCRIPT_NAME if detected
    if script_name:
        environ['SCRIPT_NAME'] = script_name
        
        # 3. Strip prefix from PATH_INFO (Flask needs clean path)
        path_info = environ.get('PATH_INFO', '')
        if path_info.startswith(script_name):
            environ['PATH_INFO'] = path_info[len(script_name):]
            
    # 4. HTTPS Fix (ProxyFix fallback)
    if environ.get('HTTPS') == 'on':
        environ['wsgi.url_scheme'] = 'https'
            
    return app(environ, start_response)
            
    # 4. HTTPS Fix (ProxyFix fallback)
    if environ.get('HTTPS') == 'on':
        environ['wsgi.url_scheme'] = 'https'
            
    return app(environ, start_response)
