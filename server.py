import eventlet

eventlet.monkey_patch()

import logging
import sys
import traceback

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger('server')

try:
    from app import create_app

    application = create_app()
except Exception:
    logger.critical('Failed to create application:\n%s', traceback.format_exc())
    sys.exit(1)
