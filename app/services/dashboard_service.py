from datetime import UTC, datetime, timedelta

from app.repositories.appointment_repository import AppointmentRepository
from app.repositories.metrics_repository import MetricsRepository
from app.repositories.user_repository import UserRepository
from app.utils import get_user_timezone, get_user_today_utc_range


class DashboardService:
    def __init__(self):
        self.user_repo = UserRepository()
        self.metrics_repo = MetricsRepository()
        self.appointment_repo = AppointmentRepository()

    def get_admin_overview(self):
        therapists = self.user_repo.count_by_role('terapista')
        patients = self.user_repo.count_by_role('jugador')
        sessions_total = self.appointment_repo.count_total()
        avg_acc = self.metrics_repo.get_global_avg_accuracy()

        from sqlalchemy import func

        from app.extensions import db
        from app.models import SessionAudit

        avg_audit = (
            db.session.query(func.avg(SessionAudit.audit_score))
            .filter(SessionAudit.audit_status == 'completed', SessionAudit.audit_score.isnot(None))
            .scalar()
            or 0
        )
        audits_count = SessionAudit.query.filter(
            SessionAudit.audit_status == 'completed', SessionAudit.audit_score.isnot(None)
        ).count()

        return {
            'therapists': therapists,
            'patients': patients,
            'sessions_total': sessions_total,
            'avg_accuracy': round(avg_acc, 1),
            'avg_audit_compliance': round(float(avg_audit), 1),
            'audits_count': audits_count,
        }

    def get_therapist_stats(self, therapist_id):
        active_patients = self.user_repo.count_active_patients_by_therapist(therapist_id)
        total_sessions = self.appointment_repo.count_by_therapist(therapist_id)
        ia_precision = round(self.metrics_repo.get_avg_accuracy_by_therapist(therapist_id), 1)

        now = datetime.utcnow()
        last_30 = now - timedelta(days=30)
        prev_60 = now - timedelta(days=60)

        avg_last_30 = self.metrics_repo.get_avg_accuracy_by_therapist_date_range(therapist_id, last_30)
        avg_prev_30 = self.metrics_repo.get_avg_accuracy_by_therapist_date_range(therapist_id, prev_60, last_30)

        if avg_last_30 and avg_prev_30 and avg_prev_30 != 0:
            improvement_rate = round(((avg_last_30 - avg_prev_30) / avg_prev_30) * 100, 1)
        else:
            improvement_rate = 0

        return {
            'active_patients': active_patients,
            'total_sessions': total_sessions,
            'ia_precision': ia_precision,
            'improvement_rate': improvement_rate,
        }

    def get_therapist_patients_data(self, therapist_id):
        patients_query = self.user_repo.get_active_patients_by_therapist(therapist_id)
        patients_data = []

        for p in patients_query:
            metrics = self.metrics_repo.get_recent_metrics_by_user(p.id, limit=10)
            sessions_count = self.metrics_repo.count_sessions_by_user(p.id)

            if metrics:
                acc_list = [m.accurracy for m in metrics]
                avg_time_list = [m.avg_time for m in metrics]
                avg_acc = round(sum(acc_list) / len(acc_list), 1)
                avg_time = round(sum(avg_time_list) / len(avg_time_list), 1)

                patients_data.append(
                    {
                        'avatar': f'https://ui-avatars.com/api/?name={(p.username or "User").replace(" ", "+")}&background=random',
                        'name': p.username or 'Usuario',
                        'ptid': p.id,
                        'game': metrics[0].game_name,
                        'level': metrics[0].prediction,
                        'accuracy': avg_acc,
                        'avg_time': avg_time,
                        'sessions': sessions_count,
                        'prediction_code': metrics[0].prediction,
                    }
                )
            else:
                patients_data.append(
                    {
                        'avatar': f'https://ui-avatars.com/api/?name={(p.username or "User").replace(" ", "+")}&background=random',
                        'name': p.username or 'Usuario',
                        'ptid': p.id,
                        'game': 'Sin actividad',
                        'level': 0,
                        'accuracy': 0,
                        'avg_time': 0,
                        'sessions': 0,
                        'prediction_code': 0,
                    }
                )

        return sorted(patients_data, key=lambda x: x['sessions'], reverse=True)[:5]

    def get_therapist_insights(self, user=None):
        from sqlalchemy import func

        from app.models import SessionMetrics, User, db

        patient_ids = []
        if user and user.role == 'terapista':
            patient_ids = [p.id for p in self.user_repo.get_active_patients_by_therapist(user.id)]

        if user:
            today_start, _ = get_user_today_utc_range(user)
            today = today_start.date()
        else:
            today = datetime.utcnow().date()

        days = [today - timedelta(days=i) for i in range(6, -1, -1)]
        series = []

        for d in days:
            day_start = datetime(d.year, d.month, d.day)

            if user:
                tz = get_user_timezone(user)
                try:
                    local_dt = datetime.combine(d, datetime.min.time())
                    local_dt = local_dt.replace(tzinfo=tz)
                    day_start = local_dt.astimezone(UTC).replace(tzinfo=None)
                except Exception:
                    pass

            day_end = day_start + timedelta(days=1)

            query = db.session.query(func.avg(SessionMetrics.accurracy)).filter(
                SessionMetrics.date >= day_start, SessionMetrics.date < day_end
            )

            if patient_ids:
                query = query.filter(SessionMetrics.user_id.in_(patient_ids))
            elif user and user.role == 'terapista':
                query = None

            avg_acc = 0
            if query:
                avg_acc = query.scalar() or 0

            series.append({'date': d.strftime('%Y-%m-%d'), 'avg_accuracy': round(avg_acc, 2)})

        seven_days_ago = datetime.utcnow() - timedelta(days=7)
        alerts_query = SessionMetrics.query.filter(
            SessionMetrics.date >= seven_days_ago, SessionMetrics.prediction == 2
        )

        if patient_ids:
            alerts_query = alerts_query.filter(SessionMetrics.user_id.in_(patient_ids))

        risky = alerts_query.order_by(SessionMetrics.date.desc()).limit(5).all()

        alerts = []
        for r in risky:
            u = User.query.get(r.user_id)
            if u:
                alerts.append(
                    {
                        'type': 'red',
                        'patient': (u.username or u.email),
                        'message': f'Baja precisión ({int(r.accurracy)}%) en {r.game_name}. Sugerido apoyo.',
                    }
                )

        return {'weekly_progress': series, 'alerts': alerts}

    def get_therapist_dashboard_data(self, user):
        """Datos completos del dashboard terapeuta (sin valores hardcodeados en frontend)."""
        from sqlalchemy import func as sqlfunc

        from app.extensions import db
        from app.models import Appointment, SessionAudit, User
        from app.utils import get_user_now, get_user_today_utc_range, localize_datetime_for_display

        now_utc = datetime.utcnow()
        today_start, today_end = get_user_today_utc_range(user)
        tz_name = user.timezone or 'America/Lima'
        user_now = get_user_now(user)

        today_sessions = (
            Appointment.query.filter(
                Appointment.therapist_id == user.id,
                Appointment.start_time >= today_start,
                Appointment.start_time < today_end,
                Appointment.status != 'cancelled',
            )
            .order_by(Appointment.start_time)
            .all()
        )

        agenda = []
        next_session = None
        active_session = None

        for s in today_sessions:
            patient = User.query.get(s.patient_id) if s.patient_id else None
            local_start = localize_datetime_for_display(s.start_time, tz_name)
            is_current = s.start_time <= now_utc and (s.end_time is None or s.end_time > now_utc)
            session_info = {
                'id': s.id,
                'title': s.title or 'Sesión de Terapia',
                'patient': patient.username if patient else 'N/A',
                'start': local_start.strftime('%I:%M %p') if local_start else '',
                'location': s.location or '',
                'status': s.status,
                'is_current': is_current,
            }
            agenda.append(session_info)
            if is_current:
                active_session = session_info
            if not next_session and (is_current or s.start_time > now_utc):
                next_session = session_info

        if not next_session and active_session:
            next_session = active_session

        audit = None
        if next_session:
            audit = SessionAudit.query.filter_by(appointment_id=next_session['id']).first()

        session_topics = self._build_session_topics(next_session, audit)
        session_progress = int(audit.audit_score) if audit and audit.audit_score else 0
        progress_meta = self._session_progress_meta(next_session, audit, session_progress)

        avg_compliance = (
            db.session.query(sqlfunc.avg(SessionAudit.audit_score))
            .join(Appointment, SessionAudit.appointment_id == Appointment.id)
            .filter(Appointment.therapist_id == user.id, SessionAudit.audit_score.isnot(None))
            .scalar()
            or 0
        )
        avg_compliance = max(0, round(float(avg_compliance), 1))

        academic_progress = self._academic_progress_delta(user.id)
        weekly_progress = self._weekly_audit_progress(user.id, today_start)
        pending_reports = self._pending_reports_summary(user.id)
        ai_coach = self._ai_coach_summary(user.id)

        months_es = ['ENE', 'FEB', 'MAR', 'ABR', 'MAY', 'JUN', 'JUL', 'AGO', 'SEP', 'OCT', 'NOV', 'DIC']
        today_label = f'{user_now.day} {months_es[user_now.month - 1]}'

        return {
            'next_session': next_session,
            'agenda': agenda,
            'today_label': today_label,
            'avg_compliance': avg_compliance,
            'session_topics': session_topics,
            'session_progress': session_progress,
            'weekly_progress': weekly_progress,
            'progress': progress_meta,
            'pending_reports': pending_reports,
            'academic_progress': academic_progress,
            'ai_coach': ai_coach,
            'total_students': len({s.patient_id for s in today_sessions if s.patient_id}),
        }

    def _build_session_topics(self, next_session, audit):
        from app.utils.objectives import enrich_objectives_from_audit, objective_status_to_ui, parse_objectives

        if not next_session:
            return {
                'items': [],
                'empty_state': {
                    'reason': 'no_session_today',
                    'message': 'Sin sesión programada hoy',
                    'hint': 'Revisa tu calendario para ver las próximas citas.',
                },
            }

        if not audit or not audit.planned_text:
            return {
                'items': [],
                'empty_state': {
                    'reason': 'no_programming',
                    'message': 'Programación no subida',
                    'hint': f'Sube el documento .docx en Revisión de sesión (ID {next_session["id"]}).',
                },
            }

        objectives = parse_objectives(audit.planned_text)
        if audit.audit_status == 'completed':
            enrich_objectives_from_audit(objectives, audit.audit_report_json)

        if not objectives:
            return {
                'items': [],
                'empty_state': {
                    'reason': 'no_objectives_parsed',
                    'message': 'No se detectaron objetivos en la programación',
                    'hint': 'Usa encabezados ## o viñetas (-) en el Word para que se listen aquí.',
                },
            }

        items = []
        for obj in objectives:
            code, label = objective_status_to_ui(obj.get('status', 'pendiente'))
            items.append({'name': obj['name'], 'status': code, 'status_label': label})

        empty_state = None
        if audit.audit_status != 'completed':
            empty_state = {
                'reason': 'awaiting_audit',
                'message': None,
                'hint': 'Los estados se actualizan al completar la grabación y la auditoría IA.',
            }

        return {'items': items, 'empty_state': empty_state}

    def _session_progress_meta(self, next_session, audit, score):
        if not next_session:
            return {
                'label': 'Cobertura de sesión',
                'weekly_label': 'Meta semanal',
                'description': 'No hay sesión activa programada para hoy.',
            }
        if not audit or not audit.planned_text:
            return {
                'label': 'Cobertura de sesión',
                'weekly_label': 'Meta semanal',
                'description': 'Sube la programación (.docx) para habilitar el seguimiento.',
            }
        if not audit.transcript_text:
            return {
                'label': 'Cobertura de sesión',
                'weekly_label': 'Meta semanal',
                'description': 'Inicia la grabación de la sesión para transcribir el audio.',
            }
        if audit.audit_status == 'processing':
            return {
                'label': 'Cobertura de sesión',
                'weekly_label': 'Meta semanal',
                'description': 'Auditoría en proceso, espera unos segundos.',
            }
        if audit.audit_status == 'error':
            return {
                'label': 'Cobertura de sesión',
                'weekly_label': 'Meta semanal',
                'description': 'La auditoría falló. Reinténtala desde Revisión de sesión.',
            }
        if audit.audit_status != 'completed':
            return {
                'label': 'Cobertura de sesión',
                'weekly_label': 'Meta semanal',
                'description': 'Ejecuta la auditoría IA para medir cobertura del plan.',
            }
        if score >= 80:
            desc = 'Excelente avance respecto a la programación planificada.'
        elif score >= 50:
            desc = 'Buen progreso; parte del plan quedó pendiente.'
        elif score > 0:
            desc = 'Cobertura parcial del plan de sesión.'
        else:
            desc = 'Auditoría completada sin puntuación registrada.'
        return {'label': 'Cobertura de sesión', 'weekly_label': 'Meta semanal', 'description': desc}

    def _weekly_audit_progress(self, therapist_id, week_start_utc):
        from app.models import Appointment, SessionAudit

        week_end_utc = week_start_utc + timedelta(days=7)
        completed = Appointment.query.filter(
            Appointment.therapist_id == therapist_id,
            Appointment.status == 'completed',
            Appointment.start_time >= week_start_utc,
            Appointment.start_time < week_end_utc,
        ).count()
        if completed == 0:
            return {'percent': 0, 'completed_sessions': 0, 'audited_sessions': 0}

        audited = (
            SessionAudit.query.join(Appointment, SessionAudit.appointment_id == Appointment.id)
            .filter(
                Appointment.therapist_id == therapist_id,
                Appointment.status == 'completed',
                Appointment.start_time >= week_start_utc,
                Appointment.start_time < week_end_utc,
                SessionAudit.audit_status == 'completed',
            )
            .count()
        )
        percent = round((audited / completed) * 100)
        return {'percent': percent, 'completed_sessions': completed, 'audited_sessions': audited}

    def _pending_reports_summary(self, therapist_id):
        from sqlalchemy import or_

        from app.models import Appointment, SessionAudit

        cutoff = datetime.utcnow() - timedelta(days=30)
        pending_count = (
            Appointment.query.outerjoin(SessionAudit, SessionAudit.appointment_id == Appointment.id)
            .filter(
                Appointment.therapist_id == therapist_id,
                Appointment.status == 'completed',
                Appointment.start_time >= cutoff,
                or_(
                    SessionAudit.id.is_(None),
                    SessionAudit.planned_text.is_(None),
                    SessionAudit.transcript_text.is_(None),
                    SessionAudit.audit_status != 'completed',
                ),
            )
            .count()
        )
        badge = None
        if pending_count >= 3:
            badge = 'Prioridad alta'
        elif pending_count > 0:
            badge = 'Revisar'
        return {
            'count': pending_count,
            'label': 'Sesiones completadas sin cierre de auditoría',
            'badge': badge,
        }

    def _academic_progress_delta(self, therapist_id):
        from sqlalchemy import func as sqlfunc

        from app.extensions import db
        from app.models import Appointment, SessionAudit

        now = datetime.utcnow()
        this_month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        if this_month_start.month == 1:
            last_month_start = this_month_start.replace(year=this_month_start.year - 1, month=12)
        else:
            last_month_start = this_month_start.replace(month=this_month_start.month - 1)

        def _avg_since(start, end=None):
            q = (
                db.session.query(sqlfunc.avg(SessionAudit.audit_score))
                .join(Appointment, SessionAudit.appointment_id == Appointment.id)
                .filter(
                    Appointment.therapist_id == therapist_id,
                    SessionAudit.audit_score.isnot(None),
                    Appointment.start_time >= start,
                )
            )
            if end:
                q = q.filter(Appointment.start_time < end)
            val = q.scalar()
            return round(float(val), 1) if val else None

        avg_this = _avg_since(this_month_start)
        avg_last = _avg_since(last_month_start, this_month_start)

        delta = 0.0
        if avg_this is not None and avg_last is not None:
            delta = round(avg_this - avg_last, 1)
        elif avg_this is not None:
            delta = avg_this

        month_names = [
            'Enero',
            'Febrero',
            'Marzo',
            'Abril',
            'Mayo',
            'Junio',
            'Julio',
            'Agosto',
            'Septiembre',
            'Octubre',
            'Noviembre',
            'Diciembre',
        ]
        return {
            'delta': delta,
            'avg_this_month': avg_this,
            'label': month_names[now.month - 1],
            'subtitle': 'Cumplimiento promedio de auditorías',
        }

    def _ai_coach_summary(self, therapist_id):
        from app.models import Appointment, SessionAudit

        cutoff = datetime.utcnow() - timedelta(days=14)
        audits = (
            SessionAudit.query.join(Appointment, SessionAudit.appointment_id == Appointment.id)
            .filter(
                Appointment.therapist_id == therapist_id,
                SessionAudit.audit_status == 'completed',
                SessionAudit.audited_at >= cutoff,
            )
            .order_by(SessionAudit.audited_at.desc())
            .limit(10)
            .all()
        )
        tips = []
        seen = set()
        for audit in audits:
            report = audit.get_report()
            for rec in report.get('recommendations') or []:
                text = (rec or '').strip()
                if text and text.lower() not in seen:
                    seen.add(text.lower())
                    tips.append(text)
        count = len(tips)
        return {
            'count': count,
            'label': 'Recomendaciones de auditorías recientes' if count else 'Sin recomendaciones nuevas',
            'badge': f'{count} sugerencia{"s" if count != 1 else ""}' if count else None,
        }

    def get_therapist_efficiency(self, therapist_id):
        """Eficiencia del terapeuta 0-100%: 50% audit_score + 50% feedback."""
        from sqlalchemy import func as sqlfunc

        from app.extensions import db
        from app.models import Appointment, SessionAudit

        avg_audit = (
            db.session.query(sqlfunc.avg(SessionAudit.audit_score))
            .join(Appointment, SessionAudit.appointment_id == Appointment.id)
            .filter(Appointment.therapist_id == therapist_id, SessionAudit.audit_score.isnot(None))
            .scalar()
            or 0
        )

        feedback_scores = []
        audits = (
            SessionAudit.query.join(Appointment, SessionAudit.appointment_id == Appointment.id)
            .filter(Appointment.therapist_id == therapist_id, SessionAudit.feedback_engagement.isnot(None))
            .all()
        )

        for a in audits:
            eng = (a.feedback_engagement or 3) / 5.0 * 100
            prog = (a.feedback_progress or 3) / 5.0 * 100
            feedback_scores.append((eng + prog) / 2)

        avg_feedback = sum(feedback_scores) / len(feedback_scores) if feedback_scores else 0

        efficiency = (float(avg_audit) * 0.5) + (avg_feedback * 0.5)

        return {
            'efficiency': round(efficiency, 1),
            'avg_audit_score': round(float(avg_audit), 1),
            'avg_feedback_score': round(avg_feedback, 1),
            'audits_count': len(audits),
        }

    def get_player_stats(self, player_id):
        metrics = self.metrics_repo.get_recent_metrics_by_user(player_id, limit=1000)
        total_sessions = self.metrics_repo.count_sessions_by_user(player_id)

        if metrics:
            acc_list = [m.accurracy for m in metrics]
            avg_time_list = [m.avg_time for m in metrics]
            avg_acc = round(sum(acc_list) / len(acc_list), 1)
            avg_time = round(sum(avg_time_list) / len(avg_time_list), 1)
        else:
            avg_acc = 0
            avg_time = 0

        return {'total_sessions': total_sessions, 'avg_accuracy': avg_acc, 'avg_time': avg_time}
