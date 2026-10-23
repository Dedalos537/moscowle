"""Conversaciones del asistente del admin (PRP 015): guardar, compartir, preguntar, actualizar y programar.

- Preguntas de datos del centro → `assistant_analytics` (bloques con los números del sistema).
- El resto → la IA general (OpenCode/MiMo con las herramientas MCP, con la cadena de respaldo), como texto.
- Quién ve qué: cada conversación es de su autor. Compartida, la ven los demás admins; un supervisor solo ve
  las compartidas por supervisores de su misma sede (nunca datos de todo el centro).
"""

from datetime import datetime, timedelta

from flask import current_app

from app.extensions import db
from app.models import User
from app.models.assistant_thread import AssistantMessage, AssistantSchedule, AssistantThread
from app.services import assistant_analytics as analytics

RETENTION_DAYS = 180
HISTORY_TURNS = 8


class AssistantError(Exception):
    def __init__(self, message, status=400):
        super().__init__(message)
        self.status = status


# ── acceso ──────────────────────────────────────────────────────────────────
def can_view(thread, user):
    if thread.user_id == user.id:
        return True
    if not thread.shared:
        return False
    author = db.session.get(User, thread.user_id)
    if user.role == 'admin':
        return True
    if user.role == 'supervisor' and author and author.role == 'supervisor':
        try:
            return analytics.scope_for(author) == analytics.scope_for(user)
        except analytics.ScopeError:
            return False
    return False


def get_thread(thread_id, user, *, write=False):
    thread = db.session.get(AssistantThread, thread_id)
    if not thread or not can_view(thread, user):
        raise AssistantError('Conversación no encontrada', 404)
    if write and thread.user_id != user.id:
        raise AssistantError('Solo quien la creó puede cambiarla', 403)
    return thread


def list_threads(user, query=None):
    own = AssistantThread.query.filter_by(user_id=user.id)
    shared = AssistantThread.query.filter(AssistantThread.shared.is_(True), AssistantThread.user_id != user.id)
    rows = own.all() + [t for t in shared.all() if can_view(t, user)]
    if query:
        q = query.lower()
        rows = [t for t in rows if q in (t.title or '').lower()]
    rows.sort(key=lambda t: (not t.pinned, -(t.updated_at or t.created_at).timestamp()))
    return [thread_dict(t, user) for t in rows]


def thread_dict(thread, user, with_messages=False):
    author = db.session.get(User, thread.user_id)
    out = {
        'id': thread.id,
        'title': thread.title,
        'pinned': thread.pinned,
        'shared': thread.shared,
        'mine': thread.user_id == user.id,
        'author': author.username if author else None,
        'created_at': thread.created_at.isoformat() + 'Z',
        'updated_at': (thread.updated_at or thread.created_at).isoformat() + 'Z',
    }
    if with_messages:
        out['messages'] = [message_dict(m) for m in thread.messages.all()]
        out['schedules'] = [
            schedule_dict(s) for s in AssistantSchedule.query.filter_by(thread_id=thread.id, user_id=user.id).all()
        ]
    return out


def message_dict(m):
    return {
        'id': m.id,
        'role': m.role,
        'text': m.text,
        'blocks': m.blocks or [],
        'sources': m.sources or [],
        'model': m.model,
        'question': m.question,
        'feedback': m.feedback,
        'created_at': m.created_at.isoformat() + 'Z',
    }


# ── preguntar ───────────────────────────────────────────────────────────────
def _history(thread):
    msgs = thread.messages.order_by(AssistantMessage.id.desc()).limit(HISTORY_TURNS * 2).all()
    return [{'role': m.role, 'content': m.text or ''} for m in reversed(msgs)]


def _general_ai(question, user, history):
    """Preguntas que no son de datos conocidos: la IA general del sistema (OpenCode/MCP con respaldo)."""
    from app.routes.mcp_routes import mcp_service

    try:
        result = mcp_service.process_message(
            message=question, user_role=user.role, user_id=user.id, mode='grande', history=history
        )
    except Exception as exc:  # noqa: BLE001 - la IA puede caerse: se responde algo útil igual
        current_app.logger.warning(f'asistente: IA general no respondió: {exc}')
        result = None
    text = (result or {}).get('response') or (
        'No pude responder eso ahora. Prueba con una pregunta de datos del centro, por ejemplo '
        '«¿cómo vamos este mes?» o «compara las sedes este trimestre».'
    )
    return {
        'title': question[:80],
        'blocks': [{'type': 'text', 'md': text}],
        'sources': [
            {'tool': t.get('name') or t.get('tool'), 'scope': 'IA'} for t in (result or {}).get('tool_calls') or []
        ],
        'model': (result or {}).get('provider') or 'IA del centro',
    }


