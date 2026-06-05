import os
import sys

if __name__ == '__main__':
    port = os.environ.get('PORT', '8080')
    os.execvpe(
        'gunicorn',
        [
            'gunicorn',
            '--worker-class',
            'eventlet',
            '--workers',
            '1',
            '--bind',
            f'0.0.0.0:{port}',
            '--timeout',
            '120',
            '--access-logfile',
            '-',
            '--error-logfile',
            '-',
            'server:application',
        ],
        os.environ,
    )
