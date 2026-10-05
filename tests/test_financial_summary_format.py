"""El chat debe mostrar el resumen financiero en espanol, una metrica por linea y en
soles, no el volcado de claves en ingles pegadas ('Expenses: $600.00Income...')."""

import json

from app.services import tools_registry as tr
from app.services.mcp_service import _trim_tool_result, normalize_number_spaces

DATA = {
    'month_name': 'October',
    'income_real': 0.0,
    'income_expected': 1010.0,
    'overdue_amount': 7585.0,
    'overdue_users_count': 24,
    'expenses': 600.0,
    'net_profit': -600.0,
}


def test_readable_is_spanish_one_metric_per_line():
    text = tr.format_financial_summary(DATA, 2026)
    lines = text.splitlines()
    assert lines[0] == 'Resumen financiero de octubre de 2026:'
    assert '- Ingresos cobrados: S/. 0.00' in lines
    assert '- Ingresos esperados: S/. 1,010.00' in lines
    assert '- Egresos: S/. 600.00' in lines
    assert '- Ganancia neta: -S/. 600.00' in lines
    assert '- Deuda vencida: S/. 7,585.00 (24 pacientes)' in lines
    assert 'October' not in text and 'Expenses' not in text and '$' not in text


def test_singular_patient_and_positive_net():
    text = tr.format_financial_summary({**DATA, 'overdue_users_count': 1, 'net_profit': 250.5}, 2026)
    assert '(1 paciente)' in text and '- Ganancia neta: S/. 250.50' in text


def test_unknown_month_name_is_kept_not_crashing():
    assert 'Resumen financiero de Foo de 2026:' in tr.format_financial_summary({**DATA, 'month_name': 'Foo'}, 2026)


def test_llm_context_carries_readable_and_no_english_dump():
    result = {
        'success': True,
        'data': {'success': True, 'data': DATA},
        'readable': tr.format_financial_summary(DATA, 2026),
    }
    out = json.loads(_trim_tool_result(result))
    assert 'readable' in out and 'Ingresos esperados' in out['readable']
    flat = json.dumps(out)
    assert 'income_expected' not in flat and 'month_name' not in flat
    assert 'TAL CUAL' in out['note']


def test_readable_survives_number_space_normalizer():
    text = tr.format_financial_summary(DATA, 2026)
    assert normalize_number_spaces(text) == text


def test_handler_adds_readable_with_requested_period(monkeypatch):
    class R:
        status_code = 200

        def get_json(self):
            return {'success': True, 'data': {**DATA, 'month_name': 'September'}}

    monkeypatch.setattr(tr, '_api_get', lambda *a, **k: R())
    out = tr.handle_financial_summary(month='2025-09')
    assert out['readable'].splitlines()[0] == 'Resumen financiero de septiembre de 2025:'


def test_synthesis_prompt_does_not_leak_a_copyable_example():
    """El ejemplo literal 'pacientes activos del centro' del prompt se colaba en
    respuestas ajenas ('Hay24 pacientes activos del centro' en un resumen financiero)."""
    from app.services.mcp_service import tool_result_context

    for result in ('{"count": 12}', '{"stats": {"total": 4}}'):
        assert 'pacientes activos del centro' not in tool_result_context('get_patient_stats', result)


def test_formatted_results_get_a_copy_only_prompt():
    from app.services.mcp_service import tool_result_context

    result = _trim_tool_result(
        {
            'success': True,
            'data': {'success': True, 'data': DATA},
            'readable': tr.format_financial_summary(DATA, 2026),
        }
    )
    ctx = tool_result_context('get_financial_summary', result)
    assert 'TAL CUAL' in ctx
    assert 'Hay N' not in ctx and 'conteo' not in ctx and 'pacientes activos' not in ctx
    assert 'NUNCA "Hay4"' in ctx  # sigue exigiendo espacio entre palabras y cifras
