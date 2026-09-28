"""Pruebas del resolutor de entidades.

El bot no resolvia nombres a identificadores: "sedes talara y piura" no llegaba
a get_sede_stats con sede_id=1 y sede_id=2, asi que respondia con la lista de
sedes sin contarlas, que es justo la queja reportada.

La resolucion es una consulta a la base de datos, no una tarea de LLM: asi que
va en codigo, es determinista y no depende del modelo.
"""

import pytest


@pytest.fixture
def sede_factory(db, session):
    from app.models.user import Sede

    created = []
    for nombre, direccion in (('Piura', 'Jr. Vicús 311'), ('Talara', 'Calle Grau 120')):
        existente = Sede.query.filter_by(name=nombre).first()
        if not existente:
            existente = Sede(name=nombre, address=direccion, is_active=True)
            session.add(existente)
            created.append(existente)
    session.commit()
    return created


class TestResolucionDeSedes:
    def test_resuelve_un_nombre_de_sede(self, sede_factory, session):
        from app.services.entity_resolver import resolve_entities

        r = resolve_entities('cuántos pacientes hay en Talara')
        assert r.sedes, 'no resolvio ninguna sede'
        assert {s['name'] for s in r.sedes} == {'Talara'}
        assert all(isinstance(s['id'], int) for s in r.sedes)

    def test_resuelve_varias_sedes_en_una_frase(self, sede_factory, session):
        from app.services.entity_resolver import resolve_entities

        r = resolve_entities('sedes talara y piura')
        assert {s['name'] for s in r.sedes} == {'Talara', 'Piura'}

    def test_es_sensible_a_mayusculas_y_acentos(self, sede_factory, session):
        from app.services.entity_resolver import resolve_entities

        r = resolve_entities('SEDES TALARA Y PIÚRA')
        assert {s['name'] for s in r.sedes} == {'Talara', 'Piura'}

    def test_ignora_sedes_inexistentes(self, sede_factory, session):
        from app.services.entity_resolver import resolve_entities

        r = resolve_entities('qué pasa en la sede Iquitos')
        assert r.sedes == []

    def test_no_resuelve_si_la_frase_no_habla_de_sedes(self, sede_factory, session):
        from app.services.entity_resolver import resolve_entities

        r = resolve_entities('quiero registrar un pago de 200 soles')
        assert r.sedes == []


class TestResolucionDeFechas:
    @pytest.mark.parametrize(
        'frase,tiene_fecha',
        [
            ('cuántas sesiones hay hoy', True),
            ('agenda de mañana', True),
            ('reporte de este mes', True),
            ('reporte del mes pasado', True),
        ],
    )
    def test_detecta_palabras_de_fecha(self, frase, tiene_fecha):
        from app.services.entity_resolver import resolve_entities

        r = resolve_entities(frase)
        assert bool(r.temporal) is tiene_fecha

    def test_una_frase_sin_fecha_no_inventa_una(self):
        from app.services.entity_resolver import resolve_entities

        r = resolve_entities('quién es el paciente 14')
        assert not r.temporal


class TestSalidaParaElPrompt:
    def test_se_serializa_a_texto_para_inyectar_en_el_prompt(self, sede_factory, session):
        from app.services.entity_resolver import resolve_entities

        r = resolve_entities('sedes talara y piura')
        texto = r.to_prompt_context()
        assert 'Talara' in texto and 'Piura' in texto
        # Debe incluir los ids para que el modelo no tenga que inventarlos.
        assert 'id=' in texto or ':' in texto

    def test_sin_entidades_el_texto_es_vacio(self):
        from app.services.entity_resolver import resolve_entities

        r = resolve_entities('hola')
        assert r.to_prompt_context() == ''

    def test_no_revela_nombres_de_pacientes_si_el_rol_no_lo_permite(self, db, session):
        """Un jugador no puede usar la resolucion para enumerar pacientes."""
        from app.models.user import User
        from app.services.entity_resolver import resolve_entities

        session.add(
            User(
                username='paciente_secreto',
                email='secreto@x.com',
                password='x',
                role='jugador',
            )
        )
        session.commit()

        r = resolve_entities('busca a paciente_secreto', role='jugador')
        assert r.patients == [], f'un jugador resolvio pacientes ajenos: {r.patients}'
