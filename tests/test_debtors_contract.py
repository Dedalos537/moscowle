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


def test_tool_counts_only_real_debtors(monkeypatch):
    """El reporte lista a todos los pacientes activos con su estado; la tool solo debe contar a quienes deben."""
    from app.services import tools_registry

    report = {
        'success': True,
        'data': {
            'summary': {'total_adeudado': 350.0, 'total_deudores': 2, 'vencidos': 1, 'proximo_a_vencer': 1},
            'por_sede': {
                '1': {
                    'sede_name': 'Cayma',
                    'deudores': [
                        {'id': 1, 'paciente': 'Ana', 'monto': 200.0, 'estado': 'vencido', 'dias_adeudo': 12},
                        {'id': 2, 'paciente': 'Beto', 'monto': 150.0, 'estado': 'proximo', 'dias_adeudo': 0},
                        {'id': 3, 'paciente': 'Caro', 'monto': 150.0, 'estado': 'al_dia', 'dias_adeudo': 0},
                        {'id': 4, 'paciente': 'Dani', 'monto': 0.0, 'estado': 'sin_plan', 'dias_adeudo': 0},
                    ],
                },
                'sin_sede': {'sede_name': 'Sin Sede', 'deudores': [{'id': 5, 'monto': 0.0, 'estado': 'sin_plan'}]},
            },
        },
    }

    class _Resp:
        def get_json(self):
            return report

    monkeypatch.setattr(tools_registry, '_api_get', lambda *a, **k: _Resp())
    out = tools_registry.TOOL_REGISTRY['get_debtors']['handler']()
    assert out['count'] == 2 and out['total_adeudado'] == 350.0
    assert len(out['por_sede']) == 1  # la sede sin deudores reales no aparece
    names = [d['paciente'] for d in out['por_sede'][0]['detalle']]
    assert names == ['Ana', 'Beto'] and out['por_sede'][0]['detalle'][1]['estado'] == 'por vencer'
