"""get_financial_summary: el periodo que manda la IA ('YYYY-MM', '9', 'setiembre')
debe llegar al endpoint como month=<1-12>&year=<YYYY>. Antes 'YYYY-MM' se
descartaba en silencio y preguntar por setiembre devolvia el mes actual."""

import pytest

from app.services import tools_registry as tr


class _Resp:
    status_code = 200

    def get_json(self):
        return {'success': True, 'data': {'month_name': 'September'}}


@pytest.fixture
def seen_url(monkeypatch):
    seen = {}

    def fake_get(endpoint, user_id=None, role=None):
        seen['url'] = endpoint
        return _Resp()

    monkeypatch.setattr(tr, '_api_get', fake_get)
    return seen


@pytest.mark.parametrize(
    'args,expected',
    [
        ({'month': '2026-09'}, 'month=9&year=2026'),
        ({'month': '2025-12'}, 'month=12&year=2025'),
        ({'month': '9'}, 'month=9'),
        ({'month': 9, 'year': 2025}, 'month=9&year=2025'),
        ({'month': 'setiembre'}, 'month=9'),
        ({'month': 'Septiembre'}, 'month=9'),
        ({}, None),
    ],
)
def test_period_reaches_endpoint_in_its_format(seen_url, args, expected):
    out = tr.handle_financial_summary(**args)
    assert out.get('success'), out
    url = seen_url['url']
    if expected is None:
        assert '?' not in url
    else:
        assert url.endswith('?' + expected), url


@pytest.mark.parametrize('bad', ['2026-13', '0', '13', 'basura', '2026-00'])
def test_invalid_period_is_not_sent(seen_url, bad):
    tr.handle_financial_summary(month=bad)
    assert 'month=' not in seen_url['url']
