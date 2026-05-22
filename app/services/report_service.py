
import logging
from datetime import datetime, timedelta, date
from app.models import db, User, Appointment, SessionAudit, WeeklyReport, DailyReport, MonthlyReport, QuarterlyReport

logger = logging.getLogger(__name__)


class ReportService:

    def generate_patient_weekly_report(self, patient_id, therapist_id, week_start_date):
        if isinstance(week_start_date, str):
            week_start = datetime.strptime(week_start_date, '%Y-%m-%d').date()
        else:
            week_start = week_start_date

        week_end = week_start + timedelta(days=6)

        patient = User.query.get(patient_id)
        if not patient:
            raise ValueError(f"Paciente {patient_id} no encontrado")

        week_start_dt = datetime(week_start.year, week_start.month, week_start.day)
        week_end_dt = datetime(week_end.year, week_end.month, week_end.day) + timedelta(days=1)

        sessions = Appointment.query.filter(
            Appointment.patient_id == patient_id,
            Appointment.therapist_id == therapist_id,
            Appointment.start_time >= week_start_dt,
            Appointment.start_time < week_end_dt,
            Appointment.status == 'completed'
        ).order_by(Appointment.start_time.asc()).all()

        sessions_count = len(sessions)

        session_ids = [s.id for s in sessions]
        audits = SessionAudit.query.filter(
            SessionAudit.appointment_id.in_(session_ids),
            SessionAudit.audit_score.isnot(None)
        ).all() if session_ids else []

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
            f"Reporte Semanal - {patient.username}",
            f"Periodo: {week_start.strftime('%d/%m/%Y')} - {week_end.strftime('%d/%m/%Y')}",
            "",
            "--- Resumen ---",
            f"Total de sesiones: {sessions_count}",
            f"Score promedio: {avg_score}%",
        ]
        if objectives_total > 0:
            report_lines.append(f"Objetivos logrados: {objectives_achieved}/{objectives_total}")
        else:
            report_lines.append("Objetivos: N/A")

        report_lines.extend(["", "--- Detalle de Sesiones ---"])
        for s in sessions:
            audit = next((a for a in audits if a.appointment_id == s.id), None)
            score_str = f"Score: {audit.audit_score}%" if audit and audit.audit_score else "Sin auditoria"
            report_lines.append(
                f"- {s.start_time.strftime('%d/%m %H:%M')} | {s.title or 'Sesion'} | {score_str}"
            )

        if audits:
            report_lines.extend([
                "",
                "--- Recomendaciones ---",
                "Continuar con el plan terapeutico segun la programacion establecida."
            ])

        report_text = "\n".join(report_lines)

        report = WeeklyReport.query.filter_by(
            patient_id=patient_id,
            therapist_id=therapist_id,
            week_start=week_start
        ).first()

        if not report:
            report = WeeklyReport(
                patient_id=patient_id,
                therapist_id=therapist_id,
                week_start=week_start,
                week_end=week_end
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
        if isinstance(week_start_date, str):
            week_start = datetime.strptime(week_start_date, '%Y-%m-%d').date()
        else:
            week_start = week_start_date

        report = WeeklyReport.query.filter_by(
            patient_id=patient_id,
            week_start=week_start
        ).first()

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
            report_date = datetime.utcnow().date()
        elif isinstance(report_date, str):
            report_date = datetime.strptime(report_date, '%Y-%m-%d').date()

        day_start = datetime(report_date.year, report_date.month, report_date.day)
        day_end = day_start + timedelta(days=1)

        sessions = Appointment.query.filter(
            Appointment.patient_id == patient_id,
            Appointment.therapist_id == therapist_id,
            Appointment.start_time >= day_start,
            Appointment.start_time < day_end,
            Appointment.status == 'completed'
        ).all()

        session_ids = [s.id for s in sessions]
        audits = SessionAudit.query.filter(
            SessionAudit.appointment_id.in_(session_ids),
            SessionAudit.audit_score.isnot(None)
        ).all() if session_ids else []

        scores = [a.audit_score for a in audits if a.audit_score is not None]
        avg_score = round(sum(scores) / len(scores), 1) if scores else 0.0

        notes_parts = []
        for s in sessions:
            audit = next((a for a in audits if a.appointment_id == s.id), None)
            if audit and audit.audit_score is not None:
                notes_parts.append(f"{s.title or 'Sesion'}: {audit.audit_score}%")

        notes = "; ".join(notes_parts) if notes_parts else "Sin datos"

        report = DailyReport.query.filter_by(
            patient_id=patient_id,
            therapist_id=therapist_id,
            date=report_date
        ).first()

        if not report:
            report = DailyReport(
                patient_id=patient_id,
                therapist_id=therapist_id,
                date=report_date
            )
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

        reports = WeeklyReport.query.filter(
            WeeklyReport.week_start == week_start
        ).all()

        by_therapist = {}
        for r in reports:
            therapist = User.query.get(r.therapist_id)
            patient = User.query.get(r.patient_id)
            tname = therapist.username if therapist else f"ID {r.therapist_id}"
            pname = patient.username if patient else f"ID {r.patient_id}"

            if tname not in by_therapist:
                by_therapist[tname] = {
                    'therapist_id': r.therapist_id,
                    'patients': [],
                    'total_sessions': 0,
                    'avg_score': 0,
                }

            by_therapist[tname]['patients'].append({
                'patient_id': r.patient_id,
                'patient_name': pname,
                'avg_score': r.avg_score,
                'sessions_count': r.sessions_count,
                'objectives_achieved': r.objectives_achieved,
                'objectives_total': r.objectives_total,
            })
            by_therapist[tname]['total_sessions'] += r.sessions_count

        for tname in by_therapist:
            scores = [p['avg_score'] for p in by_therapist[tname]['patients'] if p['avg_score']]
            by_therapist[tname]['avg_score'] = round(sum(scores) / len(scores), 1) if scores else 0

        return {
            'week_start': week_start.isoformat(),
            'week_end': week_end.isoformat(),
            'by_therapist': by_therapist,
            'total_reports': len(reports),
        }

    def get_daily_reports(self, start_date, end_date):
        if isinstance(start_date, str):
            start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
        if isinstance(end_date, str):
            end_date = datetime.strptime(end_date, '%Y-%m-%d').date()

        reports = DailyReport.query.filter(
            DailyReport.date >= start_date,
            DailyReport.date <= end_date
        ).order_by(DailyReport.date.desc()).all()

        result = []
        for r in reports:
            patient = User.query.get(r.patient_id)
            therapist = User.query.get(r.therapist_id)
            result.append({
                'id': r.id,
                'date': r.date.isoformat(),
                'patient_name': patient.username if patient else 'N/A',
                'therapist_name': therapist.username if therapist else 'N/A',
                'sessions_count': r.sessions_count,
                'avg_score': r.avg_score,
                'notes': r.notes,
            })

        return result

    def get_this_week_range(self):
        today = datetime.utcnow().date()
        monday = today - timedelta(days=today.weekday())
        return monday, monday + timedelta(days=6)

    def generate_all_weekly_reports(self, week_start=None):
        if week_start is None:
            week_start, _ = self.get_this_week_range()
        elif isinstance(week_start, str):
            week_start = datetime.strptime(week_start, '%Y-%m-%d').date()

        therapists = User.query.filter_by(role='terapista', is_active=True).all()
        generated = []
        for therapist in therapists:
            patients = therapist.associated_patients.filter_by(role='jugador').all()
            for patient in patients:
                try:
                    report = self.generate_patient_weekly_report(patient.id, therapist.id, week_start)
                    generated.append(report)
                except Exception as e:
                    logger.warning(f"Weekly report error {therapist.id}/{patient.id}: {e}")
        return generated

    def generate_monthly_report(self, patient_id, therapist_id, year, month):
        month_start = date(year, month, 1)
        if month == 12:
            month_end = date(year + 1, 1, 1) - timedelta(days=1)
        else:
            month_end = date(year, month + 1, 1) - timedelta(days=1)

        month_start_dt = datetime(year, month, 1)
        month_end_dt = datetime(year, month_end.year, month_end.month, month_end.day) + timedelta(days=1)

        sessions = Appointment.query.filter(
            Appointment.patient_id == patient_id,
            Appointment.therapist_id == therapist_id,
            Appointment.start_time >= month_start_dt,
            Appointment.start_time < month_end_dt,
            Appointment.status == 'completed'
        ).order_by(Appointment.start_time.asc()).all()

        session_ids = [s.id for s in sessions]
        audits = SessionAudit.query.filter(
            SessionAudit.appointment_id.in_(session_ids),
            SessionAudit.audit_score.isnot(None)
        ).all() if session_ids else []

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
        patient_name = patient.username if patient else f"ID {patient_id}"

        report_lines = [
            f"Reporte Mensual - {patient_name}",
            f"Periodo: {month_start.strftime('%d/%m/%Y')} - {month_end.strftime('%d/%m/%Y')}",
            "",
            "--- Resumen ---",
            f"Total de sesiones: {len(sessions)}",
            f"Score promedio: {avg_score}%",
        ]
        if objectives_total > 0:
            report_lines.append(f"Objetivos logrados: {objectives_achieved}/{objectives_total}")
        else:
            report_lines.append("Objetivos: N/A")
        report_lines.extend(["", "--- Detalle de Sesiones ---"])
        for s in sessions:
            audit = next((a for a in audits if a.appointment_id == s.id), None)
            score_str = f"Score: {audit.audit_score}%" if audit and audit.audit_score else "Sin auditoria"
            report_lines.append(f"- {s.start_time.strftime('%d/%m %H:%M')} | {s.title or 'Sesion'} | {score_str}")
        report_text = "\n".join(report_lines)

        report = MonthlyReport.query.filter_by(
            patient_id=patient_id, therapist_id=therapist_id,
            month=month, year=year
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
            'id': report.id, 'report_text': report_text, 'avg_score': avg_score,
            'sessions_count': len(sessions), 'objectives_achieved': objectives_achieved,
            'objectives_total': objectives_total, 'month': month, 'year': year,
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

        sessions = Appointment.query.filter(
            Appointment.patient_id == patient_id,
            Appointment.therapist_id == therapist_id,
            Appointment.start_time >= quarter_start_dt,
            Appointment.start_time < quarter_end_dt,
            Appointment.status == 'completed'
        ).order_by(Appointment.start_time.asc()).all()

        session_ids = [s.id for s in sessions]
        audits = SessionAudit.query.filter(
            SessionAudit.appointment_id.in_(session_ids),
            SessionAudit.audit_score.isnot(None)
        ).all() if session_ids else []

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
        patient_name = patient.username if patient else f"ID {patient_id}"

        report_lines = [
            f"Reporte Trimestral - {patient_name}",
            f"Periodo: {quarter_start.strftime('%d/%m/%Y')} - {quarter_end.strftime('%d/%m/%Y')}",
            "",
            "--- Resumen ---",
            f"Total de sesiones: {len(sessions)}",
            f"Score promedio: {avg_score}%",
        ]
        if objectives_total > 0:
            report_lines.append(f"Objetivos logrados: {objectives_achieved}/{objectives_total}")
        else:
            report_lines.append("Objetivos: N/A")
        report_lines.extend(["", "--- Detalle de Sesiones ---"])
        for s in sessions:
            audit = next((a for a in audits if a.appointment_id == s.id), None)
            score_str = f"Score: {audit.audit_score}%" if audit and audit.audit_score else "Sin auditoria"
            report_lines.append(f"- {s.start_time.strftime('%d/%m %H:%M')} | {s.title or 'Sesion'} | {score_str}")
        report_text = "\n".join(report_lines)

        report = QuarterlyReport.query.filter_by(
            patient_id=patient_id, therapist_id=therapist_id,
            quarter=quarter, year=year
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
            'id': report.id, 'report_text': report_text, 'avg_score': avg_score,
            'sessions_count': len(sessions), 'objectives_achieved': objectives_achieved,
            'objectives_total': objectives_total, 'quarter': quarter, 'year': year,
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
                    logger.warning(f"Monthly report error {therapist.id}/{patient.id}: {e}")
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
                    logger.warning(f"Quarterly report error {therapist.id}/{patient.id}: {e}")
        return generated

    def get_monthly_summary(self, year, month):
        reports = MonthlyReport.query.filter_by(month=month, year=year).all()
        by_therapist = {}
        for r in reports:
            therapist = User.query.get(r.therapist_id)
            patient = User.query.get(r.patient_id)
            tname = therapist.username if therapist else f"ID {r.therapist_id}"
            pname = patient.username if patient else f"ID {r.patient_id}"
            if tname not in by_therapist:
                by_therapist[tname] = {'therapist_id': r.therapist_id, 'patients': [], 'total_sessions': 0, 'avg_score': 0}
            by_therapist[tname]['patients'].append({
                'patient_id': r.patient_id, 'patient_name': pname,
                'avg_score': r.avg_score, 'sessions_count': r.sessions_count,
                'objectives_achieved': r.objectives_achieved, 'objectives_total': r.objectives_total,
            })
            by_therapist[tname]['total_sessions'] += r.sessions_count
        for tname in by_therapist:
            scores = [p['avg_score'] for p in by_therapist[tname]['patients'] if p['avg_score']]
            by_therapist[tname]['avg_score'] = round(sum(scores) / len(scores), 1) if scores else 0
        return {'month': month, 'year': year, 'by_therapist': by_therapist, 'total_reports': len(reports)}

    def get_quarterly_summary(self, year, quarter):
        reports = QuarterlyReport.query.filter_by(quarter=quarter, year=year).all()
        by_therapist = {}
        for r in reports:
            therapist = User.query.get(r.therapist_id)
            patient = User.query.get(r.patient_id)
            tname = therapist.username if therapist else f"ID {r.therapist_id}"
            pname = patient.username if patient else f"ID {r.patient_id}"
            if tname not in by_therapist:
                by_therapist[tname] = {'therapist_id': r.therapist_id, 'patients': [], 'total_sessions': 0, 'avg_score': 0}
            by_therapist[tname]['patients'].append({
                'patient_id': r.patient_id, 'patient_name': pname,
                'avg_score': r.avg_score, 'sessions_count': r.sessions_count,
                'objectives_achieved': r.objectives_achieved, 'objectives_total': r.objectives_total,
            })
            by_therapist[tname]['total_sessions'] += r.sessions_count
        for tname in by_therapist:
            scores = [p['avg_score'] for p in by_therapist[tname]['patients'] if p['avg_score']]
            by_therapist[tname]['avg_score'] = round(sum(scores) / len(scores), 1) if scores else 0
        return {'quarter': quarter, 'year': year, 'by_therapist': by_therapist, 'total_reports': len(reports)}
