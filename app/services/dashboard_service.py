from app.repositories.user_repository import UserRepository
from app.repositories.metrics_repository import MetricsRepository
from app.repositories.appointment_repository import AppointmentRepository
from datetime import datetime, timedelta
from app.utils import get_user_today_utc_range, get_user_timezone
import pytz

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
        
        return {
            'therapists': therapists,
            'patients': patients,
            'sessions_total': sessions_total,
            'avg_accuracy': round(avg_acc, 1)
        }

    def get_therapist_stats(self, therapist_id):
        active_patients = self.user_repo.count_active_patients_by_therapist(therapist_id)
        total_sessions = self.appointment_repo.count_by_therapist(therapist_id)
        ia_precision = round(self.metrics_repo.get_avg_accuracy_by_therapist(therapist_id), 1)
        
        # Improvement rate logic
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
            'improvement_rate': improvement_rate
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
                
                patients_data.append({
                    "avatar": f"https://ui-avatars.com/api/?name={(p.username or 'User').replace(' ', '+')}&background=random",
                    "name": p.username or 'Usuario',
                    "ptid": p.id,
                    "game": metrics[0].game_name,
                    "level": metrics[0].prediction,
                    "accuracy": avg_acc,
                    "avg_time": avg_time,
                    "sessions": sessions_count,
                    "prediction_code": metrics[0].prediction
                })
            else:
                patients_data.append({
                    "avatar": f"https://ui-avatars.com/api/?name={(p.username or 'User').replace(' ', '+')}&background=random",
                    "name": p.username or 'Usuario',
                    "ptid": p.id,
                    "game": 'Sin actividad',
                    "level": 0,
                    "accuracy": 0,
                    "avg_time": 0,
                    "sessions": 0,
                    "prediction_code": 0
                })
                
        # Sort by sessions desc and take top 5
        return sorted(patients_data, key=lambda x: x["sessions"], reverse=True)[:5]

    def get_therapist_insights(self, user=None):
        from app.models import SessionMetrics, User, db
        from sqlalchemy import func
        
        # Build last 7 days average accuracy for all active patients
        # Use user's timezone if provided
        if user:
            today_start, _ = get_user_today_utc_range(user)
            today = today_start.date()
        else:
            today = datetime.utcnow().date()
            
        days = [today - timedelta(days=i) for i in range(6, -1, -1)]
        series = []
        for d in days:
            # Construct day range in UTC that corresponds to this local day
            # Note: This simple iteration assumes the day boundaries shift uniformly, 
            # which is close enough for a 7-day chart unless DST change happens exactly then.
            # For strict correctness we would re-convert each day.
            day_start = datetime(d.year, d.month, d.day)
            if user:
                # If we have a user, 'd' is in their local time (naive date).
                # We need to convert (d 00:00 local) -> UTC and (d+1 00:00 local) -> UTC
                tz = get_user_timezone(user)
                local_dt = datetime.combine(d, datetime.min.time())
                local_dt = tz.localize(local_dt)
                day_start = local_dt.astimezone(pytz.UTC).replace(tzinfo=None)
            
            day_end = day_start + timedelta(days=1)
            
            avg_acc = db.session.query(func.avg(SessionMetrics.accurracy))\
                .filter(SessionMetrics.date >= day_start, SessionMetrics.date < day_end).scalar() or 0
            series.append({'date': d.strftime('%Y-%m-%d'), 'avg_accuracy': round(avg_acc, 2)})

        # Alerts: recent risky predictions (prediction==2)
        seven_days_ago = datetime.utcnow() - timedelta(days=7)
        risky = SessionMetrics.query.filter(SessionMetrics.date >= seven_days_ago, SessionMetrics.prediction == 2)\
            .order_by(SessionMetrics.date.desc()).limit(5).all()
        alerts = []
        for r in risky:
            u = User.query.get(r.user_id)
            alerts.append({
                'type': 'red',
                'patient': (u.username or u.email),
                'message': f'Baja precisión ({int(r.accurracy)}%) en {r.game_name}. Sugerido apoyo.'
            })

        return {'weekly_progress': series, 'alerts': alerts}

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
            
        return {
            'total_sessions': total_sessions,
            'avg_accuracy': avg_acc,
            'avg_time': avg_time
        }
