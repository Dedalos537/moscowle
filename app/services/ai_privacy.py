"""Seudonimización de lo que se manda a un modelo externo (PRP 009).

Un `Vault` por conversación cambia nombres, correos, teléfonos y DNI por fichas («P1», «E2»…) antes de
enviar, y las devuelve a su valor real en la respuesta y en los argumentos de las tools. Las notas
clínicas no se mandan nunca: se reemplazan por `[omitido]`.
"""

import re
import time
import unicodedata

from app.extensions import db

NAME_KEYS = {
    'name',
    'username',
    'patient',
    'patient_name',
    'paciente',
    'full_name',
    'nombre',
    'payer',
    'payer_name',
    'pagador',
    'therapist',
    'therapist_name',
    'terapeuta',
    'guardian_name',
    'apoderado',
    'contact_name',
    'sender',
    'recipient',
}
EMAIL_KEYS = {'email', 'correo'}
PHONE_KEYS = {'phone', 'telefono', 'teléfono', 'whatsapp', 'celular'}
DOC_KEYS = {'dni', 'document_number', 'documento'}
CLINICAL_KEYS = {
    'notes',
    'note',
    'nota',
    'notas',
    'diagnosis',
    'diagnostico',
    'diagnóstico',
    'observations',
    'observaciones',
    'clinical_notes',
    'session_notes',
    'evaluation',
    'evaluacion',
    'evaluación',
    'medical_history',
    'antecedentes',
}

_EMAIL_RE = re.compile(r'[\w.+-]+@[\w-]+\.[\w.-]+')
_PHONE_RE = re.compile(r'(?<!\d)(?:\+?51\s?)?9\d{2}[\s-]?\d{3}[\s-]?\d{3}(?!\d)')
_DNI_RE = re.compile(r'(?<![\d/.-])\d{8}(?![\d/.-])')
_TOKEN_RE = re.compile(r'«[PECD]\d+»')

_names_cache: dict = {'at': 0.0, 'items': ()}


def _fold(s):
    return ''.join(c for c in unicodedata.normalize('NFD', s.lower()) if unicodedata.category(c) != 'Mn')


def known_names(ttl=300):
    """Nombres de pacientes y apoderados activos (más largos primero), cacheados 5 min."""
    if time.time() - _names_cache['at'] < ttl:
        return _names_cache['items']
    from app.models import User

    rows = db.session.query(User.username, User.guardian_name).filter(User.is_active.isnot(False)).all()
    names = {n.strip() for row in rows for n in row if n and len(n.strip()) >= 5 and ' ' in n.strip()}
    _names_cache.update(at=time.time(), items=tuple(sorted(names, key=len, reverse=True)))
    return _names_cache['items']


class Vault:
    def __init__(self):
        self.real_by_token: dict[str, str] = {}
        self.token_by_real: dict[tuple[str, str], str] = {}
        self.counts = {'P': 0, 'E': 0, 'C': 0, 'D': 0}

    def token(self, kind, value):
        key = (kind, _fold(value.strip()))
        if key not in self.token_by_real:
            self.counts[kind] += 1
            tok = f'«{kind}{self.counts[kind]}»'
            self.token_by_real[key] = tok
            self.real_by_token[tok] = value.strip()
        return self.token_by_real[key]

    def mask_text(self, text, names=None):
        if not text:
            return text
        out = unicodedata.normalize('NFC', text)
        out = _EMAIL_RE.sub(lambda m: self.token('E', m.group()), out)
        out = _PHONE_RE.sub(lambda m: self.token('C', m.group()), out)
        out = _DNI_RE.sub(lambda m: self.token('D', m.group()), out)
        folded = _fold(out)
        for name in names if names is not None else known_names():
            fname = _fold(name)
            start = folded.find(fname)
            while start != -1:
                tok = self.token('P', name)
                out = out[:start] + tok + out[start + len(name) :]
                folded = folded[:start] + tok + folded[start + len(name) :]
                start = folded.find(fname, start + len(tok))
        return out

    def mask(self, obj, names=None, key=None):
        names = known_names() if names is None else names
        if isinstance(obj, dict):
            return {k: self.mask(v, names, str(k).lower()) for k, v in obj.items()}
        if isinstance(obj, list):
            return [self.mask(v, names, key) for v in obj]
        if not isinstance(obj, str):
            return obj
        if key in CLINICAL_KEYS:
            return '[omitido]' if obj.strip() else obj
        if key in NAME_KEYS and obj.strip():
            return self.token('P', obj)
        if key in EMAIL_KEYS and obj.strip():
            return self.token('E', obj)
        if key in PHONE_KEYS and obj.strip():
            return self.token('C', obj)
        if key in DOC_KEYS and obj.strip():
            return self.token('D', obj)
        return self.mask_text(obj, names)

    def unmask(self, obj):
        if isinstance(obj, dict):
            return {k: self.unmask(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [self.unmask(v) for v in obj]
        if isinstance(obj, str):
            return _TOKEN_RE.sub(lambda m: self.real_by_token.get(m.group(), m.group()), obj)
        return obj
