import logging
import threading
import time
from datetime import datetime, timedelta

from sqlalchemy import text

from app.extensions import db

logger = logging.getLogger(__name__)


def send_slack_alert(webhook_url, alert):
    import requests

    payload = {
        'text': '*🚨 CrisisMonitor Alert*',
        'blocks': [
            {'type': 'header', 'text': {'type': 'plain_text', 'text': f'🚨 {alert["type"].replace("_", " ").title()}'}},
            {
                'type': 'section',
                'fields': [
                    {'type': 'mrkdwn', 'text': f'*Severity:* {alert.get("severity", "unknown")}'},
                    {'type': 'mrkdwn', 'text': f'*Value:* {alert.get("value", "N/A")}'},
                ],
            },
            {
                'type': 'context',
                'elements': [{'type': 'mrkdwn', 'text': f'Timestamp: {datetime.utcnow().isoformat()}'}],
            },
        ],
    }
    try:
        resp = requests.post(webhook_url, json=payload, timeout=10)
        resp.raise_for_status()
        logger.info('Slack alert sent: %s', alert['type'])
    except Exception as e:
        logger.exception('Failed to send Slack alert: %s', e)


def send_telegram_alert(bot_token, chat_id, alert):
    from app.models.telegram_user import TelegramUser

    tg_user = TelegramUser.query.filter_by(telegram_chat_id=chat_id, is_linked=True, is_active=True).first()
    if tg_user and not tg_user.notifications_enabled:
        logger.info('CrisisMonitor Telegram alert suppressed (notifications disabled)')
        return

    import requests

    text_msg = (
        f'🚨 *{alert["type"].replace("_", " ").title()}*\n'
        f'Severity: {alert.get("severity", "unknown")}\n'
        f'Value: {alert.get("value", "N/A")}\n'
        f'Time: {datetime.utcnow().isoformat()}'
    )
    url = f'https://api.telegram.org/bot{bot_token}/sendMessage'
    try:
        resp = requests.post(url, json={'chat_id': chat_id, 'text': text_msg, 'parse_mode': 'Markdown'}, timeout=10)
        resp.raise_for_status()
        logger.info('Telegram alert sent: %s', alert['type'])
    except Exception as e:
        logger.exception('Failed to send Telegram alert: %s', e)


def send_email_alert(recipient, alert):
    try:
        from flask_mail import Message as MailMessage

        from app.extensions import mail

        subject = f'[CrisisMonitor] {alert["type"].replace("_", " ").title()}'
        body = (
            f'Alert Type: {alert["type"]}\n'
            f'Severity: {alert.get("severity", "unknown")}\n'
            f'Value: {alert.get("value", "N/A")}\n'
            f'Timestamp: {datetime.utcnow().isoformat()}'
        )
        msg = MailMessage(subject, recipients=[recipient], body=body)
        mail.send(msg)
        logger.info('Email alert sent to %s: %s', recipient, alert['type'])
    except Exception as e:
        logger.exception('Failed to send email alert: %s', e)


