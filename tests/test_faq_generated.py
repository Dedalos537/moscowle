"""Pruebas de las FAQ generadas desde el catálogo de tools (Fase D).

Criterio de éxito del PRP: ≥ 30 FAQs con source='generated', sin duplicados
por pregunta normalizada, y el chat web NUNCA responde con FAQ (siempre con
tools) — solo Telegram usa match_faq.
"""

import re

import pytest

from app.models.faq import Faq
from app.services.faq_service import generate_faq_from_tools, hourly_auto_grow


@pytest.fixture(autouse=True)
def _clean_generated(db):
    """El fixture db es de sesión: cada test parte sin FAQs generadas."""
    Faq.query.filter_by(source='generated').delete(synchronize_session=False)
    db.session.commit()
    yield


class TestFaqGeneradas:
    def test_genera_al_menos_30_sin_duplicados(self, db):
        created = generate_faq_from_tools()
        assert created >= 30, f'solo se generaron {created} FAQs (mínimo 30)'

        generadas = Faq.query.filter_by(source='generated').all()
        assert len(generadas) >= 30
        assert all(f.status == 'active' and f.is_active for f in generadas)

        from app.services.faq_service import _normalize

        preguntas = [_normalize(f.question) for f in Faq.query.all()]
        assert len(preguntas) == len(set(preguntas)), 'hay preguntas duplicadas por normalización'

    def test_es_idempotente(self, db):
        first = generate_faq_from_tools()
        assert first > 0
        second = generate_faq_from_tools()
        assert second == 0, 'la segunda corrida no debe crear duplicados'

    def test_respuesta_explica_la_tool(self, db):
        generate_faq_from_tools(limit=10)
        f = Faq.query.filter_by(source='generated').first()
        assert f is not None
        # La respuesta debe citar la herramienta que resuelve la pregunta
        assert re.search(r'`[a-z_]+`', f.answer), 'la respuesta no cita ninguna tool'
        assert f.category == 'herramientas'

    def test_scheduler_cap_de_1_por_corrida(self, db, monkeypatch):
        """hourly_auto_grow crece máximo 1 FAQ generada por ejecución."""
        from app.services import faq_service

        captured = {}
        original = faq_service.generate_faq_from_tools

        def spy(limit=None):
            captured['limit'] = limit
            return original(limit=limit)

        monkeypatch.setattr(faq_service, 'generate_faq_from_tools', spy)
        monkeypatch.setattr(faq_service, 'auto_propose_faq', lambda: 0)
        hourly_auto_grow()
        assert captured.get('limit') == 1


class TestWebchatNoUsaFaq:
    def test_mcp_routes_nunca_consulta_faq_service(self):
        """El chat web responde SOLO con tools: mcp_routes no toca faq_service."""
        import pathlib

        src = pathlib.Path('app/routes/mcp_routes.py').read_text(encoding='utf-8')
        assert 'faq_service' not in src
        assert 'match_faq' not in src

    def test_solo_telegram_usa_match_faq(self):
        import pathlib

        routes = pathlib.Path('app/routes').rglob('*.py')
        for path in routes:
            if path.name in ('telegram_routes.py',):
                continue
            src = path.read_text(encoding='utf-8')
            assert 'match_faq' not in src, f'{path} no debe usar match_faq'
