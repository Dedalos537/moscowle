import os
import sys
import time

MARK = '/home/centroju/moscowle/PASSENGER_RAN.txt'
with open(MARK, 'a') as f:
    f.write('ran at %s python=%s cwd=%s\n' % (time.time(), sys.executable, os.getcwd()))


def application(environ, start_response):
    start_response('200 OK', [('Content-Type', 'text/plain')])
    return [b'PASSENGER ALIVE']
