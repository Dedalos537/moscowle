import logging
from datetime import UTC, date, datetime, timedelta
from zoneinfo import ZoneInfo

from app.models import Appointment, DailyReport, MonthlyReport, QuarterlyReport, SessionAudit, User, WeeklyReport, db

logger = logging.getLogger(__name__)

LIMA = ZoneInfo('America/Lima')


def utc_bounds(first_day, last_day=None):
    """Inicio y fin (UTC naive, como se guardan las sesiones) de los días locales de Lima indicados.

    Antes se cortaba el día a medianoche UTC: una sesión a las 20:00 en Lima (01:00 UTC del día siguiente) caía en
    el reporte del día equivocado.
    """
    last_day = last_day or first_day
    start = datetime(first_day.year, first_day.month, first_day.day, tzinfo=LIMA)
    end = datetime(last_day.year, last_day.month, last_day.day, tzinfo=LIMA) + timedelta(days=1)
    return start.astimezone(UTC).replace(tzinfo=None), end.astimezone(UTC).replace(tzinfo=None)


def lima_today():
    return datetime.now(LIMA).date()


class ReportService:
    def generate_patient_weekly_report(self, patient_id, therapist_id, week_start_date):
        if isinstance(week_start_date, str):
            week_start = datetime.strptime(week_start_date, '%Y-%m-%d').date()
        else:
            week_start = week_start_date

        week_end = week_start + timedelta(days=6)

        patient = User.query.get(patient_id)
        if not patient:
            raise ValueError(f'Paciente {patient_id} no encontrado')

        week_start_dt, week_end_dt = utc_bounds(week_start, week_end)

        sessions = (
            Appointment.query.filter(
                Appointment.patient_id == patient_id,
                Appointment.therapist_id == therapist_id,
                Appointment.start_time >= week_start_dt,
                Appointment.start_time < week_end_dt,
                Appointment.status == 'completed',
            )
            .order_by(Appointment.start_time.asc())
            .all()
        )

        sessions_count = len(sessions)

        session_ids = [s.id for s in sessions]
        audits = (
            SessionAudit.query.filter(
                SessionAudit.appointment_id.in_(session_ids), SessionAudit.audit_score.isnot(None)
            ).all()
            if session_ids
            else []
        )

        scores = [a.audit_score for a in audits if a.audit_score is not None]
        avg_score = round(sum(scores) / len(scores), 1) if scores else 0.0

        objectives_achieved = 0
        objectives_total = 0
        for a in audits:
            report = a.get_report()
            if report and 'objectives' in report:
                for obj in report['objectives']:
                    objectives_total += 1
                    if obj.get('classification') == 'logrado':
                        objectives_achieved += 1

        report_lines = [
            f'Reporte Semanal - {patient.username}',
            f'Periodo: {week_start.strftime("%d/%m/%Y")} - {week_end.strftime("%d/%m/%Y")}',
            '',
            '--- Resumen ---',
            f'Total de sesiones: {sessions_count}',
            f'Score promedio: {avg_score}%',
        ]
        if objectives_total > 0:
            report_lines.append(f'Objetivos logrados: {objectives_achieved}/{objectives_total}')
        else:
            report_lines.append('Objetivos: N/A')

        report_lines.extend(['', '--- Detalle de Sesiones ---'])
        for s in sessions:
            audit = next((a for a in audits if a.appointment_id == s.id), None)
            score_str = f'Score: {audit.audit_score}%' if audit and audit.audit_score else 'Sin auditoria'
            report_lines.append(f'- {s.start_time.strftime("%d/%m %H:%M")} | {s.title or "Sesion"} | {score_str}')

        if audits:
            report_lines.extend(
                ['', '--- Recomendaciones ---', 'Continuar con el plan terapeutico segun la programacion establecida.']
            )

        report_text = '\n'.join(report_lines)

        report = WeeklyReport.query.filter_by(
            patient_id=patient_id, therapist_id=therapist_id, week_start=week_start
        ).first()

        if not report:
            report = WeeklyReport(
                patient_id=patient_id, therapist_id=therapist_id, week_start=week_start, week_end=week_end
            )
            db.session.add(report)

        report.report_text = report_text
        report.avg_score = avg_score
        report.sessions_count = sessions_count
        report.objectives_achieved = objectives_achieved
        report.objectives_total = objectives_total
        db.session.commit()

        return {
            'id': report.id,
            'report_text': report_text,
            'avg_score': avg_score,
            'sessions_count': sessions_count,
            'objectives_achieved': objectives_achieved,
            'objectives_total': objectives_total,
            'week_start': week_start.isoformat(),
            'week_end': week_end.isoformat(),
        }

    def get_patient_weekly_report(self, patient_id, week_start_date):
        if isinstance(week_start_date, str) and week_start_date:
            week_start = datetime.strptime(week_start_date, '%Y-%m-%d').date()
        else:
            week_start = week_start_date

        if week_start is None:
            # Sin semana: el más reciente. Antes filtraba week_start = NULL y nunca encontraba nada.
            report = (
                WeeklyReport.query.filter_by(patient_id=patient_id).order_by(WeeklyReport.week_start.desc()).first()
            )
        else:
            report = WeeklyReport.query.filter_by(patient_id=patient_id, week_start=week_start).first()

        if not report:
            return None

        return {
            'id': report.id,
            'report_text': report.report_text,
            'avg_score': report.avg_score,
            'sessions_count': report.sessions_count,
            'objectives_achieved': report.objectives_achieved,
            'objectives_total': report.objectives_total,
            'week_start': report.week_start.isoformat(),
            'week_end': report.week_end.isoformat(),
            'created_at': report.created_at.isoformat() if report.created_at else None,
        }

    def generate_daily_report(self, patient_id, therapist_id, report_date=None):
        if report_date is None:
            report_date = lima_today()
        elif isinstance(report_date, str):
            report_date = datetime.strptime(report_date, '%Y-%m-%d').date()

        day_start, day_end = utc_bounds(report_date)

        sessions = Appointment.query.filter(
            Appointment.patient_id == patient_id,
            Appointment.therapist_id == therapist_id,
            Appointment.start_time >= day_start,
            Appointment.start_time < day_end,
            Appointment.status == 'completed',
        ).all()

        session_ids = [s.id for s in sessions]
        audits = (
            SessionAudit.query.filter(
                SessionAudit.appointment_id.in_(session_ids), SessionAudit.audit_score.isnot(None)
            ).all()
            if session_ids
            else []
        )

        scores = [a.audit_score for a in audits if a.audit_score is not None]
        avg_score = round(sum(scores) / len(scores), 1) if scores else 0.0

        notes_parts = []
        for s in sessions:
            audit = next((a for a in audits if a.appointment_id == s.id), None)
            if audit and audit.audit_score is not None:
                notes_parts.append(f'{s.title or "Sesion"}: {audit.audit_score}%')

        notes = '; '.join(notes_parts) if notes_parts else 'Sin datos'

        report = DailyReport.query.filter_by(patient_id=patient_id, therapist_id=therapist_id, date=report_date).first()

        if not report:
            report = DailyReport(patient_id=patient_id, therapist_id=therapist_id, date=report_date)
            db.session.add(report)

        report.sessions_count = len(sessions)
        report.avg_score = avg_score
        report.notes = notes
        db.session.commit()

        return {
            'id': report.id,
            'date': report_date.isoformat(),
            'sessions_count': report.sessions_count,
            'avg_score': avg_score,
            'notes': notes,
        }

    def get_weekly_summary(self, week_start_date):
        if isinstance(week_start_date, str):
            week_start = datetime.strptime(week_start_date, '%Y-%m-%d').date()
        else:
            week_start = week_start_date

        week_end = week_start + timedelta(days=6)

        reports = WeeklyReport.query.filter(WeeklyReport.week_start == week_start).all()

        by_therapist = {}
        for r in reports:
            therapist = User.query.get(r.therapist_id)
            patient = User.query.get(r.patient_id)
            tname = therapist.username if therapist else f'ID {r.therapist_id}'
            pname = patient.username if patient else f'ID {r.patient_id}'

            if tname not in by_therapist:
                by_therapist[tname] = {
                    'therapist_id': r.therapist_id,
                    'patients': [],
                    'total_sessions': 0,
                    'avg_score': 0,
                }

            by_therapist[tname]['patients'].append(
                {
                    'patient_id': r.patient_id,
                    'patient_name': pname,
                    'avg_score': r.avg_score,
                    'sessions_count': r.sessions_count,
                    'objectives_achieved': r.objectives_achieved,
                    'objectives_total': r.objectives_total,
                }
            )
            by_therapist[tname]['total_sessions'] += r.sessions_count

        for _tname, tdata in by_therapist.items():
            scores = [p['avg_score'] for p in tdata['patients'] if p['avg_score']]
            tdata['avg_score'] = round(sum(scores) / len(scores), 1) if scores else 0

        return {
            'week_start': week_start.isoformat(),
            'week_end': week_end.isoformat(),
            'by_therapist': by_therapist,
            'total_reports': len(reports),
        }

    def sync_daily_reports_for_range(self, start_date, end_date):
        """Genera o actualiza reportes diarios a partir de sesiones completadas."""
        if isinstance(start_date, str):
            start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
        if isinstance(end_date, str):
            end_date = datetime.strptime(end_date, '%Y-%m-%d').date()

        if start_date > end_date:
            start_date, end_date = end_date, start_date

        current = start_date
        while current <= end_date:
            day_start, day_end = utc_bounds(current)

            pairs = (
                db.session.query(Appointment.patient_id, Appointment.therapist_id)
                .filter(
                    Appointment.start_time >= day_start,
                    Appointment.start_time < day_end,
                    Appointment.status == 'completed',
                )
                .distinct()
                .all()
            )

            for patient_id, therapist_id in pairs:
                try:
                    self.generate_daily_report(patient_id, therapist_id, current)
                except Exception as e:
                    logger.warning(
                        'Error sincronizando reporte diario %s/%s %s: %s',
                        therapist_id,
                        patient_id,
                        current,
                        e,
                    )

            current += timedelta(days=1)

        return self.get_daily_reports(start_date, end_date)

    def get_daily_reports(self, start_date, end_date):
        if isinstance(start_date, str):
            start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
        if isinstance(end_date, str):
            end_date = datetime.strptime(end_date, '%Y-%m-%d').date()

        reports = (
            DailyReport.query.filter(DailyReport.date >= start_date, DailyReport.date <= end_date)
            .order_by(DailyReport.date.desc())
            .all()
        )

        result = []
        for r in reports:
            patient = User.query.get(r.patient_id)
            therapist = User.query.get(r.therapist_id)
            result.append(
                {
                    'id': r.id,
                    'date': r.date.isoformat(),
                    'patient_name': patient.username if patient else 'N/A',
                    'therapist_name': therapist.username if therapist else 'N/A',
                    'sessions_count': r.sessions_count,
                    'avg_score': r.avg_score,
                    'notes': r.notes,
                }
            )

        return result

    def get_this_week_range(self):
        today = lima_today()
        monday = today - timedelta(days=today.weekday())
        return monday, monday + timedelta(days=6)

    def generate_all_weekly_reports(self, week_start=None):
        if week_start is None:
            week_start, _ = self.get_this_week_range()
        elif isinstance(week_start, str):
            week_start = datetime.strptime(week_start, '%Y-%m-%d').date()

        generated = []
        for patient_id, therapist_id in self._pairs_with_sessions(week_start, week_start + timedelta(days=6)):
            try:
                generated.append(self.generate_patient_weekly_report(patient_id, therapist_id, week_start))
            except Exception as e:
                logger.warning(f'Weekly report error {therapist_id}/{patient_id}: {e}')
        return generated

    def _pairs_with_sessions(self, first_day, last_day):
        """Pares (paciente, terapeuta) con sesiones completadas en esos días.

        Antes se partía de los pacientes «asociados» a cada terapeuta y se saltaban sesiones de grupo, de pacientes
        reasignados o de terapeutas de reemplazo.
        """
        start, end = utc_bounds(first_day, last_day)
        return (
            db.session.query(Appointment.patient_id, Appointment.therapist_id)
            .filter(
                Appointment.start_time >= start,
                Appointment.start_time < end,
                Appointment.status == 'completed',
                Appointment.patient_id.isnot(None),
                Appointment.therapist_id.isnot(None),
            )
            .distinct()
            .all()
        )

    def accumulate_week(self, week_start=None):
        """Acumula una semana: reportes diarios de cada día con sesiones y el semanal de cada paciente–terapeuta."""
        if week_start is None:
            week_start, _ = self.get_this_week_range()
        elif isinstance(week_start, str):
            week_start = datetime.strptime(week_start, '%Y-%m-%d').date()
        week_start = week_start - timedelta(days=week_start.weekday())  # siempre desde el lunes
        last_day = min(week_start + timedelta(days=6), lima_today())
        if last_day < week_start:
            return {'week_start': week_start.isoformat(), 'daily': 0, 'weekly': 0, 'pairs': 0}
        daily = self.sync_daily_reports_for_range(week_start, last_day)
        pairs = self._pairs_with_sessions(week_start, last_day)
        weekly = 0
        for patient_id, therapist_id in pairs:
            try:
                self.generate_patient_weekly_report(patient_id, therapist_id, week_start)
                weekly += 1
            except Exception as e:
                logger.warning('Acumulado semanal %s/%s falló: %s', therapist_id, patient_id, e)
        return {'week_start': week_start.isoformat(), 'daily': len(daily), 'weekly': weekly, 'pairs': len(pairs)}

    def generate_monthly_report(self, patient_id, therapist_id, year, month):
        month_start = date(year, month, 1)
        if month == 12:
            month_end = date(year + 1, 1, 1) - timedelta(days=1)
        else:
            month_end = date(year, month + 1, 1) - timedelta(days=1)

        month_start_dt = datetime(year, month, 1)
        month_end_dt = datetime(year, month_end.year, month_end.month, month_end.day) + timedelta(days=1)

        sessions = (
            Appointment.query.filter(
                Appointment.patient_id == patient_id,
                Appointment.therapist_id == therapist_id,
                Appointment.start_time >= month_start_dt,
                Appointment.start_time < month_end_dt,
                Appointment.status == 'completed',
            )
            .order_by(Appointment.start_time.asc())
            .all()
        )

        session_ids = [s.id for s in sessions]
        audits = (
            SessionAudit.query.filter(
                SessionAudit.appointment_id.in_(session_ids), SessionAudit.audit_score.isnot(None)
            ).all()
            if session_ids
            else []
        )

        scores = [a.audit_score for a in audits if a.audit_score is not None]
        avg_score = round(sum(scores) / len(scores), 1) if scores else 0.0

        objectives_achieved = 0
        objectives_total = 0
        for a in audits:
            report = a.get_report()
            if report and 'objectives' in report:
                for obj in report['objectives']:
                    objectives_total += 1
                    if obj.get('classification') == 'logrado':
                        objectives_achieved += 1

        patient = User.query.get(patient_id)
        patient_name = patient.username if patient else f'ID {patient_id}'

        report_lines = [
            f'Reporte Mensual - {patient_name}',
            f'Periodo: {month_start.strftime("%d/%m/%Y")} - {month_end.strftime("%d/%m/%Y")}',
            '',
            '--- Resumen ---',
            f'Total de sesiones: {len(sessions)}',
            f'Score promedio: {avg_score}%',
        ]
        if objectives_total > 0:
            report_lines.append(f'Objetivos logrados: {objectives_achieved}/{objectives_total}')
        else:
            report_lines.append('Objetivos: N/A')
        report_lines.extend(['', '--- Detalle de Sesiones ---'])
        for s in sessions:
            audit = next((a for a in audits if a.appointment_id == s.id), None)
            score_str = f'Score: {audit.audit_score}%' if audit and audit.audit_score else 'Sin auditoria'
            report_lines.append(f'- {s.start_time.strftime("%d/%m %H:%M")} | {s.title or "Sesion"} | {score_str}')
        report_text = '\n'.join(report_lines)

        report = MonthlyReport.query.filter_by(
            patient_id=patient_id, therapist_id=therapist_id, month=month, year=year
        ).first()
        if not report:
            report = MonthlyReport(patient_id=patient_id, therapist_id=therapist_id, month=month, year=year)
            db.session.add(report)
        report.sessions_count = len(sessions)
        report.avg_score = avg_score
        report.objectives_achieved = objectives_achieved
        report.objectives_total = objectives_total
        report.report_text = report_text
        db.session.commit()

        return {
            'id': report.id,
            'report_text': report_text,
            'avg_score': avg_score,
            'sessions_count': len(sessions),
            'objectives_achieved': objectives_achieved,
            'objectives_total': objectives_total,
            'month': month,
            'year': year,
        }

    def generate_quarterly_report(self, patient_id, therapist_id, year, quarter):
        month_start = (quarter - 1) * 3 + 1
        quarter_start = date(year, month_start, 1)
        if quarter == 4:
            quarter_end = date(year, 12, 31)
        else:
            quarter_end = date(year, month_start + 3, 1) - timedelta(days=1)

        quarter_start_dt = datetime(year, quarter_start.month, 1)
        quarter_end_dt = datetime(quarter_end.year, quarter_end.month, quarter_end.day) + timedelta(days=1)

        sessions = (
            Appointment.query.filter(
                Appointment.patient_id == patient_id,
                Appointment.therapist_id == therapist_id,
                Appointment.start_time >= quarter_start_dt,
                Appointment.start_time < quarter_end_dt,
                Appointment.status == 'completed',
            )
            .order_by(Appointment.start_time.asc())
            .all()
        )

        session_ids = [s.id for s in sessions]
        audits = (
            SessionAudit.query.filter(
                SessionAudit.appointment_id.in_(session_ids), SessionAudit.audit_score.isnot(None)
            ).all()
            if session_ids
            else []
        )

        scores = [a.audit_score for a in audits if a.audit_score is not None]
        avg_score = round(sum(scores) / len(scores), 1) if scores else 0.0

        objectives_achieved = 0
        objectives_total = 0
        for a in audits:
            report = a.get_report()
            if report and 'objectives' in report:
                for obj in report['objectives']:
                    objectives_total += 1
                    if obj.get('classification') == 'logrado':
                        objectives_achieved += 1

        patient = User.query.get(patient_id)
        patient_name = patient.username if patient else f'ID {patient_id}'

        report_lines = [
            f'Reporte Trimestral - {patient_name}',
            f'Periodo: {quarter_start.strftime("%d/%m/%Y")} - {quarter_end.strftime("%d/%m/%Y")}',
            '',
            '--- Resumen ---',
            f'Total de sesiones: {len(sessions)}',
            f'Score promedio: {avg_score}%',
        ]
        if objectives_total > 0:
            report_lines.append(f'Objetivos logrados: {objectives_achieved}/{objectives_total}')
        else:
            report_lines.append('Objetivos: N/A')
        report_lines.extend(['', '--- Detalle de Sesiones ---'])
        for s in sessions:
            audit = next((a for a in audits if a.appointment_id == s.id), None)
            score_str = f'Score: {audit.audit_score}%' if audit and audit.audit_score else 'Sin auditoria'
            report_lines.append(f'- {s.start_time.strftime("%d/%m %H:%M")} | {s.title or "Sesion"} | {score_str}')
        report_text = '\n'.join(report_lines)

        report = QuarterlyReport.query.filter_by(
            patient_id=patient_id, therapist_id=therapist_id, quarter=quarter, year=year
        ).first()
        if not report:
            report = QuarterlyReport(patient_id=patient_id, therapist_id=therapist_id, quarter=quarter, year=year)
            db.session.add(report)
        report.sessions_count = len(sessions)
        report.avg_score = avg_score
        report.objectives_achieved = objectives_achieved
        report.objectives_total = objectives_total
        report.report_text = report_text
        db.session.commit()

        return {
            'id': report.id,
            'report_text': report_text,
            'avg_score': avg_score,
            'sessions_count': len(sessions),
            'objectives_achieved': objectives_achieved,
            'objectives_total': objectives_total,
            'quarter': quarter,
            'year': year,
        }

    def generate_all_monthly_reports(self, year, month):
        therapists = User.query.filter_by(role='terapista', is_active=True).all()
        generated = []
        for therapist in therapists:
            patients = therapist.associated_patients.filter_by(role='jugador').all()
            for patient in patients:
                try:
                    report = self.generate_monthly_report(patient.id, therapist.id, year, month)
                    generated.append(report)
                except Exception as e:
                    logger.warning(f'Monthly report error {therapist.id}/{patient.id}: {e}')
        return generated

    def generate_all_quarterly_reports(self, year, quarter):
        therapists = User.query.filter_by(role='terapista', is_active=True).all()
        generated = []
        for therapist in therapists:
            patients = therapist.associated_patients.filter_by(role='jugador').all()
            for patient in patients:
                try:
                    report = self.generate_quarterly_report(patient.id, therapist.id, year, quarter)
                    generated.append(report)
                except Exception as e:
                    logger.warning(f'Quarterly report error {therapist.id}/{patient.id}: {e}')
        return generated

    def get_monthly_summary(self, year, month):
        reports = MonthlyReport.query.filter_by(month=month, year=year).all()
        by_therapist = {}
        for r in reports:
            therapist = User.query.get(r.therapist_id)
            patient = User.query.get(r.patient_id)
            tname = therapist.username if therapist else f'ID {r.therapist_id}'
            pname = patient.username if patient else f'ID {r.patient_id}'
            if tname not in by_therapist:
                by_therapist[tname] = {
                    'therapist_id': r.therapist_id,
                    'patients': [],
                    'total_sessions': 0,
                    'avg_score': 0,
                }
            by_therapist[tname]['patients'].append(
                {
                    'patient_id': r.patient_id,
                    'patient_name': pname,
                    'avg_score': r.avg_score,
                    'sessions_count': r.sessions_count,
                    'objectives_achieved': r.objectives_achieved,
                    'objectives_total': r.objectives_total,
                }
            )
            by_therapist[tname]['total_sessions'] += r.sessions_count
        for _tname, tdata in by_therapist.items():
            scores = [p['avg_score'] for p in tdata['patients'] if p['avg_score']]
            tdata['avg_score'] = round(sum(scores) / len(scores), 1) if scores else 0
        return {'month': month, 'year': year, 'by_therapist': by_therapist, 'total_reports': len(reports)}

    def get_quarterly_summary(self, year, quarter):
        reports = QuarterlyReport.query.filter_by(quarter=quarter, year=year).all()
        by_therapist = {}
        for r in reports:
            therapist = User.query.get(r.therapist_id)
            patient = User.query.get(r.patient_id)
            tname = therapist.username if therapist else f'ID {r.therapist_id}'
            pname = patient.username if patient else f'ID {r.patient_id}'
            if tname not in by_therapist:
                by_therapist[tname] = {
                    'therapist_id': r.therapist_id,
                    'patients': [],
                    'total_sessions': 0,
                    'avg_score': 0,
                }
            by_therapist[tname]['patients'].append(
                {
                    'patient_id': r.patient_id,
                    'patient_name': pname,
                    'avg_score': r.avg_score,
                    'sessions_count': r.sessions_count,
                    'objectives_achieved': r.objectives_achieved,
                    'objectives_total': r.objectives_total,
                }
            )
            by_therapist[tname]['total_sessions'] += r.sessions_count
        for _tname, tdata in by_therapist.items():
            scores = [p['avg_score'] for p in tdata['patients'] if p['avg_score']]
            tdata['avg_score'] = round(sum(scores) / len(scores), 1) if scores else 0
        return {'quarter': quarter, 'year': year, 'by_therapist': by_therapist, 'total_reports': len(reports)}
