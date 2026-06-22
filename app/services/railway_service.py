import os
from datetime import datetime, timedelta

import requests

RAILWAY_API_ENDPOINT = 'https://backboard.railway.app/graphql/v2'

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


def get_railway_metrics():
    token = os.getenv('RAILWAY_API_TOKEN')
    project_token = os.getenv('RAILWAY_PROJECT_TOKEN')
    environment_id = os.getenv('RAILWAY_ENVIRONMENT_ID')
    service_id = os.getenv('RAILWAY_SERVICE_ID')

    if not token and not project_token:
        return {'success': False, 'error': 'RAILWAY_API_TOKEN or RAILWAY_PROJECT_TOKEN not configured'}

    if not environment_id:
        return {'success': False, 'error': 'RAILWAY_ENVIRONMENT_ID not configured'}

    if project_token:
        headers = {'Project-Access-Token': project_token, 'Content-Type': 'application/json'}
    else:
        headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}

    start_date = (datetime.utcnow() - timedelta(hours=1)).strftime('%Y-%m-%dT%H:%M:%SZ')
    end_date = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')

    variables = {
        'environmentId': environment_id,
        'startDate': start_date,
        'endDate': end_date,
        'measurements': ['CPU_USAGE', 'CPU_LIMIT', 'MEMORY_USAGE_GB', 'MEMORY_LIMIT_GB', 'NETWORK_RX_BYTES', 'NETWORK_TX_BYTES', 'REQUEST_COUNT', 'REQUEST_ERROR_COUNT', 'RESPONSE_TIME_MS'],
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
        return {'success': False, 'error': f'Railway API request failed: {str(e)}'}

    if response.status_code != 200:
        return {'success': False, 'error': f'Railway API returned {response.status_code}'}

    data = response.json()
    if 'errors' in data:
        return {'success': False, 'error': data['errors'][0]['message']}

    metrics_list = data.get('data', {}).get('metrics', [])

    raw = {}
    for metric in metrics_list:
        measurement = metric['measurement']
        values = metric.get('values', [])
        if values:
            avg = sum(v['value'] for v in values) / len(values)
            raw[measurement] = round(avg, 4)
        else:
            raw[measurement] = 0

    cpu_usage = raw.get('CPU_USAGE', 0)
    cpu_limit = raw.get('CPU_LIMIT', 1) or 1
    memory_usage = raw.get('MEMORY_USAGE_GB', 0)
    memory_limit = raw.get('MEMORY_LIMIT_GB', 1) or 1

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
            'environment_id': environment_id,
            'service_id': service_id or 'all',
        },
    }


def get_railway_metrics_history(from_dt=None, to_dt=None, bucket='15m'):
    token = os.getenv('RAILWAY_API_TOKEN')
    project_token = os.getenv('RAILWAY_PROJECT_TOKEN')
    environment_id = os.getenv('RAILWAY_ENVIRONMENT_ID')
    service_id = os.getenv('RAILWAY_SERVICE_ID')

    if not token and not project_token:
        return {'success': False, 'error': 'RAILWAY_API_TOKEN or RAILWAY_PROJECT_TOKEN not configured'}
    if not environment_id:
        return {'success': False, 'error': 'RAILWAY_ENVIRONMENT_ID not configured'}

    if project_token:
        headers = {'Project-Access-Token': project_token, 'Content-Type': 'application/json'}
    else:
        headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}

    try:
        if from_dt:
            start_date = datetime.fromisoformat(from_dt).strftime('%Y-%m-%dT%H:%M:%SZ')
        else:
            start_date = (datetime.utcnow() - timedelta(hours=24)).strftime('%Y-%m-%dT%H:%M:%SZ')
    except ValueError:
        start_date = (datetime.utcnow() - timedelta(hours=24)).strftime('%Y-%m-%dT%H:%M:%SZ')

    try:
        if to_dt:
            end_date = datetime.fromisoformat(to_dt).strftime('%Y-%m-%dT%H:%M:%SZ')
        else:
            end_date = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')
    except ValueError:
        end_date = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')

    variables = {
        'environmentId': environment_id,
        'startDate': start_date,
        'endDate': end_date,
        'measurements': ['CPU_USAGE', 'CPU_LIMIT', 'MEMORY_USAGE_GB', 'MEMORY_LIMIT_GB', 'NETWORK_RX_BYTES', 'NETWORK_TX_BYTES', 'REQUEST_COUNT', 'REQUEST_ERROR_COUNT', 'RESPONSE_TIME_MS'],
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
        return {'success': False, 'error': f'Railway API request failed: {str(e)}'}

    if response.status_code != 200:
        return {'success': False, 'error': f'Railway API returned {response.status_code}'}

    data = response.json()
    if 'errors' in data:
        return {'success': False, 'error': data['errors'][0]['message']}

    metrics_list = data.get('data', {}).get('metrics', [])

    series = {}
    for metric in metrics_list:
        measurement = metric['measurement']
        raw_values = []
        for v in metric.get('values', []):
            raw_values.append({'ts': v['ts'], 'value': v['value']})
        series[measurement] = raw_values

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
