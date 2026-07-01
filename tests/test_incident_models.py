from app.extensions import bcrypt
from app.models.incidente import Incidente, IncidenteComentario, IncidenteHistorial
from app.models.user import User


class TestIncidenteModel:
    def test_create_incidente(self, session):
        user = User(
            username='testadmin',
            email='admin@test.com',
            role='admin',
            password=bcrypt.generate_password_hash('test123').decode('utf-8'),
        )
        session.add(user)
        session.flush()

        incidente = Incidente(
            titulo='Test incidente',
            descripcion='Descripción de prueba',
            categoria='SOFTWARE',
            prioridad=2,
            estado='NUEVO',
            user_id=user.id,
            evidencia_tipo='MANUAL',
            evidencia_original='test evidence',
        )
        session.add(incidente)
        session.commit()

        assert incidente.id_incidente is not None
        assert incidente.titulo == 'Test incidente'
        assert incidente.categoria == 'SOFTWARE'
        assert incidente.prioridad == 2
        assert incidente.estado == 'NUEVO'

    def test_incidente_repr(self, session):
        user = User(
            username='repruser',
            email='repr@test.com',
            role='admin',
            password=bcrypt.generate_password_hash('test123').decode('utf-8'),
        )
        session.add(user)
        session.flush()

        incidente = Incidente(
            titulo='Repr test',
            descripcion='Test',
            categoria='HARDWARE',
            estado='NUEVO',
            user_id=user.id,
            evidencia_tipo='MANUAL',
            evidencia_original='evidence',
        )
        session.add(incidente)
        session.commit()
        assert 'Incidente' in repr(incidente)
        assert str(incidente.id_incidente) in repr(incidente)

    def test_horas_restantes_sla(self, session):
        from datetime import datetime, timedelta

        user = User(
            username='slatest',
            email='sla@test.com',
            role='admin',
            password=bcrypt.generate_password_hash('test123').decode('utf-8'),
        )
        session.add(user)
        session.flush()

        now = datetime.utcnow()
        incidente = Incidente(
            titulo='SLA test',
            descripcion='Test',
            categoria='SOFTWARE',
            estado='NUEVO',
            user_id=user.id,
            evidencia_tipo='MANUAL',
            evidencia_original='evidence',
            fecha_limite_sla=now + timedelta(hours=5),
        )
        session.add(incidente)
        session.commit()

        horas = incidente.horas_restantes_sla
        assert horas is not None
        assert 4.5 < horas < 5.5

    def test_esta_vencido(self, session):
        from datetime import datetime, timedelta

        user = User(
            username='vencidotest',
            email='vencido@test.com',
            role='admin',
            password=bcrypt.generate_password_hash('test123').decode('utf-8'),
        )
        session.add(user)
        session.flush()

        now = datetime.utcnow()
        incidente = Incidente(
            titulo='Vencido test',
            descripcion='Test',
            categoria='SOFTWARE',
            estado='NUEVO',
            user_id=user.id,
            evidencia_tipo='MANUAL',
            evidencia_original='evidence',
            fecha_limite_sla=now - timedelta(hours=1),
        )
        session.add(incidente)
        session.commit()

        assert incidente.esta_vencido is True


class TestIncidenteHistorialModel:
    def test_create_historial(self, session):
        user = User(
            username='histuser',
            email='hist@test.com',
            role='admin',
            password=bcrypt.generate_password_hash('test123').decode('utf-8'),
        )
        session.add(user)
        session.flush()

        incidente = Incidente(
            titulo='Hist test',
            descripcion='Test',
            categoria='SOFTWARE',
            estado='NUEVO',
            user_id=user.id,
            evidencia_tipo='MANUAL',
            evidencia_original='evidence',
        )
        session.add(incidente)
        session.flush()

        historial = IncidenteHistorial(
            incidente_id=incidente.id_incidente,
            estado_anterior=None,
            estado_nuevo='NUEVO',
            comentario='Creado',
            changed_by_id=user.id,
        )
        session.add(historial)
        session.commit()

        assert historial.id_historial is not None
        assert historial.estado_nuevo == 'NUEVO'


class TestIncidenteComentarioModel:
    def test_create_comentario(self, session):
        user = User(
            username='comuser',
            email='com@test.com',
            role='admin',
            password=bcrypt.generate_password_hash('test123').decode('utf-8'),
        )
        session.add(user)
        session.flush()

        incidente = Incidente(
            titulo='Com test',
            descripcion='Test',
            categoria='SOFTWARE',
            estado='NUEVO',
            user_id=user.id,
            evidencia_tipo='MANUAL',
            evidencia_original='evidence',
        )
        session.add(incidente)
        session.flush()

        comentario = IncidenteComentario(
            incidente_id=incidente.id_incidente,
            autor_id=user.id,
            contenido='Test comment',
            es_interno=False,
        )
        session.add(comentario)
        session.commit()

        assert comentario.id_comentario is not None
        assert comentario.contenido == 'Test comment'
        assert comentario.es_interno is False
