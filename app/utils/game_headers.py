"""Cabeceras propias para los juegos de /static/games.

La política general del sitio prohíbe que otra página lo incruste (frame-ancestors 'self') y no permite WebAssembly
ni imágenes blob:. Los juegos sí lo necesitan: se juegan dentro del reproductor de la plataforma, que en cPanel vive
en otro dominio, JClic dibuja con imágenes blob: y Ruffle (Flash) compila WebAssembly.

Va como middleware WSGI para quedar por encima de Talisman y de los after_request: es la última palabra sobre las
cabeceras de esas rutas y no toca ninguna otra.
"""

GAMES_PREFIX = '/static/games/'

PLAYER_ORIGINS = (
    "'self'",
    'https://moscowle.centrojuanpabloii.com',
    'https://api-centrojuanpabloii.online',
    'http://localhost:4200',
)

GAME_CSP = '; '.join(
    [
        "default-src 'self'",
        "script-src 'self' 'unsafe-inline' 'wasm-unsafe-eval' blob: https://cdn.tailwindcss.com "
        'https://cdnjs.cloudflare.com https://cdn.jsdelivr.net',
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://cdnjs.cloudflare.com https://cdn.jsdelivr.net",
        "font-src 'self' data: https://fonts.gstatic.com https://cdnjs.cloudflare.com",
        "img-src 'self' data: blob:",
        "media-src 'self' data: blob:",
        "connect-src 'self' blob: data:",
        "worker-src 'self' blob:",
        'frame-ancestors ' + ' '.join(PLAYER_ORIGINS),
    ]
)

_DROP = {'content-security-policy', 'x-frame-options'}


class GameHeadersMiddleware:
    def __init__(self, app):
        self.app = app

    def __call__(self, environ, start_response):
        if not environ.get('PATH_INFO', '').startswith(GAMES_PREFIX):
            return self.app(environ, start_response)

        def patched(status, headers, exc_info=None):
            headers = [(k, v) for k, v in headers if k.lower() not in _DROP]
            headers.append(('Content-Security-Policy', GAME_CSP))
            return start_response(status, headers, exc_info)

        return self.app(environ, patched)
