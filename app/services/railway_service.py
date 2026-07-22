import os
from datetime import UTC, datetime, timedelta, timezone

import requests

RAILWAY_API_ENDPOINT = 'https://backboard.railway.app/graphql/v2'

# Lima = UTC-5, no DST
LIMA_TZ = timezone(timedelta(hours=-5))

METRICS_QUERY = """
query metrics(
  $environmentId: String!
  $serviceId: String
  $startDate: DateTime!
  $endDate: DateTime
  $measurements: [MetricMeasurement!]!
) {
  metrics(
    environmentId: $environmentId
    serviceId: $serviceId
    startDate: $startDate
    endDate: $endDate
    measurements: $measurements
  ) {
    measurement
    tags { deploymentId serviceId region }
    values { ts value }
  }
}
"""

ALL_MEASUREMENTS = [
    'CPU_USAGE',
    'CPU_LIMIT',
    'MEMORY_USAGE_GB',
    'MEMORY_LIMIT_GB',
    'NETWORK_RX_GB',
    'NETWORK_TX_GB',
    'DISK_USAGE_GB',
]


def _parse_datetime_to_utc(dt_str):
    """Parse datetime string and convert to UTC. Lima datetime-naive inputs are assumed to be Lima time."""
    if not dt_str:
        return None
    try:
        dt = datetime.fromisoformat(dt_str)
        if dt.tzinfo is None:
            # Naive datetime from Angular datetime-local — treat as Lima time
            dt = dt.replace(tzinfo=LIMA_TZ)
        return dt.astimezone(UTC)
    except (ValueError, TypeError):
        return None


def _get_headers():
    token = os.getenv('RAILWAY_API_TOKEN')
    project_token = os.getenv('RAILWAY_PROJECT_TOKEN')
    if project_token:
        return {'Project-Access-Token': project_token, 'Content-Type': 'application/json'}
    elif token:
        return {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}
    return None


def _fetch_metrics(environment_id, service_id, start_date, end_date, measurements=None):
    """Core GraphQL call to Railway metrics API."""
    headers = _get_headers()
    if not headers:
        return None, 'RAILWAY_API_TOKEN or RAILWAY_PROJECT_TOKEN not configured'

    variables = {
        'environmentId': environment_id,
        'startDate': start_date,
        'endDate': end_date,
        'measurements': measurements or ALL_MEASUREMENTS,
    }
    if service_id:
        variables['serviceId'] = service_id

    try:
        response = requests.post(
            RAILWAY_API_ENDPOINT,
            json={'query': METRICS_QUERY, 'variables': variables},
            headers=headers,
            timeout=30,
        )
    except requests.exceptions.RequestException as e:
        return None, f'Railway API request failed: {str(e)}'

    if response.status_code != 200:
        return None, f'Railway API returned {response.status_code}: {response.text[:500]}'

    data = response.json()
    if 'errors' in data:
        return None, data['errors'][0]['message']

    return data.get('data', {}).get('metrics', []), None


def _avg_values(values):
    """Average a list of {ts, value} points."""
    if not values:
        return 0
    return sum(v['value'] for v in values) / len(values)


def get_railway_metrics():
    environment_id = os.getenv('RAILWAY_ENVIRONMENT_ID')
    service_id = os.getenv('RAILWAY_SERVICE_ID')

    if not environment_id:
        return {'success': False, 'error': 'RAILWAY_ENVIRONMENT_ID not configured'}

    start_date = (datetime.now(UTC) - timedelta(hours=1)).strftime('%Y-%m-%dT%H:%M:%SZ')
    end_date = datetime.now(UTC).strftime('%Y-%m-%dT%H:%M:%SZ')

    metrics_list, error = _fetch_metrics(environment_id, service_id, start_date, end_date)
    if error:
        return {'success': False, 'error': error}

    raw = {}
    for metric in metrics_list:
        measurement = metric['measurement']
        raw[measurement] = round(_avg_values(metric.get('values', [])), 4)

    cpu_usage = raw.get('CPU_USAGE', 0)
    cpu_limit = raw.get('CPU_LIMIT', 1) or 1
    memory_usage = raw.get('MEMORY_USAGE_GB', 0)
    memory_limit = raw.get('MEMORY_LIMIT_GB', 1) or 1
    disk_usage = raw.get('DISK_USAGE_GB', 0)

    return {
        'success': True,
        'data': {
            'cpu': {
                'usage': cpu_usage,
                'limit': cpu_limit,
                'percentage': round((cpu_usage / cpu_limit) * 100, 1),
            },
            'memory': {
                'usage_gb': memory_usage,
                'limit_gb': memory_limit,
                'percentage': round((memory_usage / memory_limit) * 100, 1),
            },
            'disk': {
                'usage_gb': disk_usage,
            },
            'environment_id': environment_id,
            'service_id': service_id or 'all',
        },
    }


def get_railway_metrics_history(from_dt=None, to_dt=None, bucket='15m'):
    environment_id = os.getenv('RAILWAY_ENVIRONMENT_ID')
    service_id = os.getenv('RAILWAY_SERVICE_ID')

    if not environment_id:
        return {'success': False, 'error': 'RAILWAY_ENVIRONMENT_ID not configured'}

    start_utc = _parse_datetime_to_utc(from_dt)
    end_utc = _parse_datetime_to_utc(to_dt)

    if not start_utc:
        start_utc = datetime.now(UTC) - timedelta(hours=24)
    if not end_utc:
        end_utc = datetime.now(UTC)

    start_date = start_utc.strftime('%Y-%m-%dT%H:%M:%SZ')
    end_date = end_utc.strftime('%Y-%m-%dT%H:%M:%SZ')

    metrics_list, error = _fetch_metrics(environment_id, service_id, start_date, end_date)
    if error:
        return {'success': False, 'error': error}

    series = {}
    for metric in metrics_list:
        measurement = metric['measurement']
        series[measurement] = [{'ts': v['ts'], 'value': v['value']} for v in metric.get('values', [])]

    return {
        'success': True,
        'data': {
            'environment_id': environment_id,
            'service_id': service_id or 'all',
            'start': start_date,
            'end': end_date,
            'series': series,
        },
    }
