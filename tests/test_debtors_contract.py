"""Contrato get_debtors: el mes que manda la tool/IA debe llegar al endpoint
en el formato que entiende build_debt_report (1-12 | current | all) y el
resumen con el total adeudado no debe perderse al recortar el resultado."""

import json
from datetime import datetime

import pytest

from app.services.mcp_service import _trim_tool_result
from app.services.tools_registry import normalize_debt_month


@pytest.mark.parametrize(
    'raw,expected',
    [
        (None, None),
        ('', None),
        ('all', None),
        ('current', 'current'),
        ('10', '10'),
        (10, '10'),
        ('octubre', '10'),
        (f'{datetime.utcnow().year}-{datetime.utcnow().month:02d}', 'current'),
        ('2026-03', '3'),
        ('basura', None),
    ],
)
def test_normalize_debt_month(raw, expected):
    assert normalize_debt_month(raw) == expected


def test_trim_keeps_summary_total():
    result = {
        'success': True,
        'count': 2,
        'debtors': {
            'data': {
                'summary': {'total_adeudado': 5678.9, 'total_deudores': 2},
                'por_sede': {'1': {'deudores': [{'nombre': 'A'}, {'nombre': 'B'}]}},
            }
        },
    }
    out = json.loads(_trim_tool_result(result))
    assert out['summary']['total_adeudado'] == 5678.9
    assert out['count'] == 2
