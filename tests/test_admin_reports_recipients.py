"""Los resúmenes administrativos (BSC diario, semanal, mensual, anual) solo van a administradores."""

import uuid
from unittest.mock import patch

from app.extensions import db
from app.models import User
from app.services import automated_reports_service as reports
from app.services import daily_digest_service as digest


def _user(role):
    tag = uuid.uuid4().hex[:8]
    u = User(username=f'{role[:3]}{tag}', email=f'{tag}@rep.test', password='x', role=role)
    db.session.add(u)
    db.session.commit()
    return u


def test_only_admins_receive_administrative_summaries(app):
    with app.app_context():
        admin, ther, sup, pat = _user('admin'), _user('terapista'), _user('supervisor'), _user('jugador')
        ids = {u.id for u in reports.report_recipients()}
        assert admin.id in ids and not ids & {ther.id, sup.id, pat.id}

        sent = []
        with patch.object(digest, '_send_digest_for_user', side_effect=lambda u, s: sent.append(u.id)):
            digest.generate_daily_digests()
        assert admin.id in sent and not set(sent) & {ther.id, sup.id, pat.id}

        for fn in ('_send_weekly_report', '_send_monthly_report', '_send_annual_report'):
            with patch.object(reports, '_gather_period_data', side_effect=AssertionError('no debe generarse')):
                getattr(reports, fn)(ther, None, None)
        with patch.object(digest, '_gather_bsc_data', side_effect=AssertionError('no debe generarse')):
            digest._send_digest_for_user(ther, None)
