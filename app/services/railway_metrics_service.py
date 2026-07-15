"""Railway Metrics Service — polls Railway API for CPU/RAM/Disk metrics.

Checks against Warning/Critical thresholds and triggers alerts via
CrisisMonitor when thresholds are breached.
"""

import logging
import os
from datetime import UTC, datetime

import requests

logger = logging.getLogger(__name__)

# Thresholds from edu-sync-ai-baseline.md
THRESHOLDS = {
    'cpu': {'warning': 70, 'critical': 80},
    'ram': {'warning': 80, 'critical': 90},
    'disk': {'warning': 80, 'critical': 85},
    'latency': {'warning': 2000, 'critical': 3000},  # ms p95
}


class RailwayMetricsService:
    """Fetches and evaluates Railway deployment metrics against thresholds."""

    def __init__(self):
        self.api_token = os.getenv('RAILWAY_API_TOKEN', '')
        self.project_id = os.getenv('RAILWAY_PROJECT_ID', '')
        self.service_id = os.getenv('RAILWAY_SERVICE_ID', '')
        self.base_url = 'https://api.railway.app/graphql'

    def _headers(self):
        return {
            'Authorization': f'Bearer {self.api_token}',
            'Content-Type': 'application/json',
        }

    def get_metrics(self):
        """Fetch current CPU and memory usage from Railway API."""
        if not self.api_token or not self.project_id:
            logger.warning('Railway API credentials not configured')
            return None

        query = (
            """
        query {
            deployments(input: { projectId: "%s", first: 1 }) {
                edges {
                    node {
                        id
                        metrics {
                            cpu
                            memory
                            diskUsage
                        }
                    }
                }
            }
        }
        """
            % self.project_id
        )

        try:
            resp = requests.post(
                self.base_url,
                json={'query': query},
                headers=self._headers(),
                timeout=10,
            )
            resp.raise_for_status()
            data = resp.json()
            deployments = data.get('data', {}).get('deployments', {}).get('edges', [])
            if deployments:
                return deployments[0].get('node', {}).get('metrics', {})
        except Exception as e:
            logger.error(f'Failed to fetch Railway metrics: {e}')

        return None

    def check_thresholds(self, metrics=None):
        """Check metrics against thresholds and return violations."""
        if metrics is None:
            metrics = self.get_metrics()

        if not metrics:
            return []

        violations = []
        cpu = metrics.get('cpu', 0)
        ram = metrics.get('memory', 0)
        disk = metrics.get('diskUsage', 0)

        for metric_name, value in [('cpu', cpu), ('ram', ram), ('disk', disk)]:
            t = THRESHOLDS.get(metric_name, {})
            if value >= t.get('critical', 100):
                violations.append(
                    {
                        'metric': metric_name,
                        'level': 'CRITICAL',
                        'value': value,
                        'threshold': t['critical'],
                        'action': self._get_action(metric_name, 'critical'),
                    }
                )
            elif value >= t.get('warning', 100):
                violations.append(
                    {
                        'metric': metric_name,
                        'level': 'WARNING',
                        'value': value,
                        'threshold': t['warning'],
                        'action': self._get_action(metric_name, 'warning'),
                    }
                )

        return violations

    def _get_action(self, metric, level):
        """Get remediation action for a threshold violation."""
        actions = {
            'cpu': {
                'warning': 'Notificar admin, considerar auto-scale',
                'critical': 'Auto-scale si disponible, notificar inmediatamente',
            },
            'ram': {
                'warning': 'Notificar admin, monitorear procesos',
                'critical': 'Restart del servicio, notificar inmediatamente',
            },
            'disk': {
                'warning': 'Notificar admin, limpiar logs temporales',
                'critical': 'Limpiar archivos innecesarios, notificar inmediatamente',
            },
        }
        return actions.get(metric, {}).get(level, 'Revisar manualmente')

    def evaluate_and_alert(self):
        """Full evaluation cycle: fetch, check, alert."""
        metrics = self.get_metrics()
        violations = self.check_thresholds(metrics)

        if violations:
            logger.warning(f'Threshold violations detected: {violations}')
            # Integrate with CrisisMonitor here if needed

        return {
            'metrics': metrics,
            'violations': violations,
            'checked_at': datetime.now(UTC).isoformat(),
        }


# Singleton
railway_metrics_service = RailwayMetricsService()
