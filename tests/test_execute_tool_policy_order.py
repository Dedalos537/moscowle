"""La politica de alcance debe vetar ANTES de ejecutar el handler: una escritura
denegada no puede haberse ejecutado ya (el mensaje de 'sin acceso' seria mentira)."""

from app.services import policy as policy_mod
from app.services import tools_registry as tr


class _DenyPolicy:
    def check(self, name, args, role=None, user_id=None):
        return False, args, 'No tienes acceso a ese paciente: no esta en tu alcance.'

    def filter_result(self, name, result, role=None, user_id=None):
        return result


def test_denied_write_never_runs_handler(monkeypatch):
    calls = []

    def handler(patient_id, **kw):
        calls.append(patient_id)
        return {'success': True}

    monkeypatch.setitem(
        tr.TOOL_REGISTRY,
        'zz_fake_write',
        {
            'name': 'zz_fake_write',
            'handler': handler,
            'category': 'write',
            'roles': None,
            'parameters': {
                'type': 'object',
                'properties': {'patient_id': {'type': 'integer'}},
                'required': ['patient_id'],
            },
        },
    )
    monkeypatch.setattr(policy_mod, 'get_policy', lambda: _DenyPolicy())

    out = tr.execute_tool('zz_fake_write', {'patient_id': 99}, user_id=1, role='terapista')

    assert 'error' in out and 'alcance' in out['error']
    assert calls == [], 'el handler de escritura se ejecuto pese a la denegacion'
