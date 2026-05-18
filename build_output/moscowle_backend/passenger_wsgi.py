import os
import sys

basedir = os.path.dirname(os.path.abspath(__file__))
if basedir not in sys.path:
    sys.path.insert(0, basedir)

def get_app():
    try:
        from app import create_app
        application = create_app()
        return application
    except Exception as e:
        import traceback
        trace = traceback.format_exc()
        def error_app(environ, start_response):
            status = '200 OK'
            output = f"Critical Startup Error:\n\n{trace}".encode('utf-8')
            response_headers = [
                ('Content-type', 'text/plain; charset=utf-8'),
                ('Content-Length', str(len(output)))
            ]
            start_response(status, response_headers)
            return [output]
        return error_app

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

def application(environ, start_response):
    script_name = environ.get('SCRIPT_NAME', '')
    if not script_name:
        request_uri = environ.get('REQUEST_URI', '')
        if request_uri and request_uri.startswith('/moscowle'):
            script_name = '/moscowle'
    if script_name:
        environ['SCRIPT_NAME'] = script_name
        path_info = environ.get('PATH_INFO', '')
        if path_info.startswith(script_name):
            environ['PATH_INFO'] = path_info[len(script_name):]
    if environ.get('HTTPS') == 'on' or environ.get('HTTP_X_FORWARDED_PROTO') == 'https':
        environ['wsgi.url_scheme'] = 'https'
    return app(environ, start_response)