def compute(question, user, history=None):
    """La respuesta (sin guardar): datos del centro si se reconoce la pregunta; si no, la IA general."""
    try:
        res = analytics.answer(question, user)
    except analytics.ScopeError as exc:
        raise AssistantError(str(exc), 403) from exc
    return res or _general_ai(question, user, history or [])


def _plain(blocks):
    return '\n\n'.join(b['md'] for b in blocks if b.get('type') == 'text')


def ask(user, question, thread_id=None):
    question = (question or '').strip()
    if not question:
        raise AssistantError('Escribe una pregunta')
    if len(question) > 2000:
        raise AssistantError('La pregunta es muy larga (máx. 2000 caracteres)')
    thread = get_thread(thread_id, user, write=True) if thread_id else None
    history = _history(thread) if thread else []
    res = compute(question, user, history)
    now = datetime.utcnow()
    if thread is None:
        thread = AssistantThread(user_id=user.id, title=(res.get('title') or question)[:160], created_at=now)
        db.session.add(thread)
        db.session.flush()
    db.session.add(AssistantMessage(thread_id=thread.id, role='user', text=question, created_at=now))
    answer = AssistantMessage(
        thread_id=thread.id,
        role='assistant',
        text=_plain(res['blocks']),
        blocks=res['blocks'],
        sources=res.get('sources') or [],
        model=res.get('model'),
        question=question,
        created_at=now,
    )
    db.session.add(answer)
    thread.updated_at = now
    db.session.commit()
    return thread, answer


def refresh(user, message_id):
    m = db.session.get(AssistantMessage, message_id)
    if not m or m.role != 'assistant' or not m.question:
        raise AssistantError('Respuesta no encontrada', 404)
    get_thread(m.thread_id, user, write=True)
    res = compute(m.question, user)
    m.blocks, m.sources, m.model, m.text = (
        res['blocks'],
        res.get('sources') or [],
        res.get('model'),
        _plain(res['blocks']),
    )
    m.created_at = datetime.utcnow()
    db.session.commit()
    return m


def set_feedback(user, message_id, value):
    m = db.session.get(AssistantMessage, message_id)
    if not m or m.role != 'assistant':
        raise AssistantError('Respuesta no encontrada', 404)
    get_thread(m.thread_id, user)
    m.feedback = 1 if value > 0 else -1 if value < 0 else None
    db.session.commit()
    return m


def update_thread(user, thread_id, data):
    thread = get_thread(thread_id, user, write=True)
    if 'title' in data and str(data['title']).strip():
        thread.title = str(data['title']).strip()[:160]
    for key in ('pinned', 'shared'):
        if key in data:
            setattr(thread, key, bool(data[key]))
    db.session.commit()
    return thread


def delete_thread(user, thread_id):
    thread = get_thread(thread_id, user, write=True)
    AssistantSchedule.query.filter_by(thread_id=thread.id).update({'thread_id': None})
    db.session.delete(thread)
    db.session.commit()


def purge_old(now=None):
    """Retención: conversaciones no fijadas sin actividad en 180 días."""
    limit = (now or datetime.utcnow()) - timedelta(days=RETENTION_DAYS)
    old = AssistantThread.query.filter(AssistantThread.pinned.is_(False), AssistantThread.updated_at < limit).all()
    for t in old:
        db.session.delete(t)
    db.session.commit()
    return len(old)


# ── reportes programados ────────────────────────────────────────────────────
CADENCES = ('daily', 'weekly')
CHANNELS = ('email', 'telegram', 'both')
WEEKDAYS = ['lunes', 'martes', 'miércoles', 'jueves', 'viernes', 'sábado', 'domingo']


def schedule_dict(s):
    when = f'cada día a las {s.hour:02d}:00'
    if s.cadence == 'weekly':
        when = f'cada {WEEKDAYS[s.weekday or 0]} a las {s.hour:02d}:00'
    return {
        'id': s.id,
        'question': s.question,
        'cadence': s.cadence,
        'weekday': s.weekday,
        'hour': s.hour,
        'channel': s.channel,
        'active': s.active,
        'thread_id': s.thread_id,
        'label': when,
        'last_run_at': s.last_run_at.isoformat() + 'Z' if s.last_run_at else None,
    }


