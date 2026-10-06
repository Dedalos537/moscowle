from app.services import webauthn_service as svc


def _ctx(app, origin):
    headers = {'Origin': origin} if origin else {}
    return app.test_request_context('/api/webauthn/login/options', method='POST', headers=headers)


def test_cpanel_frontend_uses_parent_domain(app):
    with _ctx(app, 'https://moscowle.centrojuanpabloii.com'):
        assert svc.rp_id() == 'centrojuanpabloii.com'
        assert 'https://moscowle.centrojuanpabloii.com' in svc.origins()


def test_api_domain_keeps_configured_rp(app):
    with _ctx(app, 'https://api-centrojuanpabloii.online'):
        assert svc.rp_id() == 'api-centrojuanpabloii.online'


def test_unknown_or_insecure_origin_falls_back(app):
    for origin in (
        'https://evil.example.com',
        'http://moscowle.centrojuanpabloii.com',
        'https://centrojuanpabloii.com.evil.io',
        None,
    ):
        with _ctx(app, origin):
            assert svc.rp_id() == 'api-centrojuanpabloii.online'
            assert all('evil' not in o for o in svc.origins())
