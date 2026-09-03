import difflib
import logging
import re
from collections import Counter
from datetime import UTC

from app.extensions import db
from app.models.bot_config import BotConfig
from app.models.faq import Faq

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
    """In-memory tracker of repeated unanswered questions to auto-propose FAQ."""

    def __init__(self):
        self._log = {}  # normalized question -> counter

    def note(self, text):
        if not text or len(text.strip()) < 6:
            return
        key = _normalize(text)[:120]
        c = self._log.setdefault(key, Counter())
        c['text'] = text.strip()[:300]
        c['count'] += 1
        return c

    def popular(self):
        out = []
        for _key, c in self._log.items():
            if c.get('count', 0) >= 3:
                out.append({'question': c['text'], 'count': c['count']})
        return out

    def clear(self):
        self._log.clear()


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
    for item in _unanswered.popular():
        if item['count'] < threshold:
            continue
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
        created += 1
    if created:
        db.session.commit()
        _unanswered.clear()
    return created


def hourly_auto_grow():
    """Callable for the scheduler: create proposed FAQs from repeated unanswered hits."""
    return auto_propose_faq()