class CrisisMonitor:
    def __init__(self, app=None):
        self._alert_callbacks = []
        self._metrics = {}
        self._lock = threading.Lock()
        self._thread = None
        if app:
            self.init_app(app)

    def init_app(self, app):
        interval = app.config.get('CRISIS_CHECK_INTERVAL', 300)
        slack_url = app.config.get('ALERT_SLACK_WEBHOOK_URL', '')
        telegram_token = app.config.get('ALERT_TELEGRAM_BOT_TOKEN', '')
        telegram_chat = app.config.get('ALERT_TELEGRAM_CHAT_ID', '')
        email_to = app.config.get('ALERT_EMAIL_TO', '')

        if slack_url:
            self.on_alert(lambda a: send_slack_alert(slack_url, a))
            app.logger.info('CrisisMonitor: Slack webhook registered')
        if telegram_token and telegram_chat:
            self.on_alert(lambda a: send_telegram_alert(telegram_token, telegram_chat, a))
            app.logger.info('CrisisMonitor: Telegram bot registered')
        if email_to:
            self.on_alert(lambda a: send_email_alert(email_to, a))
            app.logger.info('CrisisMonitor: Email alert registered')

        self._db_conn_threshold = app.config.get('ALERT_DB_CONN_THRESHOLD', 50)
        self._brute_force_threshold = app.config.get('ALERT_BRUTE_FORCE_THRESHOLD', 20)
        self._brute_force_window = app.config.get('ALERT_BRUTE_FORCE_WINDOW_MINUTES', 15)

        self._thread = threading.Thread(target=self._loop, args=(interval,), daemon=True)
        self._thread.start()
        app.logger.info('CrisisMonitor thread started (interval=%ss)', interval)
        if not (slack_url or (telegram_token and telegram_chat) or email_to):
            app.logger.warning(
                'CrisisMonitor: No alert channels configured. '
                'Set ALERT_SLACK_WEBHOOK_URL, ALERT_TELEGRAM_BOT_TOKEN+CHAT_ID, or ALERT_EMAIL_TO.'
            )

    def on_alert(self, callback):
        self._alert_callbacks.append(callback)

    def _loop(self, interval):
        while True:
            try:
                alerts = self._check_all()
                for alert in alerts:
                    for cb in self._alert_callbacks:
                        try:
                            cb(alert)
                        except Exception:
                            logger.exception('CrisisMonitor callback failed for alert: %s', alert.get('type'))
            except Exception:
                logger.exception('CrisisMonitor _loop check_all failed')
            time.sleep(interval)

    def _count_active_connections(self):
        try:
            dialect = db.engine.dialect.name
            if dialect == 'mysql':
                result = db.session.execute(text('SELECT COUNT(*) FROM information_schema.PROCESSLIST'))
                return result.scalar()
            elif dialect == 'postgresql':
                result = db.session.execute(text("SELECT count(*) FROM pg_stat_activity WHERE state = 'active'"))
                return result.scalar()
            elif dialect == 'sqlite':
                result = db.session.execute(text('SELECT COUNT(*) FROM sqlite_master'))
                return 0
            return None
        except Exception:
            logger.exception('CrisisMonitor _count_active_connections failed')
            return None

    def _create_incident_for_alert(self, alert):
        """Create an incident when a crisis alert is detected."""
        try:
            from app.models.incidente import Incidente
            from app.services.incident_escalation_service import IncidentEscalationService

            titulo = f'CrisisMonitor: {alert["type"].replace("_", " ").title()}'
            existente = Incidente.query.filter(
                Incidente.titulo == titulo,
                Incidente.estado.in_(['NUEVO', 'EN_CURSO']),
                Incidente.created_at > datetime.utcnow() - timedelta(hours=1),
            ).first()
            if existente:
                return

            now = datetime.utcnow()
            fecha_limite = IncidentEscalationService.calculate_sla_deadline(
                categoria='SOFTWARE',
                prioridad=1 if alert.get('severity') == 'critical' else 2,
                fecha_creacion=now,
            )

            incidente = Incidente(
                titulo=titulo,
                descripcion=(
                    f'Alerta automática de CrisisMonitor.\n'
                    f'Tipo: {alert["type"]}\n'
                    f'Severidad: {alert.get("severity", "unknown")}\n'
                    f'Valor: {alert.get("value", "N/A")}\n'
                    f'Timestamp: {now.isoformat()}'
                ),
                categoria='SOFTWARE',
                subcategoria='api_timeout',
                prioridad=1 if alert.get('severity') == 'critical' else 2,
                estado='NUEVO',
                user_id=1,
                evidencia_tipo='MONITORING',
                evidencia_original=f'{alert["type"]}: {alert.get("value", "N/A")}',
                fecha_creacion=now,
                fecha_limite_sla=fecha_limite,
            )
            db.session.add(incidente)
            db.session.commit()
            logger.info('Incidente #%s creado desde CrisisMonitor (%s)', incidente.id_incidente, alert['type'])
        except Exception:
            db.session.rollback()
            logger.exception('Failed to create incident from CrisisMonitor alert')

    def _check_all(self):
        alerts = []
        try:
            active_conns = self._count_active_connections()
            if active_conns is not None and active_conns > self._db_conn_threshold:
                alerts.append({'type': 'db_connections', 'severity': 'warning', 'value': active_conns})
        except Exception:
            logger.exception('CrisisMonitor db_connections check failed')

        try:
            recent = datetime.utcnow() - timedelta(minutes=self._brute_force_window)
            result = db.session.execute(
                text("SELECT count(*) FROM audit_log WHERE action='login_failed' AND created_at > :recent"),
                {'recent': recent},
            )
            failures = result.scalar()
            if failures > self._brute_force_threshold:
                alerts.append({'type': 'brute_force', 'severity': 'critical', 'value': failures})
        except Exception:
            logger.exception('CrisisMonitor brute_force check failed')

        try:
            from app.middleware.metrics_middleware import collector

            snap = collector.get_snapshot()
            latency = snap.get('latency', {})
            for _path_key, lat in latency.items():
                if lat.get('p95_ms', 0) > 800:
                    alerts.append(
                        {
                            'type': 'api_latency_high',
                            'severity': 'warning',
                            'value': lat['p95_ms'],
                        }
                    )
        except Exception:
            logger.exception('CrisisMonitor api_latency check failed')

        for alert in alerts:
            self._create_incident_for_alert(alert)

        with self._lock:
            self._metrics = {a['type']: a for a in alerts}
        return alerts

    def get_metrics(self):
        with self._lock:
            return dict(self._metrics)


crisis_monitor = CrisisMonitor()
