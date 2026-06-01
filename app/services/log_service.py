import logging
from collections import deque
from datetime import datetime
import traceback

class LogCaptureHandler(logging.Handler):
    def __init__(self, capacity=500):
        super().__init__()
        self.capacity = capacity
        self.buffer = deque(maxlen=capacity)

    def emit(self, record):
        try:
            entry = {
                'timestamp': datetime.utcfromtimestamp(record.created).isoformat(),
                'level': record.levelname,
                'logger': record.name,
                'message': self.format(record),
                'short_message': record.getMessage(),
            }
            if record.exc_info and record.exc_info[0]:
                entry['exc_info'] = traceback.format_exception(*record.exc_info)
            self.buffer.append(entry)
        except Exception:
            pass

    def get_logs(self, level=None, limit=100, search=None):
        result = list(self.buffer)
        result.reverse()
        if level:
            result = [e for e in result if e['level'] == level.upper()]
        if search:
            search_lower = search.lower()
            result = [e for e in result if search_lower in e['short_message'].lower()]
        return result[:limit]


log_capture_handler = LogCaptureHandler(capacity=500)