def create_schedule(user, data):
    question = (data.get('question') or '').strip()
    if not question:
        raise AssistantError('Falta la pregunta a repetir')
    cadence = data.get('cadence') or 'weekly'
    channel = data.get('channel') or 'email'
    hour = int(data.get('hour') if data.get('hour') is not None else 8)
    weekday = int(data.get('weekday') or 0)
    if cadence not in CADENCES or channel not in CHANNELS or not 0 <= hour <= 23 or not 0 <= weekday <= 6:
        raise AssistantError('Programación no válida')
    if analytics.answer(question, user) is None:
        raise AssistantError(
            'Solo se pueden programar preguntas de datos del centro (resumen, sedes, equipo, deudores…).'
        )
    thread_id = data.get('thread_id')
    if thread_id:
        get_thread(int(thread_id), user, write=True)
    s = AssistantSchedule(
        user_id=user.id,
        thread_id=thread_id,
        question=question[:2000],
        cadence=cadence,
        weekday=weekday if cadence == 'weekly' else None,
        hour=hour,
        channel=channel,
    )
    db.session.add(s)
    db.session.commit()
    return s


def delete_schedule(user, schedule_id):
    s = db.session.get(AssistantSchedule, schedule_id)
    if not s or s.user_id != user.id:
        raise AssistantError('Programación no encontrada', 404)
    db.session.delete(s)
    db.session.commit()


def _due(s, now_lima):
    if not s.active or now_lima.hour != s.hour:
        return False
    if s.cadence == 'weekly' and now_lima.weekday() != (s.weekday or 0):
        return False
    return not (s.last_run_at and s.last_run_at > datetime.utcnow() - timedelta(hours=20))


def _render_text(res):
    lines = [_plain(res['blocks']).replace('**', '')]
    for b in res['blocks']:
        if b['type'] == 'kpis':
            for k in b['items']:
                lines.append(f'· {k["label"]}: {analytics._fmt(k["value"], k["format"])}')
        if b['type'] == 'table':
            lines.append(f'\n{b["title"]}:')
            for r in b['rows'][:15]:
                lines.append(
                    '· '
                    + ' · '.join(str(r.get(c['key']) if r.get(c['key']) is not None else '—') for c in b['columns'])
                )
    return '\n'.join(lines)


def run_schedules(now_lima=None):
    """Lo llama el scheduler cada hora: corre las preguntas programadas y manda la respuesta."""
    from zoneinfo import ZoneInfo

    now_lima = now_lima or datetime.now(ZoneInfo('America/Lima'))
    sent = 0
    for s in AssistantSchedule.query.filter_by(active=True).all():
        if not _due(s, now_lima):
            continue
        user = db.session.get(User, s.user_id)
        if not user or not user.is_active:
            continue
        try:
            res = analytics.answer(s.question, user)
        except analytics.ScopeError:
            continue
        if not res:
            continue
        text = _render_text(res)
        subject = f'[Moscowle] {res["title"]}'
        if s.channel in ('email', 'both'):
            _send_email(user, subject, text)
        if s.channel in ('telegram', 'both'):
            _send_telegram(user, f'*{res["title"]}*\n\n{text}')
        if s.thread_id:
            thread = db.session.get(AssistantThread, s.thread_id)
            if thread:
                db.session.add(
                    AssistantMessage(
                        thread_id=thread.id,
                        role='assistant',
                        text=_plain(res['blocks']),
                        blocks=res['blocks'],
                        sources=res.get('sources'),
                        model='reporte programado',
                        question=s.question,
                    )
                )
                thread.updated_at = datetime.utcnow()
        s.last_run_at = datetime.utcnow()
        db.session.commit()
        sent += 1
    return sent


def _send_email(user, subject, text):
    from app.services.email_service import EmailService, recipient_for

    to = recipient_for(user)
    if to:
        EmailService.send_notification_email(subject, [to], body=text, user_id=user.id)


def _send_telegram(user, text):
    try:
        from app.models.telegram_user import TelegramUser
        from app.services.telegram_bot_service import send_telegram_message

        for tg in TelegramUser.query.filter_by(admin_user_id=user.id, is_linked=True).all():
            send_telegram_message(tg.telegram_chat_id, text[:3900])
    except Exception as exc:  # noqa: BLE001
        current_app.logger.warning(f'asistente: no se pudo enviar por Telegram: {exc}')
