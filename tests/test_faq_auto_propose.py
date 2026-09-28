"""Pruebas del mecanismo de auto-propuesta de FAQs.

Hallazgos que corrigen:
- `_UnansweredTracker.popular()` filtraba con >= 3 fijo, asi que un
  `auto_faq_threshold` configurado en 1 o 2 nunca surtia efecto.
- `auto_propose_faq()` llamaba `clear()` y borraba los contadores de TODAS las
  preguntas, incluidas las que seguian por debajo del umbral.
- `note_unanswered()` se llamaba antes de que la IA respondiera, por lo que
  preguntas que las tools si respondian terminaban propuestas como FAQ.
"""

import pytest

from app.services import faq_service
from app.services.faq_service import _UnansweredTracker
from app.services.telegram_bot_service import _note_if_unanswered


class TestUmbralConfigurable:
    def test_umbral_de_1_surge_efecto(self, tracker):
        tracker.note('como solicito una cita')
        assert tracker.popular(threshold=1), 'con umbral 1 una sola repeticion debe bastar'

    def test_umbral_de_2_requiere_dos(self, tracker):
        tracker.note('como solicito una cita')
        assert tracker.popular(threshold=2) == [], 'con umbral 2 una repeticion no debe bastar'
        tracker.note('como solicito una cita')
        assert tracker.popular(threshold=2), 'con umbral 2 la segunda repeticion debe bastar'

    def test_umbral_3_ignora_dos(self, tracker):
        tracker.note('como solicito una cita')
        tracker.note('como solicito una cita')
        assert tracker.popular(threshold=3) == []

    def test_umbral_invalido_usa_3(self, tracker):
        for _ in range(3):
            tracker.note('pregunta de prueba')
        assert tracker.popular('basura') != []
        assert tracker.popular(None) != []


class TestBorradoSelectivo:
    def test_forget_solo_borra_lo_promovido(self, tracker):
        tracker.note('pregunta que se promueve')
        tracker.note('pregunta que sigue acumulando')
        tracker.forget(['pregunta que se promueve'])
        restantes = [i['question'] for i in tracker.popular(threshold=1)]
        assert 'pregunta que sigue acumulando' in restantes
        assert 'pregunta que se promueve' not in restantes

    def test_clear_sigue_vaciando_todo(self, tracker):
        tracker.note('a')
        tracker.note('b')
        tracker.clear()
        assert tracker.popular(threshold=1) == []


class TestAutoProposeNoBorraContadoresAjenos:
    def test_contadores_bajos_el_umbral_se_conservan(self, app, monkeypatch):
        """Crear una propuesta no debe Resetear las preguntas que faltan	count."""
        tracker = _UnansweredTracker()
        monkeypatch.setattr(faq_service, '_unanswered', tracker)

        # una pregunta llega al umbral y otra se queda a medias
        for _ in range(3):
            tracker.note('pregunta promovida ahora')
        tracker.note('pregunta todavia abajo')

        monkeypatch.setattr(faq_service, '_proposed_exists', lambda q: False)
        monkeypatch.setattr(faq_service, 'match_faq', lambda *a, **k: [])

        class Cfg:
            auto_faq_enabled = True
            auto_faq_threshold = 3

        monkeypatch.setattr(faq_service.BotConfig, 'get_or_create', staticmethod(lambda: Cfg()))

        created = faq_service.auto_propose_faq()
        assert created == 1, 'debe crearse exactamente una propuesta'

        # la pregunta promovida salio del registro, la otra sigue contando
        pendientes = {i['question'] for i in tracker.popular(threshold=1)}
        assert 'pregunta todavia abajo' in pendientes, (
            'el registro completo se borro y se perdio el contador de otra pregunta'
        )


class TestContarSoloSiLaIARespondio:
    """_note_if_unanswered debe distinguir 'sin FAQ' de 'el asistente no pudo responder'."""

    @pytest.fixture
    def registradas(self, monkeypatch):
        import app.services.faq_service as fs

        visto = []
        monkeypatch.setattr(fs, 'note_unanswered', lambda t: visto.append(t))
        return visto

    def test_no_cuenta_si_hubo_tool_call(self, registradas):
        _note_if_unanswered(
            {'response': 'Hay 2 sedes: Piura y Talara', 'tool_calls': [{'name': 'list_sedes'}]},
            'cuantas sedes hay',
        )
        assert registradas == [], 'una respuesta con tool call NO es una pregunta sin responder'

    def test_no_cuenta_si_respondio_con_texto_util(self, registradas):
        _note_if_unanswered(
            {'response': 'Para agendar una cita debes llamar al centro de lunes a viernes.'},
            'como agendo una cita',
        )
        assert registradas == [], 'una respuesta sustantiva no debe contar como fallida'

    def test_cuenta_si_la_ia_no_pudo_responder(self, registradas):
        _note_if_unanswered(
            {'response': 'No pude generar una respuesta.'},
            'pregunta muy rara del usuario',
        )
        assert registradas == ['pregunta muy rara del usuario']

    def test_no_cuenta_si_hubo_error(self, registradas):
        _note_if_unanswered({'error': 'boom'}, 'otra pregunta')
        assert registradas == []

    def test_no_cuenta_texto_vacio(self, registradas):
        _note_if_unanswered({'response': '   '}, 'pregunta sin respuesta real')
        assert registradas == []


@pytest.fixture
def tracker(app):
    """Tracker limpio en BD para cada test."""
    t = _UnansweredTracker()
    t.clear()
    yield t
    t.clear()


class TestPersistencia:
    """Los contadores deben sobrevivir a un reinicio y ser compartidos."""

    def test_el_contador_sobrevive_a_otra_instancia(self, app):
        """Un tracker nuevo (como tras reiniciar el worker) ve el mismo contador."""
        from app.models.faq_unanswered import FaqUnanswered

        _UnansweredTracker().clear()
        _UnansweredTracker().note('pregunta que debe persistir')
        _UnansweredTracker().note('pregunta que debe persistir')

        # instancia nueva: simula otro worker o un reinicio
        otro = _UnansweredTracker()
        assert [i['count'] for i in otro.popular(threshold=1)] == [2], (
            'el contador no persistio: se perderia al reiniciar el proceso'
        )
        assert FaqUnanswered.query.count() == 1
        _UnansweredTracker().clear()

    def test_normaliza_para_no_duplicar(self, app):
        _UnansweredTracker().clear()
        t = _UnansweredTracker()
        t.note('Como solicito una cita?')
        t.note('¿como solicito una cita')
        from app.models.faq_unanswered import FaqUnanswered

        assert FaqUnanswered.query.count() == 1, 'variaciones del mismo texto deben sumarse'
        assert t.popular(threshold=2)[0]['count'] == 2
        _UnansweredTracker().clear()
