from datetime import UTC, datetime, timedelta

from app.extensions import bcrypt
from app.models.incidente import Incidente
from app.models.user import User
from app.services.incident_escalation_service import IncidentEscalationService


class TestIncidentEscalationService:
    def _create_user(self, session, username, role='admin'):
        user = User(
            username=username,
            email=f'{username}@test.com',
            role=role,
            password=bcrypt.generate_password_hash('test123').decode('utf-8'),
        )
        session.add(user)
        session.commit()
        return user

    def test_sla_deadline_software_p1(self):
        now = datetime.now(UTC)
        deadline = IncidentEscalationService.calculate_sla_deadline('SOFTWARE', 1, now)
        expected = now + timedelta(hours=2)
        assert abs((deadline - expected).total_seconds()) < 60

    def test_sla_deadline_hardware_p3(self):
        now = datetime.now(UTC)
        deadline = IncidentEscalationService.calculate_sla_deadline('HARDWARE', 3, now)
        expected = now + timedelta(hours=24)
        assert abs((deadline - expected).total_seconds()) < 60

    def test_sla_deadline_unknown_category(self):
        now = datetime.now(UTC)
        deadline = IncidentEscalationService.calculate_sla_deadline('UNKNOWN', 1, now)
        expected = now + timedelta(hours=48)
        assert abs((deadline - expected).total_seconds()) < 60

    def test_check_escalations_no_incidents(self, session):
        result = IncidentEscalationService.check_escalations()
        assert isinstance(result, list)

    def test_check_escalations_breached_sla(self, session):
        admin = self._create_user(session, 'escal_admin')
        now = datetime.now(UTC)

        incidente = Incidente(
            titulo='Escalation test',
            descripcion='Testing escalation',
            categoria='SOFTWARE',
            prioridad=1,
            estado='EN_CURSO',
            user_id=admin.id,
            responsable_id=admin.id,
            evidencia_tipo='MANUAL',
            evidencia_original='test',
            fecha_creacion=now - timedelta(hours=5),
            fecha_limite_sla=now - timedelta(hours=3),
            escalamiento_nivel=0,
        )
        session.add(incidente)
        session.commit()

        result = IncidentEscalationService.check_escalations()
        assert len(result) >= 1
        assert result[0]['id_incidente'] == incidente.id_incidente

    def test_max_escalation_limit(self, session):
        admin = self._create_user(session, 'max_escal_admin')
        now = datetime.now(UTC)

        incidente = Incidente(
            titulo='Max escalation test',
            descripcion='Testing max escalation',
            categoria='SOFTWARE',
            prioridad=1,
            estado='PENDIENTE_PROVEEDOR',
            user_id=admin.id,
            responsable_id=admin.id,
            evidencia_tipo='MANUAL',
            evidencia_original='test',
            fecha_creacion=now - timedelta(hours=10),
            fecha_limite_sla=now - timedelta(hours=8),
            escalamiento_nivel=2,
        )
        session.add(incidente)
        session.commit()

        result = IncidentEscalationService.check_escalations()
        for r in result:
            assert r['id_incidente'] != incidente.id_incidente


class TestIncidentDetectionService:
    def test_run_daily_checks(self, session):
        from app.services.incident_detection_service import IncidentDetectionService

        IncidentDetectionService.run_daily_checks()

    def test_run_realtime_checks(self, session):
        from app.services.incident_detection_service import IncidentDetectionService

        IncidentDetectionService.run_realtime_checks()
