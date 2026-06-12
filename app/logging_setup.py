import logging
import os
from logging.handlers import RotatingFileHandler

from flask import Flask
from pythonjsonlogger import jsonlogger


def setup_logging(app: Flask) -> None:
    log_dir = os.path.dirname(app.config['LOG_FILE'])
    os.makedirs(log_dir, exist_ok=True)

    app.logger.handlers.clear()

    file_handler = RotatingFileHandler(
        app.config['LOG_FILE'], maxBytes=app.config['LOG_MAX_SIZE'], backupCount=app.config['LOG_BACKUP_COUNT']
    )

    formatter = jsonlogger.JsonFormatter(
        '%(timestamp)s %(level)s %(name)s %(message)s %(exc_info)s %(request_id)s %(path)s %(method)s %(status_code)s %(duration_ms)s',
        timestamp=True,
    )
    file_handler.setFormatter(formatter)

    if app.debug:
        console_handler = logging.StreamHandler()
        console_formatter = logging.Formatter('[%(asctime)s] %(levelname)s [%(name)s]: %(message)s')
        console_handler.setFormatter(console_formatter)
        app.logger.addHandler(console_handler)

    from app.services.log_service import log_capture_handler

    capture_formatter = logging.Formatter('[%(asctime)s] %(levelname)s [%(name)s]: %(message)s')
    log_capture_handler.setFormatter(capture_formatter)
    app.logger.addHandler(log_capture_handler)

    app.logger.addHandler(file_handler)
    app.logger.setLevel(getattr(logging, app.config['LOG_LEVEL']))

    app.logger.info(
        'Application initialized',
        extra={
            'env': app.config['ENV'],
            'debug': app.debug,
            'timestamp': __import__('datetime').datetime.utcnow().isoformat(),
        },
    )
