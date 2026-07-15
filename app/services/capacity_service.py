"""Capacity Service — Utilization Law calculations.

U = lambda * S / C

Where:
  U = Utilization (0-1)
  lambda = Arrival rate (requests/second)
  S = Service time (seconds/request)
  C = Capacity (number of servers/workers)
"""

import logging
import time
from collections import deque
from threading import Lock

logger = logging.getLogger(__name__)


class CapacityService:
    """Calculates system utilization using the Utilization Law."""

    def __init__(self, window_seconds=300):
        self.window = window_seconds
        self._requests = deque()
        self._lock = Lock()
        self._total_requests = 0
        self._total_service_time = 0.0

    def record_request(self, service_time_seconds):
        """Record a completed request with its service time."""
        now = time.time()
        with self._lock:
            self._requests.append((now, service_time_seconds))
            self._total_requests += 1
            self._total_service_time += service_time_seconds
            # Prune old entries
            cutoff = now - self.window
            while self._requests and self._requests[0][0] < cutoff:
                self._requests.popleft()

    def get_arrival_rate(self):
        """Calculate arrival rate (lambda) in requests/second over the window."""
        with self._lock:
            if not self._requests:
                return 0.0
            now = time.time()
            cutoff = now - self.window
            recent = [(t, s) for t, s in self._requests if t >= cutoff]
            if not recent:
                return 0.0
            duration = now - recent[0][0]
            if duration <= 0:
                return 0.0
            return len(recent) / duration

    def get_avg_service_time(self):
        """Calculate average service time (S) in seconds."""
        with self._lock:
            if not self._requests:
                return 0.0
            total = sum(s for _, s in self._requests)
            return total / len(self._requests)

    def get_utilization(self, num_workers=1):
        """Calculate utilization: U = lambda * S / C.

        Args:
            num_workers: Number of concurrent workers/servers (C).
        """
        lam = self.get_arrival_rate()
        s = self.get_avg_service_time()
        c = max(num_workers, 1)
        u = (lam * s) / c
        return min(u, 1.0)  # Cap at 1.0

    def get_stats(self, num_workers=1):
        """Get full capacity statistics."""
        return {
            'arrival_rate_rps': round(self.get_arrival_rate(), 2),
            'avg_service_time_ms': round(self.get_avg_service_time() * 1000, 1),
            'utilization': round(self.get_utilization(num_workers), 3),
            'utilization_percent': round(self.get_utilization(num_workers) * 100, 1),
            'window_seconds': self.window,
            'sample_size': len(self._requests),
            'total_requests': self._total_requests,
        }

    def get_recommendation(self, num_workers=1):
        """Get capacity recommendation based on utilization."""
        u = self.get_utilization(num_workers)

        if u >= 0.9:
            return {
                'level': 'CRITICAL',
                'message': f'Utilizacion al {u * 100:.0f}%. Escalar horizontalmente recomendado.',
                'action': 'scale_out',
            }
        elif u >= 0.7:
            return {
                'level': 'WARNING',
                'message': f'Utilizacion al {u * 100:.0f}%. Monitorear de cerca.',
                'action': 'monitor',
            }
        else:
            return {
                'level': 'OK',
                'message': f'Utilizacion al {u * 100:.0f}%. Capacidad suficiente.',
                'action': 'none',
            }


# Singleton
capacity_service = CapacityService()
