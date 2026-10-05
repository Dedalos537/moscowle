import difflib
import logging
import re
from datetime import UTC, datetime

from app.extensions import db
from app.models.bot_config import BotConfig
from app.models.faq import Faq
from app.models.faq_unanswered import FaqUnanswered

logger = logging.getLogger('app.faq')


def _tokenize(text):
    return re.findall(r'[a-záéíóúñü0-9]{3,}', (text or '').lower())


def _normalize(text):
    return re.sub(r'[^\w\sáéíóúñüÁÉÍÓÚÑÜ]', ' ', (text or '').lower()).strip()


def match_faq(text, limit=3):
    """Return the best FAQ matches for a user message.

    Matching is by keyword overlap or fuzzy substring similarity on the question.
    Each returned item is a dict with the FAQ plus a score.
    """
    if not text:
        return []
    tokens = _tokenize(text)
    if not tokens:
        return []
    norm = _normalize(text)

    faqs = Faq.query.filter_by(is_active=True, status='active').all()
    scored = []
    for faq in faqs:
        score = 0
        q_tokens = _tokenize(faq.question)
        overlap = len(set(tokens) & set(q_tokens))
        if overlap:
            score += overlap * 2

        kw = _tokenize(faq.keywords or '')
        kw_overlap = len(set(tokens) & set(kw))
        score += kw_overlap * 3

        # Substring / fuzzy proximity on normalized question
        q_norm = _normalize(faq.question)
        if len(norm) > 4 and q_norm and (q_norm in norm or norm in q_norm):
            score += 6
        elif len(norm) > 4:
            ratio = difflib.SequenceMatcher(None, norm, q_norm).ratio()
            if ratio > 0.55:
                score += round(ratio * 5)

        if score:
            scored.append({'faq': faq, 'score': score, 'id': faq.id})

    scored.sort(key=lambda x: x['score'], reverse=True)
    return scored[:limit]


def record_usage(faq_ids):
    """Increment usage counters for matched FAQs (auto-growth from real usage)."""
    if not faq_ids:
        return
    from datetime import datetime

    for fid in faq_ids:
        faq = Faq.query.get(fid)
        if faq:
            faq.usage_count = (faq.usage_count or 0) + 1
            faq.last_used_at = datetime.now(UTC)
    db.session.commit()


class _UnansweredTracker:
    """Contador de preguntas repetidas sin responder, persistido en la BD.

    Antes era un diccionario en memoria: los contadores se perdian al
    reiniciar y cada worker de gunicorn llevaba su propia copia, asi que una
    pregunta podia no alcanzar el umbral nunca. Se mantiene la misma API
    (note/popular/forget/clear) para no tocar los llamadores.
    """

    def note(self, text):
        if not text or len(text.strip()) < 6:
            return None
        key = _normalize(text)[:160]
        now = datetime.now(UTC)
        row = FaqUnanswered.query.filter_by(question_key=key).first()
        if row is None:
            row = FaqUnanswered(
                question_key=key,
                question=text.strip()[:300],
                count=1,
                first_seen_at=now,
                last_seen_at=now,
            )
            db.session.add(row)
        else:
            row.count = (row.count or 0) + 1
            row.question = text.strip()[:300]
            row.last_seen_at = now
        try:
            db.session.commit()
        except Exception:
            db.session.rollback()
            logger.exception('No se pudo registrar la pregunta sin responder')
            return None
        return row

    def popular(self, threshold=3):
        """Preguntas que alcanzaron el umbral.

        Antes el umbral estaba fijo en 3 dentro de popular(), asi que un
        auto_faq_threshold de 1 o 2 nunca podia surtir efecto: el filtro
        ocurria antes de comparar con el umbral configurado.
        """
        try:
            threshold = max(1, int(threshold))
        except (TypeError, ValueError):
            threshold = 3
        rows = FaqUnanswered.query.filter(FaqUnanswered.count >= threshold).order_by(FaqUnanswered.count.desc()).all()
        return [{'question': r.question, 'count': r.count} for r in rows]

    def forget(self, questions):
        """Elimina solo las preguntas indicadas.

        clear() borraba el registro completo al crear propuestas y perdia los
        contadores de otras preguntas que aun estaban acumulando.
        """
        keys = [_normalize(q)[:160] for q in questions if q]
        if not keys:
            return
        try:
            FaqUnanswered.query.filter(FaqUnanswered.question_key.in_(keys)).delete(synchronize_session=False)
            db.session.commit()
        except Exception:
            db.session.rollback()
            logger.exception('No se pudo limpiar el registro de preguntas')

    def clear(self):
        try:
            FaqUnanswered.query.delete(synchronize_session=False)
            db.session.commit()
        except Exception:
            db.session.rollback()
            logger.exception('No se pudo vaciar el registro de preguntas')


_unanswered = _UnansweredTracker()


def note_unanswered(text):
    _unanswered.note(text)


def _proposed_exists(question):
    q = _normalize(question)
    return any(_normalize(f.question) == q for f in Faq.query.filter(Faq.status == 'proposed').all())


def auto_propose_faq():
    """Promote repeated unanswered questions to 'proposed' FAQs WITHOUT an answer.

    The answer field is seeded with a placeholder so the admin can fill it in from the
    FAQ tab. Backed by the auto_faq_threshold from BotConfig.
    """
    cfg = BotConfig.get_or_create()
    if not cfg.auto_faq_enabled:
        return 0
    threshold = max(1, cfg.auto_faq_threshold or 3)

    created = 0
    promoted = []
    for item in _unanswered.popular(threshold):
        if _proposed_exists(item['question']):
            continue
        # Skip if an active FAQ already covers it
        if match_faq(item['question'], limit=1):
            continue
        faq = Faq(
            question=item['question'],
            answer='⏳ Pendiente de respuesta. (El bot aún no sabe responder esto.)',
            category='auto',
            keywords='',
            is_active=False,
            source='auto_proposed',
            status='proposed',
            usage_count=item['count'],
        )
        db.session.add(faq)
        promoted.append(item['question'])
        created += 1
    if created:
        db.session.commit()
        # Solo se retiran las preguntas promovidas: las demas siguen contando.
        _unanswered.forget(promoted)
    return created


def _faq_templates(name, entry):
    """1-3 preguntas FAQ en español derivadas de la descripción de la tool.

    El sustantivo temático sale de la propia descripción (mismo léxico
    normalizado que tool_intents), así el catálogo de preguntas se GENERA
    y no se escribe a mano tool por tool.
    """
    from app.services.tool_intents import _content_words, norm

    desc = (entry.get('description') or '').strip()
    if len(desc.split()) < 4:
        return []
    nouns = _content_words(desc)
    if not nouns:
        return []
    subject = nouns[0]
    plural_q = 'cuántas' if subject.endswith(('a', 'as')) else 'cuántos'
    questions = [f'Lista de {subject}', f'¿Qué {subject} hay?']
    if re.search(r'cuant|cantidad|total|estadistic', desc, re.IGNORECASE):
        questions.append(f'¿{plural_q.title()} {subject} hay?')

    first_sentence = re.split(r'(?<=[.!?])\s', desc)[0]
    answer = (
        f'Lo resuelve la herramienta `{name}` del asistente: {first_sentence} '
        'El asistente llamará esa herramienta con los parámetros de tu mensaje '
        'y te mostrará exactamente lo que devuelva (sin inventar datos).'
    )
    keywords = norm(f'{name} {subject} ' + ' '.join(nouns[1:4]))
    return [(q, answer, keywords) for q in questions]


def generate_faq_from_tools(limit=None):
    """Crea FAQs activas (source='generated') derivadas del catálogo de tools.

    Regla de oro: SIN duplicados por pregunta normalizada contra TODAS las
    FAQs existentes (manuales, auto-propuestas o generadas), para que el
    catálogo pueda crecer de forma incremental sin ensuciar la base.
    ``limit`` acota cuántas crea en esta corrida (el scheduler usa 1).
    Devuelve el número de FAQs creadas.
    """
    from app.services.tools_registry import TOOL_REGISTRY

    existing = {_normalize(f.question) for f in Faq.query.with_entities(Faq.question).all()}
    created = 0
    for name, entry in TOOL_REGISTRY.items():
        if entry.get('category') != 'read':
            continue
        for question, answer, keywords in _faq_templates(name, entry):
            q_norm = _normalize(question)
            if q_norm in existing:
                continue
            db.session.add(
                Faq(
                    question=question,
                    answer=answer,
                    category='herramientas',
                    keywords=keywords,
                    is_active=True,
                    source='generated',
                    status='active',
                )
            )
            existing.add(q_norm)
            created += 1
            if limit is not None and created >= limit:
                db.session.commit()
                return created
    if created:
        db.session.commit()
    return created


def hourly_auto_grow():
    """Callable for the scheduler: create proposed FAQs from repeated unanswered hits
    and, como máximo 1 por corrida, FAQs generadas desde el catálogo de tools."""
    return auto_propose_faq() + generate_faq_from_tools(limit=1)
